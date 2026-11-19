"""Synchronous access to a streaming IMU on a serial port."""

from __future__ import annotations

from math import isfinite
from time import monotonic
from types import TracebackType
from typing import Generic, TypeVar

from serial import Serial

from .protocol import ImuProtocol

_MeasurementT = TypeVar("_MeasurementT")


class Imu(Generic[_MeasurementT]):
    """Manage a serial connection using the supplied frame protocol."""

    def __init__(
        self, port: str, baudrate: int, *, protocol: ImuProtocol[_MeasurementT]
    ) -> None:
        if not isinstance(port, str) or not port.strip():
            raise ValueError("port must be a non-empty serial device name")
        if isinstance(baudrate, bool) or not isinstance(baudrate, int) or baudrate <= 0:
            raise ValueError("baudrate must be a positive integer")
        self._port = port
        self._baudrate = baudrate
        self._protocol = protocol
        self._serial: Serial | None = None
        self._buffer = bytearray()

    def connect(self) -> bool:
        """Open the port without waiting for data; raise if opening fails."""
        if self._serial is not None:
            return True

        self._serial = Serial(port=self._port, baudrate=self._baudrate, timeout=1.0)
        return True

    def read_frame(self, timeout: float = 1.0) -> bytes:
        """Read one validated frame, raising TimeoutError when the deadline expires."""
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a finite, positive number of seconds")
        connection = self._serial
        if connection is None:
            raise RuntimeError("call connect() before reading from the IMU")

        deadline = monotonic() + timeout
        while True:
            frame = self._protocol.extract_frame(self._buffer)
            if frame is not None:
                return frame
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError(f"no valid IMU frame from {self._port} within {timeout:g} s")

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

    def read_data(self, timeout: float = 1.0) -> _MeasurementT:
        """Read and decode one frame."""
        return self._protocol.decode_frame(self.read_frame(timeout))

    def close(self) -> None:
        """Close the serial port and discard buffered data."""
        connection = self._serial
        self._serial = None
        self._buffer.clear()
        if connection is not None:
            connection.close()

    def __enter__(self) -> Imu[_MeasurementT]:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
