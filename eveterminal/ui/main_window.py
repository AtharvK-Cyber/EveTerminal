"""
Main Application Window for Debian 64-bit Terminal Client.
Enforces single-window execution with flexible Tabbed or Tiled (Rows/Columns: R1, R2, R3) layouts.
"""

import os
import sys
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
        QFileDialog, QApplication, QLabel, QInputDialog
    )
    from PyQt6.QtGui import QAction, QIcon, QKeySequence
    from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import (
            QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
            QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
            QFileDialog, QApplication, QLabel, QInputDialog
        )
        from PySide6.QtGui import QAction, QIcon, QKeySequence
        from PySide6.QtCore import Qt, Slot as pyqtSlot, Signal as pyqtSignal
        QT_API = "PySide6"
    except ImportError:
        QMainWindow = object
        QT_API = None

import threading
from ..config_parser import SecureCRTConfigManager
from ..terminal.terminal_widget import TerminalWidget
from ..protocols.ssh_backend import SSHConnection
from ..protocols.serial_backend import SerialConnection
from ..protocols.telnet_backend import TelnetConnection
from ..protocols.pty_backend import PtyConnection
from .session_tree_dock import SessionTreeDock
from .quick_connect_dialog import QuickConnectDialog
from .button_bar import ButtonBar


class SessionTab(QWidget if QT_API else object):
    """Holds a terminal widget, connection backend, and active logging file."""

    sig_data_received = pyqtSignal(bytes) if QT_API else None
    sig_disconnected = pyqtSignal() if QT_API else None
    sig_title_changed = pyqtSignal(str) if QT_API else None

    # Prompt regex for Cisco IOS / network devices: e.g. R1#, R2>, R3(config)#, Switch#
    PROMPT_REGEX = re.compile(r'(?:^|[\r\n])\s*([A-Za-z0-9_\-\.]+)(?:\([^\)]+\))?[>#]\s*$')
    PROMPT_BLACKLIST = {
        "password", "enter", "confirm", "username", "login", "more",
        "line", "radius", "tacacs", "error", "warning", "info", "debug"
    }

    def __init__(self, title: str, connection, config: Dict[str, Any], auto_detect_title: bool = False, parent=None):
        if not QT_API:
            return
        super().__init__(parent)
        self.title = title
        self.connection = connection
        self.config = config
        self.auto_detect_title = auto_detect_title
        self.log_file = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar for Tiled Rows / Columns (R1, R2, R3 format)
        self.header_bar = QLabel(f"  ● {self.title}")
        self.header_bar.setStyleSheet(
            "background-color: #21252b; color: #61afef; font-weight: bold; "
            "padding: 3px 8px; font-size: 11px; border-bottom: 1px solid #3c3f41;"
        )
        self.header_bar.hide()  # Hidden by default in tabbed mode
        layout.addWidget(self.header_bar)

        # Create terminal widget
        color_scheme = config.get("Color Scheme", "Traditional")
        cols = config.get("Cols", 80)
        rows = config.get("Rows", 24)
        self.terminal = TerminalWidget(cols=cols, rows=rows, color_scheme_name=color_scheme)
        layout.addWidget(self.terminal)

        # Wire title changes from VT sequence \x1b]0;Title\x07
        if self.terminal.title_changed:
            self.terminal.title_changed.connect(self.set_title)

        # Wire user input directly
        self.terminal.data_to_send.connect(self._on_user_input)

        # Wire remote backend data safely across threads via Qt QueuedConnection
        # This prevents GUI crashes and socket aborts when multiple tabs/routers are active
        if QT_API:
            self.sig_data_received.connect(self._on_remote_data, Qt.ConnectionType.QueuedConnection)
            self.sig_disconnected.connect(self._on_disconnected, Qt.ConnectionType.QueuedConnection)

        self.connection.on_data_received = self._emit_data
        self.connection.on_disconnected = self._emit_disconnected

        # Setup logging if configured
        log_path_template = config.get("Log Filename", "")
        if log_path_template and config.get("Start Log Upon Connect", 0):
            self.start_logging(log_path_template)

    def set_title(self, new_title: str) -> None:
        """Updates tab label, row header, and emits title changed signal."""
        if not new_title or new_title == self.title:
            return
        self.title = new_title
        if hasattr(self, "header_bar"):
            self.header_bar.setText(f"  ● {new_title}")
        if QT_API and self.sig_title_changed:
            self.sig_title_changed.emit(new_title)

    def _detect_hostname_from_stream(self, data: bytes) -> None:
        """Parses router prompt (e.g., R1#, R2>, R3(config)#) and auto-syncs tab title."""
        try:
            text = data.decode("utf-8", errors="ignore")
            m = self.PROMPT_REGEX.search(text)
            if m:
                detected = m.group(1).strip()
                if (
                    len(detected) >= 2
                    and not detected.isdigit()
                    and detected.lower() not in self.PROMPT_BLACKLIST
                ):
                    self.set_title(detected)
        except Exception:
            pass

    def _emit_data(self, data: bytes) -> None:
        if QT_API and self.sig_data_received:
            self.sig_data_received.emit(data)

    def _emit_disconnected(self) -> None:
        if QT_API and self.sig_disconnected:
            self.sig_disconnected.emit()

    def start_logging(self, template: str) -> None:
        """Expands %Y, %M, %D, %h, %m, %s timestamp tokens and opens log stream."""
        now = datetime.now()
        resolved = template.replace("%Y", now.strftime("%Y")) \
                           .replace("%M", now.strftime("%m")) \
                           .replace("%D", now.strftime("%d")) \
                           .replace("%h", now.strftime("%H")) \
                           .replace("%m", now.strftime("%M")) \
                           .replace("%s", now.strftime("%S")) \
                           .replace("%S", self.title)
        os.makedirs(os.path.dirname(os.path.abspath(resolved)), exist_ok=True)
        self.log_file = open(resolved, "a", encoding="utf-8", errors="replace")

    def _on_user_input(self, data: bytes) -> None:
        if self.connection and self.connection.is_connected:
            self.connection.send(data)

    def _on_remote_data(self, data: bytes) -> None:
        self.terminal.feed_data(data)
        if self.auto_detect_title:
            self._detect_hostname_from_stream(data)
        if self.log_file:
            self.log_file.write(data.decode("utf-8", errors="replace"))
            self.log_file.flush()

    def _on_disconnected(self) -> None:
        self.terminal.feed_data(b"\r\n[Disconnected from remote host]\r\n")
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def close(self) -> None:
        if self.connection:
            self.connection.disconnect()
        if self.log_file:
            self.log_file.close()


