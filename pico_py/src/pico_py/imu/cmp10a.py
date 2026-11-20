"""Frame validation, decoding and command encoding for the CMP10A serial protocol."""

from dataclasses import dataclass
from struct import pack, unpack_from

FRAME_SIZE = 11
_HEADER = b"\x55"
_FRAME_TYPES = frozenset(range(0x50, 0x5B)) | {0x5F}
_BAUD_CODES = {4800: 1, 9600: 2, 19200: 3, 38400: 4, 57600: 5, 115200: 6, 230400: 7}


@dataclass(frozen=True, slots=True)
class Acceleration:
    x_g: float
    y_g: float
    z_g: float
    temperature_c: float


@dataclass(frozen=True, slots=True)
class AngularVelocity:
    x_dps: float
    y_dps: float
    z_dps: float


@dataclass(frozen=True, slots=True)
class EulerAngles:
    roll_deg: float
    pitch_deg: float
    yaw_deg: float


@dataclass(frozen=True, slots=True)
class MagneticField:
    x_lsb: int
    y_lsb: int
    z_lsb: int
    temperature_c: float


@dataclass(frozen=True, slots=True)
class UndecodedFrame:
    """Valid CMP10A frame type without a dedicated decoder in this release."""

    frame_type: int
    payload: bytes


Measurement = Acceleration | AngularVelocity | EulerAngles | MagneticField | UndecodedFrame


def _encode_register_write(address: int, value: int) -> bytes:
    return b"\xFF\xAA" + pack("<BH", address, value)


def encode_unlock() -> bytes:
    """Encode the KEY command to unlock the device's configuration registers."""
    return _encode_register_write(0x69, 0xB588)


def encode_set_baudrate(baudrate: int) -> bytes:
    """Encode a BAUD command for a rate supported by the CMP10A."""
    if type(baudrate) is not int or baudrate not in _BAUD_CODES:
        raise ValueError(f"unsupported CMP10A baud rate: {baudrate!r}")
    return _encode_register_write(0x04, _BAUD_CODES[baudrate])


def encode_calibrate_accel() -> bytes:
    """Encode the CALSW command to start automatic accelerometer calibration."""
    return _encode_register_write(0x01, 0x0001)


def encode_save() -> bytes:
    """Encode the SAVE command to persist the device's current configuration."""
    return _encode_register_write(0x00, 0x0000)


def _frame_error(frame: bytes) -> str | None:
    if len(frame) != FRAME_SIZE:
        return f"expected {FRAME_SIZE} bytes, got {len(frame)}"
    if not frame.startswith(_HEADER):
        return "expected a CMP10A frame header (0x55)"
    if frame[1] not in _FRAME_TYPES:
        return f"unknown CMP10A frame type 0x{frame[1]:02X}"
    if (sum(frame[:-1]) & 0xFF) != frame[-1]:
        return "CMP10A checksum mismatch"
    return None


def decode_frame(frame: bytes) -> Measurement:
    """Decode one complete frame; raise ValueError for malformed data."""
    error = _frame_error(frame)
    if error is not None:
        raise ValueError(error)

    kind = frame[1]
    if kind not in (0x51, 0x52, 0x53, 0x54):
        return UndecodedFrame(kind, bytes(frame[2:-1]))

    x, y, z, extra = unpack_from("<4h", frame, 2)
    if kind == 0x51:
        scale = 16 / 32768
        return Acceleration(x * scale, y * scale, z * scale, extra / 100)
    if kind == 0x52:
        scale = 2000 / 32768
        return AngularVelocity(x * scale, y * scale, z * scale)
    if kind == 0x53:
        scale = 180 / 32768
        return EulerAngles(x * scale, y * scale, z * scale)
    return MagneticField(x, y, z, extra / 100)


def extract_frame(buffer: bytearray) -> bytes | None:
    """Consume one valid frame, retaining unread bytes and incomplete frames."""
    while True:
        start = buffer.find(_HEADER)
        if start == -1:
            buffer.clear()
            return None
        del buffer[:start]
        if len(buffer) < FRAME_SIZE:
            return None

        frame = bytes(buffer[:FRAME_SIZE])
        if _frame_error(frame) is None:
            del buffer[:FRAME_SIZE]
            return frame
        # A bad candidate may contain the header of the next valid frame.
        del buffer[0]
