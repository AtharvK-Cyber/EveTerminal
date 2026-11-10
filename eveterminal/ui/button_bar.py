"""
Customizable Button Bar widget for terminal command macros.
Supports right-click context menu to trigger Command Window (Broadcast to all sessions).
"""

from typing import Callable, Optional, List, Tuple

try:
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QInputDialog, QMenu
    from PyQt6.QtGui import QAction, QContextMenuEvent
    from PyQt6.QtCore import Qt, pyqtSignal
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QInputDialog, QMenu
        from PySide6.QtGui import QAction, QContextMenuEvent
        from PySide6.QtCore import Qt, Signal as pyqtSignal
        QT_API = "PySide6"
    except ImportError:
        QWidget = object
        QT_API = None


class MacroButton(QPushButton if QT_API else object):
    """Button representing a macro command with right-click broadcast menu."""

    send_macro = pyqtSignal(str) if QT_API else None
    send_macro_all = pyqtSignal(str) if QT_API else None
    delete_requested = pyqtSignal(object) if QT_API else None

    def __init__(self, label: str, command: str, parent=None):
        if not QT_API:
            return
        super().__init__(label, parent)
        self.command = command
        self.clicked.connect(lambda: self.send_macro.emit(self.command))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos) -> None:
        if not QT_API:
            return
        menu = QMenu(self)
        act_active = menu.addAction(f"Send '{self.text()}' to Active Session")
        act_all = menu.addAction(f"📢 Broadcast '{self.text()}' to ALL Sessions")
        menu.addSeparator()
        act_del = menu.addAction("Remove Button")

        action = menu.exec(self.mapToGlobal(pos))
        if action == act_active:
            self.send_macro.emit(self.command)
        elif action == act_all:
            self.send_macro_all.emit(self.command)
        elif action == act_del:
            self.delete_requested.emit(self)


class ButtonBar(QWidget if QT_API else object):
    """Bottom toolbar with user-defined macro buttons and right-click broadcast triggers."""

    send_macro = pyqtSignal(str) if QT_API else None
    send_macro_all = pyqtSignal(str) if QT_API else None
    open_command_window = pyqtSignal(bool) if QT_API else None  # True = send_to_all

    DEFAULT_BUTTONS: List[Tuple[str, str]] = [
        ("show ip int br", "show ip interface brief\r\n"),
        ("show run", "show running-config\r\n"),
        ("conf t", "configure terminal\r\n"),
        ("wr mem", "write memory\r\n"),
        ("exit", "exit\r\n"),
        ("clear screen", "clear\r\n"),
    ]

    def __init__(self, parent=None):
        if not QT_API:
            return
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_bar_context_menu)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 2, 4, 2)
        self.layout.setSpacing(4)

        for label, cmd in self.DEFAULT_BUTTONS:
            self.add_button(label, cmd)

        self.layout.addStretch()

        # Add '+' button to allow user to add custom button
        add_btn = QPushButton("+")
        add_btn.setToolTip("Add new macro button")
        add_btn.setMaximumWidth(30)
        add_btn.clicked.connect(self._on_add_clicked)
        self.layout.addWidget(add_btn)

    def add_button(self, label: str, command: str) -> None:
        if not QT_API:
            return
        btn = MacroButton(label, command, self)
        btn.send_macro.connect(self.send_macro.emit)
        btn.send_macro_all.connect(self.send_macro_all.emit)
        btn.delete_requested.connect(self._remove_button)
        self.layout.insertWidget(self.layout.count() - 2, btn)

    def _remove_button(self, btn: MacroButton) -> None:
        self.layout.removeWidget(btn)
        btn.deleteLater()

    def _on_add_clicked(self) -> None:
        if not QT_API:
            return
        label, ok = QInputDialog.getText(self, "New Macro Button", "Button Label:")
        if ok and label:
            cmd, ok2 = QInputDialog.getText(self, "New Macro Button", "Command to Send:")
            if ok2 and cmd:
                self.add_button(label, cmd + "\r\n")

    def _show_bar_context_menu(self, pos) -> None:
        if not QT_API:
            return
        menu = QMenu(self)
        act_broadcast = menu.addAction("📢 Send Command to All Devices (Command Window)...")
        menu.addSeparator()
        act_add = menu.addAction("Add Macro Button...")

        action = menu.exec(self.mapToGlobal(pos))
        if action == act_broadcast:
            if self.open_command_window:
                self.open_command_window.emit(True)
        elif action == act_add:
            self._on_add_clicked()
