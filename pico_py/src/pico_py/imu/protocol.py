"""Contract for streaming serial IMU protocols."""

from typing import Protocol, TypeVar

_MeasurementT_co = TypeVar("_MeasurementT_co", covariant=True)


class ImuProtocol(Protocol[_MeasurementT_co]):
    """A module or object that can extract and decode frames."""

    def extract_frame(self, buffer: bytearray, /) -> bytes | None:
        """Consume one valid frame, or return None if more bytes are needed.

        Discard unusable bytes in place and retain any incomplete frame and
        unread bytes for the next call. The caller owns the buffer.
        """
        ...

    def decode_frame(self, frame: bytes, /) -> _MeasurementT_co:
        """Decode one complete frame into the protocol's measurement type."""
        ...
