"""
RFC 854 / RFC 855 Telnet Protocol Backend for EVE-NG, GNS3, and Cisco Consoles.
Implements:
- Full Telnet option negotiation (SGA, ECHO, BINARY, NAWS, TTYPE)
- TCP socket keepalive and periodic Telnet IAC NOP keepalives (prevents 30s disconnects)
- Robust non-blocking read loop that handles idle timeouts without disconnecting
- Thread-safe data transmission
"""

import socket
import threading
import time
from typing import Optional, Callable, Dict, Set
from .base import BaseConnection

# Telnet command bytes (RFC 854)
SE   = 240  # End of subnegotiation
NOP  = 241  # No Operation (Keepalive)
DM   = 242  # Data Mark
BRK  = 243  # Break
IP   = 244  # Interrupt Process
AO   = 245  # Abort Output
AYT  = 246  # Are You There
EC   = 247  # Erase Character
EL   = 248  # Erase Line
GA   = 249  # Go Ahead
SB   = 250  # Subnegotiation Begin
WILL = 251
WONT = 252
DO   = 253
DONT = 254
IAC  = 255  # Interpret As Command

# Telnet options
OPT_BINARY = 0    # 8-bit data path (RFC 856)
OPT_ECHO   = 1    # Echo (RFC 857)
OPT_SGA    = 3    # Suppress Go Ahead (RFC 858)
OPT_TTYPE  = 24   # Terminal Type (RFC 1091)
OPT_NAWS   = 31   # Negotiate About Window Size (RFC 1073)


