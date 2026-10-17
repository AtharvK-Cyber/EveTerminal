"""
Local POSIX PTY Shell Backend.
Spawns an interactive local shell (/bin/bash) on Linux / Debian.
"""

import os
import sys
import threading
from typing import Optional, Callable
from .base import BaseConnection


class PtyConnection(BaseConnection):
    """Local terminal shell session using POSIX pseudo-terminal."""

    def __init__(
        self,
        shell_cmd: Optional[str] = None,
        cols: int = 80,
        rows: int = 24,
        on_data_received: Optional[Callable[[bytes], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        super().__init__(on_data_received, on_disconnected)
        self.shell_cmd = shell_cmd or os.environ.get("SHELL", "/bin/bash")
        self.cols = cols
        self.rows = rows

        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        if os.name == "nt":
            # On Windows, local PTY requires winpty / conpty; provide informational message
            if self.on_data_received:
                self.on_data_received(b"\r\n[Local shell is designed for Debian / Linux hosts]\r\n")
            return False

        try:
            import pty
            import termios
            import struct
            import fcntl

            pid, fd = pty.fork()
            if pid == 0:
                # Child process
                env = os.environ.copy()
                env["TERM"] = "xterm-256color"
                os.execvpe(self.shell_cmd, [self.shell_cmd], env)
            else:
                # Parent process
                self.pid = pid
                self.master_fd = fd
                self._connected = True

                # Set window size
                ws = struct.pack("HHHH", self.rows, self.cols, 0, 0)
                fcntl.ioctl(fd, termios.TIOCSWINSZ, ws)

                self._stop_event.clear()
                self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
                self.reader_thread.start()
                return True
        except Exception as e:
            if self.on_data_received:
                self.on_data_received(f"\r\n[PTY Error: {e}]\r\n".encode("utf-8"))
            self.disconnect()
            return False

    def _read_loop(self) -> None:
        while not self._stop_event.is_set() and self.master_fd is not None:
            try:
                data = os.read(self.master_fd, 1024)
                if not data:
                    break
                if self.on_data_received:
                    self.on_data_received(data)
            except Exception:
                break

        self._connected = False
        if self.on_disconnected:
            self.on_disconnected()

    def send(self, data: bytes) -> None:
        if self.master_fd is not None and self._connected:
            try:
                os.write(self.master_fd, data)
            except Exception:
                self.disconnect()

    def disconnect(self) -> None:
        self._stop_event.set()
        self._connected = False
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None
        if self.pid is not None:
            try:
                import signal
                os.kill(self.pid, signal.SIGTERM)
            except Exception:
                pass
            self.pid = None
