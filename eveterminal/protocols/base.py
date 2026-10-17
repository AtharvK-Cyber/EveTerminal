"""
Abstract connection interface for terminal backends (SSH, Serial, Telnet, PTY).
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseConnection(ABC):
    """Abstract base class for all protocol backends."""

    def __init__(self, on_data_received: Optional[Callable[[bytes], None]] = None, on_disconnected: Optional[Callable[[], None]] = None):
        self.on_data_received = on_data_received
        self.on_disconnected = on_disconnected
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to remote endpoint or local device."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully terminates connection and releases descriptors."""
        pass

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Sends raw byte stream to connection."""
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected
