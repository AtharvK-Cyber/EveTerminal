"""
Command Window / Broadcast Bar for sending commands to multiple terminal sessions.
Emulates SecureCRT's Command Window feature for running commands across R1, R2, R3, etc.
"""

from typing import List, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QComboBox, QMenu, QDockWidget, QSizePolicy, QFrame
    )
    from PyQt6.QtGui import QAction, QFont, QKeySequence, QKeyEvent, QContextMenuEvent
    from PyQt6.QtCore import Qt, pyqtSignal
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
            QPushButton, QComboBox, QMenu, QDockWidget, QSizePolicy, QFrame
        )
        from PySide6.QtGui import QAction, QFont, QKeySequence, QKeyEvent, QContextMenuEvent
        from PySide6.QtCore import Qt, Signal as pyqtSignal
        QT_API = "PySide6"
    except ImportError:
        QWidget = object
        QDockWidget = object
        QT_API = None


class CommandLineEdit(QLineEdit if QT_API else object):
    """
    Terminal command line input with command history (Up/Down arrows)
    and right-click context menu to toggle broadcast mode.
    """

    close_requested = pyqtSignal() if QT_API else None
    mode_toggle_requested = pyqtSignal(bool) if QT_API else None

    def __init__(self, parent=None):
        if not QT_API:
            return
        super().__init__(parent)
        self.history: List[str] = []
        self.history_idx: int = -1
        self.current_stash: str = ""
        self.is_send_to_all: bool = True

        self.setStyleSheet(
            "QLineEdit {"
            "    background-color: #1e2227;"
            "    color: #abb2bf;"
            "    border: 1px solid #3c3f41;"
            "    border-radius: 4px;"
            "    padding: 6px 10px;"
            "    font-family: 'Consolas', 'DejaVu Sans Mono', 'Courier New', monospace;"
            "    font-size: 13px;"
            "}"
            "QLineEdit:focus {"
            "    border: 1px solid #61afef;"
            "}"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not QT_API:
            return

        key = event.key()
        if key == Qt.Key.Key_Up:
            # Navigate back in command history
            if not self.history:
                return
            if self.history_idx == -1:
                self.current_stash = self.text()
                self.history_idx = len(self.history) - 1
            elif self.history_idx > 0:
                self.history_idx -= 1
            self.setText(self.history[self.history_idx])
            event.accept()
            return
        elif key == Qt.Key.Key_Down:
            # Navigate forward in command history
            if self.history_idx == -1:
                return
            if self.history_idx < len(self.history) - 1:
                self.history_idx += 1
                self.setText(self.history[self.history_idx])
            else:
                self.history_idx = -1
                self.setText(self.current_stash)
            event.accept()
            return
        elif key == Qt.Key.Key_Escape:
            if self.text():
                self.clear()
            elif self.close_requested:
                self.close_requested.emit()
            event.accept()
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        if not QT_API:
            return
        menu = self.createStandardContextMenu()
        menu.addSeparator()

        act_all = menu.addAction("📢 Send Commands to All Sessions")
        act_all.setCheckable(True)
        act_all.setChecked(self.is_send_to_all)

        act_active = menu.addAction("🎯 Send Commands to Active Session Only")
        act_active.setCheckable(True)
        act_active.setChecked(not self.is_send_to_all)

        menu.addSeparator()
        act_clear_history = menu.addAction("Clear Command History")
        act_close = menu.addAction("Close Command Window")

        action = menu.exec(event.globalPos())
        if action == act_all:
            self.is_send_to_all = True
            if self.mode_toggle_requested:
                self.mode_toggle_requested.emit(True)
        elif action == act_active:
            self.is_send_to_all = False
            if self.mode_toggle_requested:
                self.mode_toggle_requested.emit(False)
        elif action == act_clear_history:
            self.history.clear()
            self.history_idx = -1
        elif action == act_close:
            if self.close_requested:
                self.close_requested.emit()


class CommandWindowWidget(QWidget if QT_API else object):
    """
    Bottom split screen command console allowing instant broadcasting
    to all active sessions or targeted to active session.
    """

    command_submitted = pyqtSignal(str, bool) if QT_API else None  # (cmd, send_to_all)
    close_requested = pyqtSignal() if QT_API else None

    def __init__(self, parent=None):
        if not QT_API:
            return
        super().__init__(parent)
        self.setStyleSheet("background-color: #21252b; color: #abb2bf;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 8)
        main_layout.setSpacing(6)

        # Header / Target control toolbar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Title Label
        title_lbl = QLabel("⚡ Command Window:")
        title_lbl.setStyleSheet("font-weight: bold; color: #61afef; font-size: 12px;")
        header_layout.addWidget(title_lbl)

        # Target Selector Dropdown
        self.target_combo = QComboBox()
        self.target_combo.addItems([
            "📢 Send to All Sessions (Broadcast)",
            "🎯 Send to Active Session Only"
        ])
        self.target_combo.setStyleSheet(
            "QComboBox {"
            "    background-color: #282c34;"
            "    color: #e5c07b;"
            "    font-weight: bold;"
            "    border: 1px solid #3c3f41;"
            "    border-radius: 3px;"
            "    padding: 3px 8px;"
            "    font-size: 11px;"
            "}"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView {"
            "    background-color: #282c34;"
            "    color: #abb2bf;"
            "    selection-background-color: #3e4451;"
            "}"
        )
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        header_layout.addWidget(self.target_combo)

        # Sessions Status Badge
        self.badge_lbl = QLabel("(0 connected sessions)")
        self.badge_lbl.setStyleSheet("color: #98c379; font-size: 11px;")
        header_layout.addWidget(self.badge_lbl)

        header_layout.addStretch()

        # Close button '✕'
        close_btn = QPushButton("✕")
        close_btn.setToolTip("Close Command Window (Esc)")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: transparent;"
            "    color: #5c6370;"
            "    border: none;"
            "    font-weight: bold;"
            "    font-size: 13px;"
            "}"
            "QPushButton:hover {"
            "    color: #e06c75;"
            "}"
        )
        close_btn.clicked.connect(self._on_close_clicked)
        header_layout.addWidget(close_btn)

        main_layout.addLayout(header_layout)

        # Command input row
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)

        self.input_edit = CommandLineEdit(self)
        self.input_edit.returnPressed.connect(self.submit_command)
        self.input_edit.close_requested.connect(self._on_close_clicked)
        self.input_edit.mode_toggle_requested.connect(self.set_send_to_all)
        input_layout.addWidget(self.input_edit)

        # Send Button
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #3e4451;"
            "    color: #61afef;"
            "    font-weight: bold;"
            "    border: 1px solid #4b5263;"
            "    border-radius: 4px;"
            "    padding: 6px 14px;"
            "    font-size: 12px;"
            "}"
            "QPushButton:hover {"
            "    background-color: #4b5263;"
            "    color: #98c379;"
            "}"
            "QPushButton:pressed {"
            "    background-color: #2c313a;"
            "}"
        )
        self.send_btn.clicked.connect(self.submit_command)
        input_layout.addWidget(self.send_btn)

        main_layout.addLayout(input_layout)

        # Default placeholder
        self._update_placeholder()

    def set_focus_to_input(self) -> None:
        if QT_API and hasattr(self, "input_edit"):
            self.input_edit.setFocus()
            self.input_edit.selectAll()

    def set_send_to_all(self, send_to_all: bool) -> None:
        idx = 0 if send_to_all else 1
        if self.target_combo.currentIndex() != idx:
            self.target_combo.setCurrentIndex(idx)
        else:
            self._update_placeholder()

    def _on_target_changed(self, index: int) -> None:
        is_all = (index == 0)
        self.input_edit.is_send_to_all = is_all
        if is_all:
            self.target_combo.setStyleSheet(
                "QComboBox {"
                "    background-color: #282c34;"
                "    color: #e5c07b;"
                "    font-weight: bold;"
                "    border: 1px solid #e5c07b;"
                "    border-radius: 3px;"
                "    padding: 3px 8px;"
                "    font-size: 11px;"
                "}"
            )
        else:
            self.target_combo.setStyleSheet(
                "QComboBox {"
                "    background-color: #282c34;"
                "    color: #61afef;"
                "    font-weight: bold;"
                "    border: 1px solid #3c3f41;"
                "    border-radius: 3px;"
                "    padding: 3px 8px;"
                "    font-size: 11px;"
                "}"
            )
        self._update_placeholder()

    def _update_placeholder(self) -> None:
        if self.target_combo.currentIndex() == 0:
            self.input_edit.setPlaceholderText(
                "Broadcast command to ALL sessions (R1, R2, R3...) - Press Enter to execute"
            )
        else:
            self.input_edit.setPlaceholderText(
                "Send command to active session only - Press Enter to execute"
            )

    def update_sessions_info(self, sessions_count: int, session_names: List[str], active_name: str = "") -> None:
        if not QT_API:
            return
        if sessions_count == 0:
            self.badge_lbl.setText("(0 sessions open)")
            self.badge_lbl.setStyleSheet("color: #e06c75; font-size: 11px;")
        elif self.target_combo.currentIndex() == 0:
            names_summary = ", ".join(session_names[:6])
            if len(session_names) > 6:
                names_summary += f", +{len(session_names)-6} more"
            self.badge_lbl.setText(f"({sessions_count} sessions: {names_summary})")
            self.badge_lbl.setStyleSheet("color: #98c379; font-size: 11px; font-weight: bold;")
        else:
            self.badge_lbl.setText(f"(Active: {active_name or 'None'})")
            self.badge_lbl.setStyleSheet("color: #61afef; font-size: 11px;")

    def submit_command(self) -> None:
        if not QT_API:
            return
        cmd = self.input_edit.text()
        if not cmd:
            return

        # Add to history if unique from previous
        if not self.input_edit.history or self.input_edit.history[-1] != cmd:
            self.input_edit.history.append(cmd)
        self.input_edit.history_idx = -1
        self.input_edit.current_stash = ""

        send_to_all = (self.target_combo.currentIndex() == 0)
        if self.command_submitted:
            self.command_submitted.emit(cmd, send_to_all)

        self.input_edit.clear()

    def _on_close_clicked(self) -> None:
        if self.close_requested:
            self.close_requested.emit()


