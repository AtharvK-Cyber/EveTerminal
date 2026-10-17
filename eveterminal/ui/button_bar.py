"""
Customizable Button Bar widget for terminal command macros.
"""

from typing import Callable, Optional, List, Tuple

try:
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QInputDialog
    from PyQt6.QtCore import pyqtSignal
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QInputDialog
        from PySide6.QtCore import Signal as pyqtSignal
        QT_API = "PySide6"
    except ImportError:
        QWidget = object
        QT_API = None


class ButtonBar(QWidget if QT_API else object):
    """Bottom toolbar with user-defined macro buttons."""

    send_macro = pyqtSignal(str) if QT_API else None

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
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 2, 4, 2)
        self.layout.setSpacing(4)

        for label, cmd in self.DEFAULT_BUTTONS:
            self.add_button(label, cmd)

        self.layout.addStretch()

        # Add '+' button to allow user to add custom button
        add_btn = QPushButton("+")
        add_btn.setMaximumWidth(30)
        add_btn.clicked.connect(self._on_add_clicked)
        self.layout.addWidget(add_btn)

    def add_button(self, label: str, command: str) -> None:
        if not QT_API:
            return
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self.send_macro.emit(command))
        self.layout.insertWidget(self.layout.count() - 2, btn)

    def _on_add_clicked(self) -> None:
        if not QT_API:
            return
        label, ok = QInputDialog.getText(self, "New Macro Button", "Button Label:")
        if ok and label:
            cmd, ok2 = QInputDialog.getText(self, "New Macro Button", "Command to Send:")
            if ok2 and cmd:
                self.add_button(label, cmd + "\r\n")
