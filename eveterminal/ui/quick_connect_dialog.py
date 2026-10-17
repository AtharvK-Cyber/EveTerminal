"""
Quick Connect Dialog.
Allows rapid connection via SSH2, Telnet, Serial, or Local Shell.
"""

from typing import Optional, Dict, Any

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
        QLineEdit, QSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QLabel
    )
    from PyQt6.QtCore import Qt
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
            QLineEdit, QSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QLabel
        )
        from PySide6.QtCore import Qt
        QT_API = "PySide6"
    except ImportError:
        QDialog = object
        QT_API = None


class QuickConnectDialog(QDialog if QT_API else object):
    """Quick connect dialog matching SecureCRT's Alt+Q dialog."""

    def __init__(self, parent=None):
        if not QT_API:
            return
        super().__init__(parent)
        self.setWindowTitle("Quick Connect")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Protocol
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["SSH2", "Telnet", "Serial", "Local Shell"])
        self.protocol_combo.currentTextChanged.connect(self._on_protocol_changed)
        form.addRow("Protocol:", self.protocol_combo)

        # Hostname
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("e.g. 192.168.1.1 or router1.lab")
        form.addRow("Hostname / IP:", self.host_edit)

        # Port
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        form.addRow("Port:", self.port_spin)

        # Username
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username")
        form.addRow("Username:", self.user_edit)

        # Serial specific options
        self.serial_port_edit = QLineEdit("/dev/ttyUSB0")
        form.addRow("Serial Device:", self.serial_port_edit)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        form.addRow("Baud Rate:", self.baud_combo)

        # Open in tab option
        self.open_tab_check = QCheckBox("Open in a new tab")
        self.open_tab_check.setChecked(True)
        form.addRow("", self.open_tab_check)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_protocol_changed(self.protocol_combo.currentText())

    def _on_protocol_changed(self, protocol: str) -> None:
        is_net = protocol in ("SSH2", "Telnet")
        is_serial = (protocol == "Serial")
        is_ssh = (protocol == "SSH2")

        self.host_edit.setEnabled(is_net)
        self.port_spin.setEnabled(is_net)
        self.user_edit.setEnabled(is_ssh)

        self.serial_port_edit.setEnabled(is_serial)
        self.baud_combo.setEnabled(is_serial)

        if protocol == "SSH2":
            self.port_spin.setValue(22)
        elif protocol == "Telnet":
            self.port_spin.setValue(23)

    def get_connection_params(self) -> Dict[str, Any]:
        proto = self.protocol_combo.currentText()
        return {
            "protocol": proto,
            "hostname": self.host_edit.text().strip(),
            "port": self.port_spin.value(),
            "username": self.user_edit.text().strip(),
            "serial_port": self.serial_port_edit.text().strip(),
            "baudrate": int(self.baud_combo.currentText()),
            "open_in_tab": self.open_tab_check.isChecked(),
        }
