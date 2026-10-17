"""
Application Entrypoint & Single-Instance IPC Manager.
Ensures that all connections (e.g., GNS3/EVE-NG opening R1, R2, R3) open in the SAME window.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        QT_API = "PySide6"
    except ImportError:
        QApplication = None
        QT_API = None

from .config_parser import SecureCRTConfigManager
from .ui.main_window import MainWindow

IPC_SERVER_NAME = "eveterminal_single_instance_ipc"


def parse_securecrt_cli_args(argv: List[str]) -> Dict[str, Any]:
    """
    Parses CLI arguments compatible with SecureCRT flags:
    /T (open in tab), /N <title> (session title: R1, R2, R3),
    /SSH2, /TELNET, /SERIAL, /S <session>, and URL schemes.
    """
    params: Dict[str, Any] = {
        "title": None,
        "protocol": "SSH2",
        "hostname": "",
        "port": 22,
        "serial_port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "username": "",
        "open_in_tab": True,
        "layout": None,  # Can request "rows", "columns", "tabs"
    }

    i = 1
    n = len(argv)
    while i < n:
        arg = argv[i]
        upper = arg.upper()

        if upper in ("/T", "--TAB"):
            params["open_in_tab"] = True
        elif upper.startswith("/N:") or upper.startswith("-N:") or upper.startswith("/T:"):
            params["title"] = arg.split(":", 1)[1].strip()
        elif upper.startswith("/N=") or upper.startswith("-N=") or upper.startswith("/TITLE="):
            params["title"] = arg.split("=", 1)[1].strip()
        elif upper in ("/N", "-N", "--NAME", "-T", "-TITLE", "--TITLE") and i + 1 < n:
            params["title"] = argv[i + 1]
            i += 1
        elif upper in ("/ROWS", "--ROWS"):
            params["layout"] = "rows"
        elif upper in ("/COLS", "--COLUMNS"):
            params["layout"] = "columns"
        elif upper in ("/TELNET", "-TELNET") and i + 1 < n:
            params["protocol"] = "Telnet"
            params["hostname"] = argv[i + 1]
            params["port"] = 23
            i += 1
            if i + 1 < n and argv[i + 1].isdigit():
                params["port"] = int(argv[i + 1])
                i += 1
        elif upper in ("/SSH2", "-SSH2") and i + 1 < n:
            params["protocol"] = "SSH2"
            params["hostname"] = argv[i + 1]
            params["port"] = 22
            i += 1
            if i + 1 < n and argv[i + 1].isdigit():
                params["port"] = int(argv[i + 1])
                i += 1
        elif upper in ("/SERIAL", "-SERIAL") and i + 1 < n:
            params["protocol"] = "Serial"
            params["serial_port"] = argv[i + 1]
            i += 1
            if i + 1 < n and argv[i + 1].isdigit():
                params["baudrate"] = int(argv[i + 1])
                i += 1
        elif upper.startswith("TELNET://"):
            params["protocol"] = "Telnet"
            raw_url = arg[9:].strip("/")
            # Check for URL fragment (#R1)
            if "#" in raw_url:
                hostpart, fragment = raw_url.split("#", 1)
                if fragment and not params.get("title"):
                    params["title"] = fragment.strip("/")
            else:
                hostpart = raw_url

            # Check for URL query (?title=R1 or ?name=R1)
            if "?" in hostpart:
                hostpart, query = hostpart.split("?", 1)
                for qpart in query.split("&"):
                    if "=" in qpart:
                        k, v = qpart.split("=", 1)
                        if k.lower() in ("title", "name", "node", "router") and not params.get("title"):
                            params["title"] = v.strip()

            # Check for path element (host:port/R1)
            if "/" in hostpart:
                h_parts = hostpart.split("/", 1)
                hostpart = h_parts[0]
                if len(h_parts) > 1 and h_parts[1] and not params.get("title"):
                    params["title"] = h_parts[1].strip()

            if ":" in hostpart:
                h, p = hostpart.split(":", 1)
                p = p.strip("/")
                params["hostname"] = h
                params["port"] = int(p) if p.isdigit() else 23
            elif " " in hostpart:
                h, p = hostpart.split(" ", 1)
                p = p.strip("/")
                params["hostname"] = h
                params["port"] = int(p) if p.isdigit() else 23
            else:
                params["hostname"] = hostpart
                params["port"] = 23
        elif upper.startswith("SSH://"):
            params["protocol"] = "SSH2"
            raw_url = arg[6:].strip("/")
            if "#" in raw_url:
                hostpart, fragment = raw_url.split("#", 1)
                if fragment and not params.get("title"):
                    params["title"] = fragment.strip("/")
            else:
                hostpart = raw_url
            if "?" in hostpart:
                hostpart, query = hostpart.split("?", 1)
                for qpart in query.split("&"):
                    if "=" in qpart:
                        k, v = qpart.split("=", 1)
                        if k.lower() in ("title", "name", "node", "router") and not params.get("title"):
                            params["title"] = v.strip()
            if "@" in hostpart:
                u, hostpart = hostpart.split("@", 1)
                params["username"] = u
            if ":" in hostpart:
                h, p = hostpart.split(":", 1)
                p = p.strip("/")
                params["hostname"] = h
                params["port"] = int(p) if p.isdigit() else 22
            else:
                params["hostname"] = hostpart
                params["port"] = 22
        elif not arg.startswith("/") and not arg.startswith("-"):
            # Plain host or host:port or host port
            if not params["hostname"]:
                clean_arg = arg.strip("/")
                if ":" in clean_arg:
                    h, p = clean_arg.split(":", 1)
                    p = p.strip("/")
                    params["hostname"] = h
                    params["port"] = int(p) if p.isdigit() else 23
                    params["protocol"] = "Telnet" if params["port"] != 22 else "SSH2"
                else:
                    params["hostname"] = clean_arg
                    if i + 1 < n and argv[i + 1].strip("/").isdigit():
                        params["port"] = int(argv[i + 1].strip("/"))
                        params["protocol"] = "Telnet" if params["port"] != 22 else "SSH2"
                        i += 1
        i += 1

    return params


def send_to_running_instance(params: Dict[str, Any]) -> bool:
    """Tries to send launch parameters to an already-running instance over IPC."""
    if not QT_API:
        return False

    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if socket.waitForConnected(1000):
        payload = json.dumps(params).encode("utf-8")
        socket.write(payload)
        socket.flush()
        socket.waitForBytesWritten(1000)
        # Wait for acknowledgment so socket isn't closed before server processes it
        socket.waitForReadyRead(1000)
        socket.disconnectFromServer()
        return True
    return False


class SingleInstanceServer:
    """Listens for commands from secondary processes and forwards to MainWindow."""

    def __init__(self, main_window: MainWindow):
        self.window = main_window
        self.server = QLocalServer()
        # Clean up stale socket file if needed
        QLocalServer.removeServer(IPC_SERVER_NAME)
        self.server.listen(IPC_SERVER_NAME)
        self.server.newConnection.connect(self._handle_client)

    def _handle_client(self) -> None:
        client = self.server.nextPendingConnection()
        if not client:
            return
        if client.waitForReadyRead(1000):
            data = client.readAll().data().decode("utf-8", errors="replace")
            try:
                params = json.loads(data)
                self.window.create_session_from_params(params)
                if params.get("layout"):
                    self.window.set_layout_mode(params["layout"])
                self.window.show()
                self.window.raise_()
                self.window.activateWindow()
                client.write(b"ACK\n")
                client.flush()
                client.waitForBytesWritten(500)
            except Exception as e:
                print(f"[IPC Error] {e}")
        client.disconnectFromServer()


def main() -> int:
    params = parse_securecrt_cli_args(sys.argv)

    # Check if another window instance is already running
    # If so, forward parameters to it so new terminals open in the SAME window!
    if send_to_running_instance(params):
        print(f"[Client] Forwarded connection to existing window.")
        return 0

    if not QT_API:
        print("Error: PyQt6 or PySide6 is required on Debian (run 'apt install python3-pyqt6').")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("SecureCRT-Linux")

    config_mgr = SecureCRTConfigManager()
    window = MainWindow(config_mgr)

    # Start single-instance IPC listener
    ipc_server = SingleInstanceServer(window)

    # Initial session from CLI if provided
    if params.get("hostname"):
        window.create_session_from_params(params)
    if params.get("layout"):
        window.set_layout_mode(params["layout"])

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
