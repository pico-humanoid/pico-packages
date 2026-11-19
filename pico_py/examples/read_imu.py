"""Print measurements from a CMP10A connected to a serial port."""

import argparse
import sys

from serial import SerialException

from pico_py.imu import Imu, cmp10a


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port, for example /dev/ttyUSB0 or COM3")
    parser.add_argument("--baudrate", type=int, default=9600)
    args = parser.parse_args()

    try:
        with Imu(port=args.port, baudrate=args.baudrate, protocol=cmp10a) as imu:
            while True:
                print(imu.read_data(), flush=True)
    except KeyboardInterrupt:
        return 0
    except (SerialException, TimeoutError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
