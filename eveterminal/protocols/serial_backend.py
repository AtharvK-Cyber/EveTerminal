"""
Serial console backend using PySerial.
Supports Linux /dev/ttyUSB*, /dev/ttyS*, baud rates, parity, stop bits, flow control.
"""

import threading
import time
from typing import Optional, Callable
from .base import BaseConnection

try:
    import serial
except ImportError:
    serial = None


class SerialConnection(BaseConnection):
    """Serial communication port backend."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: float = 1,
        rtscts: bool = False,
        xonxoff: bool = False,
        on_data_received: Optional[Callable[[bytes], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        super().__init__(on_data_received, on_disconnected)
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.rtscts = rtscts
        self.xonxoff = xonxoff

        self.serial_port: Optional[serial.Serial] = None
        self.reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        if serial is None:
            if self.on_data_received:
                self.on_data_received(b"\r\n[Error: PySerial library is not installed. Run 'apt install python3-serial']\r\n")
            return False

        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                rtscts=self.rtscts,
                xonxoff=self.xonxoff,
                timeout=0.1,
            )
            self._connected = True

            self._stop_event.clear()
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            return True
        except Exception as e:
            if self.on_data_received:
                self.on_data_received(f"\r\n[Serial Error: {e}]\r\n".encode("utf-8"))
            self.disconnect()
            return False

    def _read_loop(self) -> None:
        while not self._stop_event.is_set() and self.serial_port and self.serial_port.is_open:
            try:
                data = self.serial_port.read(1024)
                if data:
                    if self.on_data_received:
                        self.on_data_received(data)
            except Exception:
                break

        self._connected = False
        if self.on_disconnected:
            self.on_disconnected()

    def send(self, data: bytes) -> None:
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data)
            except Exception:
                self.disconnect()

    def disconnect(self) -> None:
        self._stop_event.set()
        self._connected = False
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass
            self.serial_port = None
