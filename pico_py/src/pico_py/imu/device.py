"""Synchronous access to one CMP10A on an explicitly selected serial port."""

from __future__ import annotations

from math import isfinite
from time import monotonic
from types import TracebackType

from serial import Serial

from . import cmp10a


class Imu:
    """Manage a CMP10A connection. Use one reader at a time per port."""

    def __init__(self, port: str, baudrate: int = 9600) -> None:
        if not isinstance(port, str) or not port.strip():
            raise ValueError("port must be a non-empty serial device name")
        if isinstance(baudrate, bool) or not isinstance(baudrate, int) or baudrate <= 0:
            raise ValueError("baudrate must be a positive integer")
        self._port = port
        self._baudrate = baudrate
        self._serial: Serial | None = None
        self._buffer = bytearray()
        self._first_frame: bytes | None = None

    def connect(self) -> bool:
        """Open the port and verify a valid CMP10A frame arrives within one second."""
        if self._serial is not None:
            return True

        self._serial = Serial(port=self._port, baudrate=self._baudrate, timeout=1.0)
        try:
            self._first_frame = self.read_frame()
        except BaseException:
            self.close()
            raise
        return True

    def read_frame(self, timeout: float = 1.0) -> bytes:
        """Read one validated frame, raising TimeoutError when the deadline expires."""
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a finite, positive number of seconds")
        connection = self._serial
        if connection is None:
            raise RuntimeError("call connect() before reading from the IMU")

        if self._first_frame is not None:
            frame = self._first_frame
            self._first_frame = None
            return frame

        deadline = monotonic() + timeout
        while True:
            frame = cmp10a._pop_frame(self._buffer)
            if frame is not None:
                return frame
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError(f"no valid CMP10A frame from {self._port} within {timeout:g} s")

            # Wait for one byte when idle, or read a batch that's already queued.
            queued = connection.in_waiting
            if queued:
                size = min(queued, 256)
                read_timeout = 0
            else:
                size = 1
                read_timeout = remaining
            if connection.timeout != read_timeout:
                connection.timeout = read_timeout
            self._buffer.extend(connection.read(size))

    def read_data(self, timeout: float = 1.0) -> cmp10a.Measurement:
        """Read and decode one frame."""
        return cmp10a.decode_frame(self.read_frame(timeout))

    def close(self) -> None:
        """Close the serial port and discard buffered data."""
        connection = self._serial
        self._serial = None
        self._buffer.clear()
        self._first_frame = None
        if connection is not None:
            connection.close()

    def __enter__(self) -> Imu:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
