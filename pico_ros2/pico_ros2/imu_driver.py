"""Publish CMP10A measurements as ROS 2 sensor messages."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from math import cos, radians, sin
import os
import sys
from time import monotonic, sleep

from pico_py.imu import Imu as SerialImu
from pico_py.imu import cmp10a
from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.exceptions import ParameterException
from rclpy.logging import get_logger
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Imu, MagneticField, Temperature


_SCAN_RATES = (9600, 115200, 19200, 38400, 57600, 230400, 4800)
_PROBE_TIMEOUT_S = 2.0
_PROBE_FRAMES = 3
_READ_TIMEOUT_S = 0.1
_COMMAND_DELAY_S = 0.1
_MAX_SAMPLE_SPAN_S = 0.1
_STANDARD_GRAVITY = 9.80665
# Yahboom specifies a typical magnetometer resolution of 0.0667 mGauss/LSB.
_CMP10A_TESLA_PER_LSB = 6.67e-9

_RAW_TYPES = (cmp10a.Acceleration, cmp10a.AngularVelocity)
_ORIENTATION_TYPES = (*_RAW_TYPES, cmp10a.EulerAngles)


@dataclass(frozen=True)
class _Sample:
    data: cmp10a.Measurement
    stamp: Time
    received_at: float


class ImuDriver(Node):
    """Configure a serial IMU and publish its decoded measurements."""

    def __init__(self) -> None:
        """Declare startup parameters and create the requested publishers."""
        super().__init__('imu_driver')
        defaults = {
            'model': 'cmp10a',
            'port': '/dev/ttyUSB0',
            'baudrate': 9600,
            'frame_id': 'imu_link',
            'publish_mag': True,
            'publish_temperature': True,
        }
        self.declare_parameters('', [
            (name, value, ParameterDescriptor(read_only=True))
            for name, value in defaults.items()
        ])
        self._model = self.get_parameter('model').value
        self._port = self.get_parameter('port').value
        self._baudrate = self.get_parameter('baudrate').value
        self._frame_id = self.get_parameter('frame_id').value
        publish_mag = self.get_parameter('publish_mag').value
        publish_temperature = self.get_parameter('publish_temperature').value

        logger = self.get_logger()
        logger.info(
            f'Startup configuration: model={self._model} port={self._port} '
            f'target_baudrate={self._baudrate} frame_id={self._frame_id}'
        )
        logger.info(
            f'Optional topics: publish_mag={publish_mag} '
            f'publish_temperature={publish_temperature}'
        )
        if self._model != 'cmp10a':
            raise ValueError(f'Unsupported IMU model: {self._model!r}; supported: cmp10a')
        if not self._port.strip() or not self._frame_id.strip():
            raise ValueError('port and frame_id must be non-empty')
        self._baudrate_command = cmp10a.encode_set_baudrate(self._baudrate)

        qos = qos_profile_sensor_data
        self._raw_pub = self.create_publisher(Imu, 'imu/data_raw', qos)
        self._data_pub = self.create_publisher(Imu, 'imu/data', qos)
        self._mag_pub = (
            self.create_publisher(MagneticField, 'imu/mag', qos) if publish_mag else None
        )
        self._temp_pub = (
            self.create_publisher(Temperature, 'imu/temperature', qos)
            if publish_temperature else None
        )
        self._raw_samples = {}
        self._orientation_samples = {}
        self._ready = False

    def run(self) -> None:
        """Read and publish frames until ROS shuts down or the port fails."""
        with self._connect() as imu:
            while self.context.ok():
                try:
                    data = imu.read_data(timeout=_READ_TIMEOUT_S)
                except TimeoutError:
                    pass
                else:
                    self._handle_sample(_Sample(data, self.get_clock().now(), monotonic()))
                rclpy.spin_once(self, timeout_sec=0.0)

    def _confirm_frames(self, imu: SerialImu) -> bool:
        deadline = monotonic() + _PROBE_TIMEOUT_S
        count = 0
        while self.context.ok():
            remaining = deadline - monotonic()
            if remaining <= 0:
                return False
            try:
                data = imu.read_data(timeout=min(remaining, _READ_TIMEOUT_S))
            except TimeoutError:
                continue
            if isinstance(data, cmp10a.UndecodedFrame):
                count = 0
                continue
            count += 1
            if count == _PROBE_FRAMES:
                return True
        raise ExternalShutdownException()

    @contextmanager
    def _connect(self):
        rates = tuple(dict.fromkeys((self._baudrate, *_SCAN_RATES)))
        logger = self.get_logger()
        for rate in rates:
            logger.debug(f'Probing IMU port={self._port} baudrate={rate}')
            # A new SDK connection starts with an empty frame buffer.
            with SerialImu(self._port, rate, protocol=cmp10a) as imu:
                if not self._confirm_frames(imu):
                    continue
                logger.info(f'Valid CMP10A frames detected: detected_baudrate={rate}')
                if rate == self._baudrate:
                    yield imu
                    return
                _write_unlocked(imu, self._baudrate_command)
                break
        else:
            raise TimeoutError(
                f'No valid {self._model} stream on {self._port}; tried baud rates {rates}'
            )

        self._save_baudrate(previous_rate=rate)
        with SerialImu(self._port, self._baudrate, protocol=cmp10a) as imu:
            if not self._confirm_frames(imu):
                raise TimeoutError(
                    f'Could not verify {self._model} on {self._port} '
                    f'at target baud rate {self._baudrate} after sending SAVE'
                )
            logger.info(
                f'Communication verified after baud rate change: active_baudrate={self._baudrate}'
            )
            yield imu

    def _save_baudrate(self, previous_rate: int) -> None:
        # Firmware may switch immediately or keep the old rate until SAVE.
        for rate in (self._baudrate, previous_rate):
            with SerialImu(self._port, rate, protocol=cmp10a) as imu:
                if self._confirm_frames(imu):
                    _write_unlocked(imu, cmp10a.encode_save())
                    self.get_logger().info(f'Sent CMP10A SAVE command at baudrate={rate}')
                    return
        raise TimeoutError(
            f'Could not send SAVE on {self._port}; no valid frames at baud rates '
            f'{self._baudrate} or {previous_rate} after the change command'
        )

    def _handle_sample(self, sample: _Sample) -> None:
        data = sample.data
        kind = type(data)
        if kind in _RAW_TYPES:
            self._raw_samples[kind] = sample
            if self._publish_imu(self._raw_pub, self._raw_samples, _RAW_TYPES) and not self._ready:
                self._ready = True
                topic = self._raw_pub.topic_name
                self.get_logger().info(_success_text(f'Ready: first {topic} message published'))
        if kind in _ORIENTATION_TYPES:
            self._orientation_samples[kind] = sample
            self._publish_imu(
                self._data_pub, self._orientation_samples, _ORIENTATION_TYPES
            )
        if isinstance(data, cmp10a.Acceleration) and self._temp_pub is not None:
            msg = Temperature()
            msg.header.frame_id = self._frame_id
            msg.header.stamp = sample.stamp.to_msg()
            msg.temperature = data.temperature_c
            self._temp_pub.publish(msg)
        if isinstance(data, cmp10a.MagneticField) and self._mag_pub is not None:
            msg = MagneticField()
            msg.header.frame_id = self._frame_id
            msg.header.stamp = sample.stamp.to_msg()
            msg.magnetic_field.x = data.x_lsb * _CMP10A_TESLA_PER_LSB
            msg.magnetic_field.y = data.y_lsb * _CMP10A_TESLA_PER_LSB
            msg.magnetic_field.z = data.z_lsb * _CMP10A_TESLA_PER_LSB
            self._mag_pub.publish(msg)

    def _publish_imu(self, publisher, pending: dict, required_types: tuple) -> bool:
        if len(pending) < len(required_types):
            return False
        samples = [pending[kind] for kind in required_types]
        latest = max(samples, key=lambda sample: sample.received_at)
        cutoff = latest.received_at - _MAX_SAMPLE_SPAN_S
        stale_types = [kind for kind, sample in pending.items() if sample.received_at < cutoff]
        if stale_types:
            for kind in stale_types:
                del pending[kind]
            return False

        accel, gyro = (sample.data for sample in samples[:2])
        msg = Imu()
        msg.header.frame_id = self._frame_id
        msg.header.stamp = latest.stamp.to_msg()
        msg.linear_acceleration.x = accel.x_g * _STANDARD_GRAVITY
        msg.linear_acceleration.y = accel.y_g * _STANDARD_GRAVITY
        msg.linear_acceleration.z = accel.z_g * _STANDARD_GRAVITY
        msg.angular_velocity.x = radians(gyro.x_dps)
        msg.angular_velocity.y = radians(gyro.y_dps)
        msg.angular_velocity.z = radians(gyro.z_dps)
        if len(samples) == 3:
            msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w = (
                _quaternion_from_rpy(samples[2].data)
            )
        else:
            msg.orientation_covariance[0] = -1.0
        publisher.publish(msg)
        pending.clear()
        return True


def _write_unlocked(imu: SerialImu, command: bytes) -> None:
    imu.write(cmp10a.encode_unlock())
    sleep(_COMMAND_DELAY_S)
    imu.write(command)
    sleep(_COMMAND_DELAY_S)


def _quaternion_from_rpy(angles: cmp10a.EulerAngles) -> tuple[float, float, float, float]:
    # Fixed-axis roll, pitch, yaw about X, Y, Z in the device's reference frame.
    roll = radians(angles.roll_deg) / 2
    pitch = radians(angles.pitch_deg) / 2
    yaw = radians(angles.yaw_deg) / 2
    cr, sr = cos(roll), sin(roll)
    cp, sp = cos(pitch), sin(pitch)
    cy, sy = cos(yaw), sin(yaw)
    return (
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    )


def _success_text(message: str) -> str:
    color_setting = os.getenv('RCUTILS_COLORIZED_OUTPUT')
    stream = sys.stdout if os.getenv('RCUTILS_LOGGING_USE_STDOUT') == '1' else sys.stderr
    if color_setting == '1' or (color_setting in (None, '') and stream.isatty()):
        return f'\x1b[32m{message}\x1b[0m'
    return message


def main(args=None) -> int:
    """Run the IMU node and release ROS and serial resources on exit."""
    rclpy.init(args=args)
    node = None
    try:
        node = ImuDriver()
        node.run()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (OSError, ParameterException, ValueError) as error:
        logger = node.get_logger() if node is not None else get_logger('imu_driver')
        logger.error(f'IMU driver failed: {error}')
        return 1
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
    return 0