class CommandWindowDock(QDockWidget if QT_API else object):
    """
    Dockable split screen bottom pane for Command Window.
    Can be docked at bottom, resized, floated, or toggled on/off.
    """

    command_submitted = pyqtSignal(str, bool) if QT_API else None

    def __init__(self, parent=None):
        if not QT_API:
            return
        super().__init__("Command Window (Broadcast)", parent)
        self.setObjectName("CommandWindowDock")
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)

        self.widget = CommandWindowWidget(self)
        self.widget.command_submitted.connect(self._on_cmd_submitted)
        self.widget.close_requested.connect(self.hide)
        self.setWidget(self.widget)

        self.setStyleSheet(
            "QDockWidget {"
            "    background-color: #21252b;"
            "    color: #abb2bf;"
            "    font-weight: bold;"
            "    font-size: 11px;"
            "}"
            "QDockWidget::title {"
            "    background-color: #21252b;"
            "    color: #61afef;"
            "    padding: 4px 8px;"
            "    border-top: 1px solid #3c3f41;"
            "    border-bottom: 1px solid #181a1f;"
            "}"
        )

    def _on_cmd_submitted(self, cmd: str, send_to_all: bool) -> None:
        if self.command_submitted:
            self.command_submitted.emit(cmd, send_to_all)

    def update_sessions_info(self, sessions_count: int, session_names: List[str], active_name: str = "") -> None:
        if hasattr(self, "widget"):
            self.widget.update_sessions_info(sessions_count, session_names, active_name)

    def set_send_to_all(self, send_to_all: bool) -> None:
        if hasattr(self, "widget"):
            self.widget.set_send_to_all(send_to_all)

    def focus_input(self) -> None:
        if hasattr(self, "widget"):
            self.widget.set_focus_to_input()