class MainWindow(QMainWindow if QT_API else object):
    """Main application window supporting multi-tab and tiled row layouts."""

    def __init__(self, config_manager: Optional[SecureCRTConfigManager] = None):
        if not QT_API:
            return
        super().__init__()
        self.config_mgr = config_manager or SecureCRTConfigManager()
        self.setWindowTitle("EveTerminal")
        self.resize(1024, 720)

        # Sessions tracking
        self.active_sessions: List[SessionTab] = []
        self.layout_mode = "tabs"  # Options: "tabs", "rows", "columns", "grid"

        # Central container
        self.central_container = QWidget()
        self.central_layout = QVBoxLayout(self.central_container)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.central_container)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self._show_tab_context_menu)
        self.central_layout.addWidget(self.tab_widget)

        # Splitter for tiling mode (r1, r2, r3 rows)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.hide()
        self.central_layout.addWidget(self.splitter)

        # Dockable Session Tree sidebar
        self.session_dock = SessionTreeDock(self.config_mgr.sessions, self)
        self.session_dock.session_selected.connect(self.connect_session)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.session_dock)

        # Bottom Button Bar
        self.button_bar = ButtonBar(self)
        self.button_bar.send_macro.connect(self._send_macro_to_active)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, QToolBar("Button Bar", self))
        self.findChild(QToolBar).addWidget(self.button_bar)

        # Status Bar
        self.setStatusBar(QStatusBar())

        # Menu bar
        self._create_menus()

    def _create_menus(self) -> None:
        menubar = self.menuBar()

        # --- File Menu ---
        file_menu = menubar.addMenu("&File")

        act_quick = QAction("&Quick Connect...", self)
        act_quick.setShortcut(QKeySequence("Alt+Q"))
        act_quick.triggered.connect(self.open_quick_connect)
        file_menu.addAction(act_quick)

        act_connect = QAction("&Connect...", self)
        act_connect.setShortcut(QKeySequence("Alt+C"))
        act_connect.triggered.connect(lambda: self.session_dock.show())
        file_menu.addAction(act_connect)

        file_menu.addSeparator()

        act_clone = QAction("Cl&one Current Session", self)
        act_clone.setShortcut(QKeySequence("Alt+B"))
        act_clone.triggered.connect(self._clone_active_session)
        file_menu.addAction(act_clone)

        act_disconnect = QAction("&Disconnect", self)
        act_disconnect.triggered.connect(self._disconnect_active)
        file_menu.addAction(act_disconnect)

        file_menu.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # --- View Menu ---
        view_menu = menubar.addMenu("&View")

        act_dock = self.session_dock.toggleViewAction()
        act_dock.setText("Session Manager Sidebar")
        view_menu.addAction(act_dock)

        view_menu.addSeparator()

        # Layout options: Tabbed vs Tiled Rows (R1, R2, R3 format)
        layout_menu = view_menu.addMenu("&Window Layout")

        act_tabs = QAction("Tabbed Layout", self)
        act_tabs.triggered.connect(lambda: self.set_layout_mode("tabs"))
        layout_menu.addAction(act_tabs)

        act_rows = QAction("Tile Horizontally (Rows: R1, R2, R3...)", self)
        act_rows.triggered.connect(lambda: self.set_layout_mode("rows"))
        layout_menu.addAction(act_rows)

        act_cols = QAction("Tile Vertically (Columns)", self)
        act_cols.triggered.connect(lambda: self.set_layout_mode("columns"))
        layout_menu.addAction(act_cols)

        # --- Script Menu ---
        script_menu = menubar.addMenu("&Script")
        act_run_script = QAction("&Run Script...", self)
        act_run_script.triggered.connect(self._run_script_dialog)
        script_menu.addAction(act_run_script)

    def set_layout_mode(self, mode: str) -> None:
        """
        Switches between Tabbed mode and Tiled Rows/Columns mode (e.g. R1, R2, R3 in same window).
        """
        self.layout_mode = mode
        if mode == "tabs":
            self.splitter.hide()
            # Move all sessions into tab widget
            for s in self.active_sessions:
                s.setParent(None)
                if hasattr(s, "header_bar"):
                    s.header_bar.hide()
                self.tab_widget.addTab(s, s.title)
            self.tab_widget.show()
        elif mode in ("rows", "columns"):
            self.tab_widget.hide()
            self.splitter.setOrientation(
                Qt.Orientation.Vertical if mode == "rows" else Qt.Orientation.Horizontal
            )
            # Clear splitter and re-add sessions as stacked rows/columns
            for s in self.active_sessions:
                s.setParent(None)
                if hasattr(s, "header_bar"):
                    s.header_bar.show()
                self.splitter.addWidget(s)
            self.splitter.show()

    def open_quick_connect(self) -> None:
        dlg = QuickConnectDialog(self)
        if dlg.exec():
            params = dlg.get_connection_params()
            self.create_session_from_params(params)

    def create_session_from_params(self, params: Dict[str, Any]) -> None:
        proto = params.get("protocol")
        hostname = params.get("hostname", "")
        port = params.get("port", 23 if proto == "Telnet" else 22)
        title = params.get("title")
        auto_detect_title = False
        if not title:
            auto_detect_title = True
            session_num = len(self.active_sessions) + 1
            if proto == "Telnet" or port not in (22, 23):
                title = f"R{session_num}"
            else:
                title = hostname or f"Session {session_num}"

        conn = None
        if proto == "SSH2":
            conn = SSHConnection(
                hostname=hostname,
                port=port,
                username=params.get("username", ""),
            )
        elif proto == "Telnet":
            conn = TelnetConnection(
                hostname=hostname,
                port=port,
            )
        elif proto == "Serial":
            conn = SerialConnection(
                port=params.get("serial_port", "/dev/ttyUSB0"),
                baudrate=params.get("baudrate", 9600),
            )
        elif proto == "Local Shell":
            conn = PtyConnection()

        if conn:
            config = self.config_mgr.default_session.copy()
            session = SessionTab(title, conn, config, auto_detect_title=auto_detect_title, parent=self)
            self.add_session(session)
            # Connect in a background thread so the GUI thread never freezes
            # and existing router sessions are not disrupted!
            threading.Thread(target=conn.connect, daemon=True).start()

    def connect_session(self, session_name: str, config: Dict[str, Any]) -> None:
        """Launches a saved session from config."""
        proto = config.get("Protocol Name", "SSH2")
        hostname = config.get("Hostname", "")
        port = config.get("[SSH2] Port", 22)
        username = config.get("Username", "")

        conn = None
        if proto == "SSH2":
            conn = SSHConnection(hostname=hostname, port=port, username=username)
        elif proto == "Telnet":
            conn = TelnetConnection(hostname=hostname, port=port)
        elif proto == "Serial":
            conn = SerialConnection()
        else:
            conn = PtyConnection()

        session = SessionTab(session_name, conn, config, auto_detect_title=False, parent=self)
        self.add_session(session)
        # Connect in a background thread
        threading.Thread(target=conn.connect, daemon=True).start()

    def add_session(self, session: SessionTab) -> None:
        """Adds a session to the current layout (Tab or Tiled Row/Column)."""
        self.active_sessions.append(session)
        if session.sig_title_changed:
            session.sig_title_changed.connect(lambda new_title, s=session: self.update_session_title(s, new_title))
        if self.layout_mode == "tabs":
            if hasattr(session, "header_bar"):
                session.header_bar.hide()
            idx = self.tab_widget.addTab(session, session.title)
            self.tab_widget.setCurrentIndex(idx)
        else:
            if hasattr(session, "header_bar"):
                session.header_bar.show()
            self.splitter.addWidget(session)
        session.terminal.setFocus()
        self.statusBar().showMessage(f"Connected: {session.title}", 3000)

    def update_session_title(self, session: SessionTab, new_title: str) -> None:
        """Synchronizes tab label and row header with updated session name."""
        if not new_title:
            return
        session.title = new_title
        idx = self.tab_widget.indexOf(session)
        if idx != -1:
            self.tab_widget.setTabText(idx, new_title)
        if hasattr(session, "header_bar"):
            session.header_bar.setText(f"  ● {new_title}")

    def _show_tab_context_menu(self, pos) -> None:
        """Context menu on right clicking a tab to rename, duplicate, or close."""
        idx = self.tab_widget.tabBar().tabAt(pos)
        if 0 <= idx < len(self.active_sessions):
            session = self.active_sessions[idx]
            menu = QMenu(self)
            act_rename = menu.addAction("Rename Tab...")
            act_clone = menu.addAction("Clone Session")
            menu.addSeparator()
            act_close = menu.addAction("Close Tab")
            action = menu.exec(self.tab_widget.mapToGlobal(pos))
            if action == act_rename:
                new_name, ok = QInputDialog.getText(self, "Rename Tab", "Enter new tab name:", text=session.title)
                if ok and new_name.strip():
                    session.auto_detect_title = False
                    self.update_session_title(session, new_name.strip())
            elif action == act_clone:
                self._clone_active_session()
            elif action == act_close:
                self._close_tab(idx)

    def _on_tab_changed(self, index: int) -> None:
        if 0 <= index < len(self.active_sessions):
            self.active_sessions[index].terminal.setFocus()

    def _close_tab(self, index: int) -> None:
        if 0 <= index < len(self.active_sessions):
            session = self.active_sessions.pop(index)
            session.close()
            self.tab_widget.removeTab(index)

    def _disconnect_active(self) -> None:
        session = self._get_active_session()
        if session and session.connection:
            session.connection.disconnect()

    def _clone_active_session(self) -> None:
        session = self._get_active_session()
        if session:
            # Re-instantiate identical connection in new tab
            self.create_session_from_params({
                "protocol": session.config.get("Protocol Name", "SSH2"),
                "hostname": session.config.get("Hostname", "localhost"),
                "port": session.config.get("[SSH2] Port", 22),
                "username": session.config.get("Username", ""),
                "title": f"{session.title} (Clone)",
            })

    def _get_active_session(self) -> Optional[SessionTab]:
        if self.layout_mode == "tabs":
            idx = self.tab_widget.currentIndex()
            if 0 <= idx < len(self.active_sessions):
                return self.active_sessions[idx]
        elif self.active_sessions:
            return self.active_sessions[0]
        return None

    def _send_macro_to_active(self, text: str) -> None:
        session = self._get_active_session()
        if session and session.connection and session.connection.is_connected:
            session.connection.send(text.encode("utf-8"))

    def _run_script_dialog(self) -> None:
        session = self._get_active_session()
        if not session:
            QMessageBox.warning(self, "No Active Session", "Open a terminal session before running a script.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select Automation Script", "", "Python Scripts (*.py);;All Files (*)")
        if path:
            from ..scripting.crt_shim import CrtFacade, ScreenShim, SessionShim, execute_script
            screen_shim = ScreenShim(session.connection.send, lambda: "")
            session_shim = SessionShim(session.title)
            crt_obj = CrtFacade(screen_shim, session_shim)

            # Route incoming data into screen shim queue
            prev_cb = session.connection.on_data_received
            def intercept(data: bytes):
                screen_shim.feed_rx(data.decode("utf-8", errors="replace"))
                if prev_cb:
                    prev_cb(data)
            session.connection.on_data_received = intercept

            import threading
            threading.Thread(target=execute_script, args=(path, crt_obj), daemon=True).start()
            self.statusBar().showMessage(f"Executing script: {os.path.basename(path)}", 5000)
