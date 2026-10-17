"""
SecureCRT 'crt' Scripting Object Model Facade for Python 3.
Implements crt.Screen, crt.Session, crt.Dialog, crt.GetScriptTab()
enabling execution of existing SecureCRT automation scripts.
"""

import time
import queue
from typing import Optional, List, Union, Callable


class ScreenShim:
    """Emulates crt.Screen / objTab.Screen."""

    def __init__(self, send_fn: Callable[[bytes], None], get_buffer_fn: Callable[[], str]):
        self._send_fn = send_fn
        self._get_buffer_fn = get_buffer_fn
        self._rx_queue: queue.Queue = queue.Queue()

        self.Synchronous: bool = False
        self.IgnoreEscape: bool = False
        self.CurrentRow: int = 1
        self.CurrentColumn: int = 1

    def feed_rx(self, text: str) -> None:
        """Called whenever data is received from the backend."""
        self._rx_queue.put(text)

    def Send(self, text: str) -> None:
        """Sends string data to the session."""
        self._send_fn(text.encode("utf-8"))

    def WaitForString(self, target: str, timeout: int = 0) -> bool:
        """Waits until target string is received, or until timeout expires."""
        start_time = time.time()
        accumulated = ""

        while True:
            try:
                chunk = self._rx_queue.get(timeout=0.1)
                accumulated += chunk
                if target in accumulated:
                    return True
            except queue.Empty:
                pass

            if timeout > 0 and (time.time() - start_time) >= timeout:
                return False

    def WaitForStrings(self, targets: List[str], timeout: int = 0) -> int:
        """Waits for any string in targets; returns 1-based index of matched target, or 0 on timeout."""
        start_time = time.time()
        accumulated = ""

        while True:
            try:
                chunk = self._rx_queue.get(timeout=0.1)
                accumulated += chunk
                for idx, t in enumerate(targets):
                    if t in accumulated:
                        return idx + 1
            except queue.Empty:
                pass

            if timeout > 0 and (time.time() - start_time) >= timeout:
                return 0

    def ReadString(self, end_string: str, timeout: int = 0) -> str:
        """Captures text from screen until end_string is encountered."""
        start_time = time.time()
        captured = ""

        while True:
            try:
                chunk = self._rx_queue.get(timeout=0.1)
                captured += chunk
                if end_string in captured:
                    pos = captured.find(end_string)
                    return captured[:pos]
            except queue.Empty:
                pass

            if timeout > 0 and (time.time() - start_time) >= timeout:
                return captured


class SessionShim:
    """Emulates crt.Session / objTab.Session."""

    def __init__(self, session_name: str = "Default"):
        self.Path: str = session_name
        self.Connected: bool = True
        self.Logging: bool = False
        self.LogFileName: str = ""

    def Connect(self, cmd: str) -> None:
        pass

    def Disconnect(self) -> None:
        self.Connected = False

    def Log(self, start: bool = True, append: bool = True, raw: bool = False) -> None:
        self.Logging = start


class DialogShim:
    """Emulates crt.Dialog."""

    def MessageBox(self, prompt: str, title: str = "SecureCRT", icon: int = 0) -> int:
        print(f"[{title}] {prompt}")
        return 1  # IDOK

    def Prompt(self, prompt: str, title: str = "SecureCRT", default: str = "", is_password: bool = False) -> str:
        return default


class TabShim:
    """Emulates crt.GetScriptTab() return object."""

    def __init__(self, screen: ScreenShim, session: SessionShim):
        self.Screen = screen
        self.Session = session


class CrtFacade:
    """Top-level 'crt' global object injected into user automation scripts."""

    def __init__(self, screen: ScreenShim, session: SessionShim):
        self.Screen = screen
        self.Session = session
        self.Dialog = DialogShim()
        self.Arguments: List[str] = []
        self.Version: str = "7.1.1 (Debian 64-bit Compatible)"
        self._tab = TabShim(screen, session)

    def GetScriptTab(self) -> TabShim:
        return self._tab

    def Sleep(self, milliseconds: int) -> None:
        time.sleep(milliseconds / 1000.0)


def execute_script(script_path: str, crt_obj: CrtFacade) -> None:
    """Executes a Python automation script in an isolated namespace with 'crt' pre-injected."""
    with open(script_path, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    namespace = {"crt": crt_obj, "__file__": script_path}
    exec(code, namespace)
    if "Main" in namespace and callable(namespace["Main"]):
        namespace["Main"]()
