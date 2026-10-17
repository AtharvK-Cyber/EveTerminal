"""
SSHv2 protocol backend using Paramiko.
Supports password, public key files, OpenSSH agent, and channel resizing.
"""

import threading
import time
from typing import Optional, Callable
from .base import BaseConnection

try:
    import paramiko
except ImportError:
    paramiko = None


class SSHConnection(BaseConnection):
    """SSH2 terminal session."""

    def __init__(
        self,
        hostname: str,
        port: int = 22,
        username: str = "",
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        cols: int = 80,
        rows: int = 24,
        on_data_received: Optional[Callable[[bytes], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        super().__init__(on_data_received, on_disconnected)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.cols = cols
        self.rows = rows

        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        self.reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        if paramiko is None:
            if self.on_data_received:
                self.on_data_received(b"\r\n[Error: Paramiko library is not installed. Run 'apt install python3-paramiko']\r\n")
            return False

        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                key_filename=self.key_filename or None,
                allow_agent=True,
                look_for_keys=True,
                timeout=15,
            )

            self.channel = self.client.invoke_shell(
                term="xterm-256color",
                width=self.cols,
                height=self.rows,
            )
            # Enable SSH transport keepalive (every 15s) to prevent idle timeouts
            transport = self.client.get_transport()
            if transport:
                transport.set_keepalive(15)
            self._connected = True

            self._stop_event.clear()
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            return True
        except Exception as e:
            if self.on_data_received:
                self.on_data_received(f"\r\n[SSH Connection Error: {e}]\r\n".encode("utf-8"))
            self.disconnect()
            return False

    def _read_loop(self) -> None:
        while not self._stop_event.is_set() and self.channel and not self.channel.closed:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(4096)
                    if not data:
                        break
                    if self.on_data_received:
                        self.on_data_received(data)
                else:
                    time.sleep(0.01)
            except Exception:
                break

        self._connected = False
        if self.on_disconnected:
            self.on_disconnected()

    def send(self, data: bytes) -> None:
        if self.channel and not self.channel.closed:
            try:
                self.channel.sendall(data)
            except Exception:
                self.disconnect()

    def resize_pty(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        if self.channel and not self.channel.closed:
            try:
                self.channel.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def disconnect(self) -> None:
        self._stop_event.set()
        self._connected = False
        if self.channel:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
