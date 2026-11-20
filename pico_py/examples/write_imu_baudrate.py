"""Change the serial baud rate of a CMP10A and send its save command."""

import argparse
import sys
from time import sleep

from serial import SerialException

from pico_py.imu import Imu, cmp10a


def _unlock(imu: Imu) -> None:
    imu.write(cmp10a.encode_unlock())
    sleep(0.1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port, for example /dev/ttyUSB0 or COM3")
    parser.add_argument("--baudrate", type=int, required=True, help="target baud rate")
    parser.add_argument(
        "--current-baudrate", type=int, default=9600,
        help="device's current baud rate (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        command = cmp10a.encode_set_baudrate(args.baudrate)
        with Imu(args.port, args.current_baudrate, protocol=cmp10a) as imu:
            imu.read_frame()
            if args.current_baudrate == args.baudrate:
                print(f"Already receiving frames at {args.baudrate} baud; no change made.")
                return 0
            _unlock(imu)
            imu.write(command)
            sleep(0.1)

        # The device may switch immediately or wait for SAVE.
        for baudrate in (args.baudrate, args.current_baudrate):
            with Imu(args.port, baudrate, protocol=cmp10a) as imu:
                try:
                    imu.read_frame()
                except TimeoutError:
                    continue
                _unlock(imu)
                imu.write(cmp10a.encode_save())
                sleep(0.1)
                break
        else:
            raise TimeoutError("No valid frame at the target or previous baud rate; SAVE was not sent.")

        with Imu(args.port, args.baudrate, protocol=cmp10a) as imu:
            imu.read_frame()
        print(f"Receiving frames at {args.baudrate} baud. SAVE sent; power-cycle to verify persistence.")
    except KeyboardInterrupt:
        return 130
    except (SerialException, TimeoutError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
