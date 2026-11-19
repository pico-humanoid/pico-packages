from unittest import TestCase
from unittest.mock import patch

from pico_py.imu import Imu


class LineProtocol:
    """A test protocol with a different frame format and measurement type."""

    def extract_frame(self, buffer: bytearray) -> bytes | None:
        end = buffer.find(b"\n")
        if end == -1:
            return None
        frame = bytes(buffer[:end + 1])
        del buffer[:end + 1]
        return frame

    def decode_frame(self, frame: bytes) -> int:
        return int(frame)


class ImuTests(TestCase):
    def test_reads_using_an_independent_protocol(self):
        with patch("pico_py.imu.device.Serial") as create_serial:
            serial = create_serial.return_value
            serial.in_waiting = 6
            serial.read.return_value = b"17\n42\n"
            with Imu("test-port", 115200, protocol=LineProtocol()) as imu:
                serial.read.assert_not_called()
                self.assertEqual(imu.read_frame(), b"17\n")
                self.assertEqual(imu.read_data(), 42)
            create_serial.assert_called_once_with(
                port="test-port", baudrate=115200, timeout=1.0
            )
            serial.read.assert_called_once_with(6)
            serial.close.assert_called_once_with()

    def test_read_timeout_keeps_the_port_and_partial_frame(self):
        with patch("pico_py.imu.device.Serial") as create_serial:
            serial = create_serial.return_value
            serial.in_waiting = 0
            serial.read.side_effect = [b"1", b"7", b"\n"]
            with Imu("test-port", 9600, protocol=LineProtocol()) as imu:
                with patch("pico_py.imu.device.monotonic", side_effect=[0, 0, 1]):
                    with self.assertRaisesRegex(TimeoutError, "test-port"):
                        imu.read_frame()
                serial.close.assert_not_called()
                self.assertEqual(imu.read_data(), 17)
            serial.close.assert_called_once_with()