class TelnetConnection(BaseConnection):
    """
    Robust Telnet connection optimized for EVE-NG, GNS3, and Cisco network devices.
    Maintains persistent connections with active keepalive.
    """

    def __init__(
        self,
        hostname: str,
        port: int = 23,
        cols: int = 80,
        rows: int = 24,
        terminal_type: str = "VT100",
        keepalive_interval: int = 15,
        on_data_received: Optional[Callable[[bytes], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        super().__init__(on_data_received, on_disconnected)
        self.hostname = hostname
        self.port = port
        self.cols = cols
        self.rows = rows
        self.terminal_type = terminal_type
        self.keepalive_interval = keepalive_interval

        self.sock: Optional[socket.socket] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.keepalive_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._send_lock = threading.Lock()
        self._last_activity = time.time()

        # Track negotiation states to prevent infinite echo loops
        self._my_opts: Set[int] = set()
        self._his_opts: Set[int] = set()

    def connect(self) -> bool:
        """Establishes socket connection and configures keepalives."""
        try:
            # Initial connection with timeout
            sock = socket.create_connection((self.hostname, self.port), timeout=10)

            # Enable OS-level TCP Keepalive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                # Linux-specific TCP keepalive tuning
                if hasattr(socket, "TCP_KEEPIDLE"):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
                if hasattr(socket, "TCP_KEEPINTVL"):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
                if hasattr(socket, "TCP_KEEPCNT"):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            except Exception:
                pass

            # CRITICAL FIX: Set read timeout to 1.0 second so recv() periodically
            # wakes up to check _stop_event, but NEVER aborts the connection on timeout!
            sock.settimeout(1.0)
            self.sock = sock
            self._connected = True
            self._last_activity = time.time()
            self._stop_event.clear()

            # Start reader thread
            self.reader_thread = threading.Thread(target=self._read_loop, name=f"TelnetReader-{self.hostname}:{self.port}", daemon=True)
            self.reader_thread.start()

            # Start Telnet IAC NOP keepalive thread (prevents EVE-NG 30s disconnect)
            self.keepalive_thread = threading.Thread(target=self._keepalive_loop, name=f"TelnetKeepalive-{self.hostname}:{self.port}", daemon=True)
            self.keepalive_thread.start()

            return True
        except Exception as e:
            if self.on_data_received:
                self.on_data_received(f"\r\n[Telnet Connection Error: {e}]\r\n".encode("utf-8"))
            self.disconnect()
            return False

    def _read_loop(self) -> None:
        """Continuously reads from socket and handles timeouts gracefully."""
        while not self._stop_event.is_set() and self.sock:
            try:
                raw = self.sock.recv(4096)
                if not raw:
                    # Connection closed by remote endpoint
                    break

                self._last_activity = time.time()
                filtered = self._process_telnet_data(raw)
                if filtered and self.on_data_received:
                    self.on_data_received(filtered)

            except (socket.timeout, TimeoutError):
                # Normal read timeout; socket is still healthy, continue listening!
                continue
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                # Remote end forcibly closed socket
                break
            except OSError as e:
                # Catch non-fatal socket conditions (EAGAIN / EWOULDBLOCK)
                if getattr(e, "errno", None) in (11, 10035):
                    continue
                break
            except Exception:
                break

        self._connected = False
        if self.on_disconnected:
            self.on_disconnected()

    def _keepalive_loop(self) -> None:
        """
        Sends Telnet IAC NOP (0xFF 0xF1) periodically if idle.
        This keeps NAT states, EVE-NG web proxies, and hypervisor console ports alive.
        """
        while not self._stop_event.is_set():
            time.sleep(2.0)
            if self._stop_event.is_set() or not self._connected:
                break

            # If no data sent or received within keepalive_interval, send Telnet NOP
            if time.time() - self._last_activity >= self.keepalive_interval:
                self.send_raw(bytes([IAC, NOP]))
                self._last_activity = time.time()

    def _process_telnet_data(self, data: bytes) -> bytes:
        """
        Parses Telnet command streams according to RFC 854/855.
        Properly negotiates SGA, ECHO, NAWS, and TTYPE for EVE-NG/Cisco.
        """
        out = bytearray()
        i = 0
        n = len(data)

        while i < n:
            b = data[i]
            if b == IAC:
                if i + 1 >= n:
                    break
                cmd = data[i + 1]

                # --- 3-byte command: DO, DONT, WILL, WONT ---
                if cmd in (DO, DONT, WILL, WONT):
                    if i + 2 >= n:
                        break
                    opt = data[i + 2]
                    self._handle_negotiation(cmd, opt)
                    i += 3
                    continue

                # --- Subnegotiation: SB ... SE ---
                elif cmd == SB:
                    # Find matching IAC SE
                    idx = data.find(bytes([IAC, SE]), i + 2)
                    if idx != -1:
                        sb_payload = data[i + 2:idx]
                        self._handle_subnegotiation(sb_payload)
                        i = idx + 2
                    else:
                        break
                    continue

                # --- Escaped 0xFF literal ---
                elif cmd == IAC:
                    out.append(IAC)
                    i += 2
                    continue

                # --- Other 2-byte commands (NOP, GA, AYT, etc.) ---
                else:
                    if cmd == AYT:
                        self.send_raw(b"\r\n[SecureCRT Linux: Terminal Ready]\r\n")
                    i += 2
                    continue
            else:
                out.append(b)
                i += 1

        return bytes(out)

    def _handle_negotiation(self, cmd: int, opt: int) -> None:
        """
        Responds to options according to RFC 854 rules.
        Never sends duplicate responses to avoid negotiation loops.
        """
        if cmd == WILL:
            # Server says: I WILL use option
            if opt in (OPT_ECHO, OPT_SGA, OPT_BINARY):
                if opt not in self._his_opts:
                    self._his_opts.add(opt)
                    self.send_raw(bytes([IAC, DO, opt]))
            else:
                # Reject other options
                if opt in self._his_opts:
                    self._his_opts.remove(opt)
                self.send_raw(bytes([IAC, DONT, opt]))

        elif cmd == DO:
            # Server asks: Please DO use option
            if opt == OPT_SGA:
                if opt not in self._my_opts:
                    self._my_opts.add(opt)
                    self.send_raw(bytes([IAC, WILL, OPT_SGA]))

            elif opt == OPT_BINARY:
                if opt not in self._my_opts:
                    self._my_opts.add(opt)
                    self.send_raw(bytes([IAC, WILL, OPT_BINARY]))

            elif opt == OPT_NAWS:
                # Window size negotiation (RFC 1073)
                if opt not in self._my_opts:
                    self._my_opts.add(opt)
                    self.send_raw(bytes([IAC, WILL, OPT_NAWS]))
                # Send current window size
                naws_payload = bytes([
                    IAC, SB, OPT_NAWS,
                    (self.cols >> 8) & 0xFF, self.cols & 0xFF,
                    (self.rows >> 8) & 0xFF, self.rows & 0xFF,
                    IAC, SE
                ])
                self.send_raw(naws_payload)

            elif opt == OPT_TTYPE:
                # Terminal type negotiation (RFC 1091)
                if opt not in self._my_opts:
                    self._my_opts.add(opt)
                    self.send_raw(bytes([IAC, WILL, OPT_TTYPE]))

            else:
                # Refuse any other client option
                self.send_raw(bytes([IAC, WONT, opt]))

        elif cmd == WONT:
            # Server says: I WONT use option
            if opt in self._his_opts:
                self._his_opts.remove(opt)
                self.send_raw(bytes([IAC, DONT, opt]))

        elif cmd == DONT:
            # Server says: You DONT use option
            if opt in self._my_opts:
                self._my_opts.remove(opt)
                self.send_raw(bytes([IAC, WONT, opt]))

    def _handle_subnegotiation(self, payload: bytes) -> None:
        """Handles subnegotiation payloads (e.g., TTYPE SEND query)."""
        if not payload:
            return

        opt = payload[0]
        if opt == OPT_TTYPE and len(payload) > 1 and payload[1] == 1:
            # Server sends: IAC SB TTYPE 1 (SEND) IAC SE
            # Client responds: IAC SB TTYPE 0 (IS) "VT100" IAC SE
            reply = bytes([IAC, SB, OPT_TTYPE, 0]) + self.terminal_type.encode("ascii") + bytes([IAC, SE])
            self.send_raw(reply)

    def send(self, data: bytes) -> None:
        """Sends data escaping any 0xFF characters according to Telnet protocol."""
        if not data or not self.sock or not self._connected:
            return

        # Double any 0xFF bytes for Telnet escape
        escaped = data.replace(b"\xff", b"\xff\xff")
        self.send_raw(escaped)

    def send_raw(self, raw_bytes: bytes) -> None:
        """Thread-safe raw socket transmission."""
        if not self.sock or not self._connected:
            return

        with self._send_lock:
            try:
                self.sock.sendall(raw_bytes)
                self._last_activity = time.time()
            except Exception:
                self.disconnect()

    def disconnect(self) -> None:
        """Graceful disconnection."""
        self._stop_event.set()
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
