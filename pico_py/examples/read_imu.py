"""Print measurements from a CMP10A connected to a serial port."""

import argparse
import sys
from math import isfinite
from time import monotonic

from serial import SerialException

from pico_py.imu import Imu, cmp10a


def _positive_hz(value: str) -> float:
    try:
        hz = float(value)
    except ValueError:
        hz = 0.0
    if not isfinite(hz) or hz <= 0 or not isfinite(1 / hz):
        raise argparse.ArgumentTypeError("print frequency must be a finite, positive number")
    return hz


def _format_values(values, spec: str, width: int) -> str:
    return " ".join(f"{v:{spec}}" if v is not None else f"{'--':>{width}}" for v in values)


def _format_line(latest: dict[str, tuple]) -> str:
    empty_axes = (None, None, None)
    acc = _format_values(latest.get("acc", empty_axes), "+7.3f", 7)
    gyro = _format_values(latest.get("gyro", empty_axes), "+7.1f", 7)
    rpy = _format_values(latest.get("rpy", empty_axes), "+6.1f", 6)
    mag = _format_values(latest.get("mag", empty_axes), "+6d", 6)
    temp = _format_values(latest.get("temp", (None,)), "+7.2f", 7)
    return f"A[g] {acc} | G[d/s] {gyro} | RPY[deg] {rpy} | M[lsb] {mag} | T[C] {temp}"


def _update_latest(latest: dict[str, tuple], data: cmp10a.Measurement) -> None:
    if isinstance(data, cmp10a.Acceleration):
        latest["acc"] = (data.x_g, data.y_g, data.z_g)
        latest["temp"] = (data.temperature_c,)
    elif isinstance(data, cmp10a.AngularVelocity):
        latest["gyro"] = (data.x_dps, data.y_dps, data.z_dps)
    elif isinstance(data, cmp10a.EulerAngles):
        latest["rpy"] = (data.roll_deg, data.pitch_deg, data.yaw_deg)
    elif isinstance(data, cmp10a.MagneticField):
        latest["mag"] = (data.x_lsb, data.y_lsb, data.z_lsb)
        latest["temp"] = (data.temperature_c,)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port, for example /dev/ttyUSB0 or COM3")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument(
        "--print-hz", type=_positive_hz, metavar="HZ",
        help="maximum output lines per second (default: print each decoded measurement)",
    )
    args = parser.parse_args()

    interval = 1 / args.print_hz if args.print_hz is not None else 0.0
    next_print = 0.0
    latest: dict[str, tuple] = {}
    try:
        with Imu(port=args.port, baudrate=args.baudrate, protocol=cmp10a) as imu:
            while True:
                data = imu.read_data()
                if isinstance(data, cmp10a.UndecodedFrame):
                    continue
                _update_latest(latest, data)
                now = monotonic()
                if now >= next_print:
                    print(_format_line(latest), flush=True)
                    next_print = now + interval
    except KeyboardInterrupt:
        return 0
    except (SerialException, TimeoutError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
