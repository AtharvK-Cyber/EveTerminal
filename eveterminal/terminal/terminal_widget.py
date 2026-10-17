"""
PyQt6 / PySide6 Terminal Screen Widget.
Renders the character grid with monospace font, scrollback handling,
cursor rendering, copy-on-select, right-click-to-paste, and key mapping.
"""

import sys
from typing import Optional, Callable
from .vt_parser import ScreenBuffer, VTParser
from .color_schemes import get_scheme

try:
    from PyQt6.QtWidgets import QWidget, QScrollBar, QHBoxLayout, QApplication
    from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent, QWheelEvent
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QEvent
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import QWidget, QScrollBar, QHBoxLayout, QApplication
        from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent, QWheelEvent
        from PySide6.QtCore import Qt, QTimer, Signal as pyqtSignal, QRect, QEvent
        QT_API = "PySide6"
    except ImportError:
        # Fallback dummy classes if running in non-GUI or test environment
        QWidget = object
        QT_API = None


class TerminalWidget(QWidget if QT_API else object):
    """Interactive GUI Terminal Canvas displaying the VT buffer."""

    data_to_send = pyqtSignal(bytes) if QT_API else None
    title_changed = pyqtSignal(str) if QT_API else None

    def __init__(
        self,
        cols: int = 80,
        rows: int = 24,
        font_family: str = "Monospace",
        font_size: int = 11,
        color_scheme_name: str = "Traditional",
        parent=None,
    ):
        if QT_API:
            super().__init__(parent)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.cols = cols
        self.rows = rows
        self.buffer = ScreenBuffer(cols, rows)
        self.parser = VTParser(self.buffer, on_title_change=self._on_title_change)

        self.color_scheme_name = color_scheme_name
        self.scheme = get_scheme(color_scheme_name)

        self.font_family = font_family
        self.font_size = font_size
        self.char_width = 9
        self.char_height = 18

        self.cursor_blink_visible = True
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False

        self.scroll_offset = 0  # 0 means view bottom (live grid)

        if QT_API:
            self._update_font_metrics()
            # Cursor blink timer
            self.blink_timer = QTimer(self)
            self.blink_timer.timeout.connect(self._toggle_cursor_blink)
            self.blink_timer.start(500)

    def _update_font_metrics(self) -> None:
        if not QT_API:
            return
        font = QFont(self.font_family, self.font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.font = font
        fm = QFontMetrics(font)
        self.char_width = fm.horizontalAdvance("W")
        self.char_height = fm.lineSpacing()
        self.setMinimumSize(self.cols * self.char_width, self.rows * self.char_height)

    def _toggle_cursor_blink(self) -> None:
        self.cursor_blink_visible = not self.cursor_blink_visible
        if QT_API:
            self.update()

    def _on_title_change(self, title: str) -> None:
        if QT_API and self.title_changed:
            self.title_changed.emit(title)

    def feed_data(self, data: bytes) -> None:
        """Receives raw data from backend connection (SSH/Serial/Telnet/PTY)."""
        text = data.decode("utf-8", errors="replace")
        self.parser.feed(text)
        if QT_API:
            self.update()

    def set_color_scheme(self, name: str) -> None:
        self.color_scheme_name = name
        self.scheme = get_scheme(name)
        if QT_API:
            self.update()

    def paintEvent(self, event) -> None:
        if not QT_API:
            return

        painter = QPainter(self)
        painter.setFont(self.font)

        bg_color = QColor(self.scheme["background"])
        default_fg = QColor(self.scheme["foreground"])
        cursor_color = QColor(self.scheme["cursor"])

        # Fill background
        painter.fillRect(self.rect(), bg_color)

        buf = self.parser.buffer
        grid = buf.grid

        # Render rows
        for r_idx in range(min(buf.rows, len(grid))):
            row = grid[r_idx]
            y = (r_idx + 1) * self.char_height - 4

            for c_idx in range(min(buf.cols, len(row))):
                cell = row[c_idx]
                x = c_idx * self.char_width

                # Cell background override
                if cell.bg or cell.reverse:
                    c_bg = QColor(cell.fg if cell.reverse else cell.bg)
                    painter.fillRect(QRect(x, r_idx * self.char_height, self.char_width, self.char_height), c_bg)

                # Cell foreground
                if cell.reverse:
                    fg = bg_color if not cell.bg else QColor(cell.bg)
                elif cell.fg:
                    fg = QColor(cell.fg)
                else:
                    fg = default_fg

                painter.setPen(fg)
                if cell.char and cell.char != " ":
                    painter.drawText(x, y, cell.char)

        # Draw cursor
        if self.parser.cursor_visible and self.cursor_blink_visible:
            cx = buf.cursor_x * self.char_width
            cy = buf.cursor_y * self.char_height
            painter.fillRect(QRect(cx, cy, self.char_width, self.char_height), cursor_color)
            # Re-draw char under cursor inverted
            if 0 <= buf.cursor_y < len(grid) and 0 <= buf.cursor_x < len(grid[buf.cursor_y]):
                under_char = grid[buf.cursor_y][buf.cursor_x].char
                if under_char and under_char != " ":
                    painter.setPen(bg_color)
                    painter.drawText(cx, (buf.cursor_y + 1) * self.char_height - 4, under_char)

    def focusNextPrevChild(self, next: bool) -> bool:
        """
        Prevent Qt focus engine from intercepting Tab and Shift+Tab.
        In terminal emulators, Tab must be transmitted to the remote shell/router
        (e.g., for Cisco IOS command autocompletion like 'show ip interface bri' -> Tab).
        """
        return False

    def event(self, event) -> bool:
        """
        Deliver Tab, Backtab, and navigation keys directly to keyPressEvent
        before Qt widget focus traversal consumes them.
        """
        if QT_API and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                self.keyPressEvent(event)
                return True
        return super().event(event) if QT_API else False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not QT_API:
            return

        key = event.key()
        text = event.text()
        modifiers = event.modifiers()

        # Handle arrow keys and functional keys with VT escape sequences
        seq = None
        if key == Qt.Key.Key_Up:
            seq = b"\x1b[A"
        elif key == Qt.Key.Key_Down:
            seq = b"\x1b[B"
        elif key == Qt.Key.Key_Right:
            seq = b"\x1b[C"
        elif key == Qt.Key.Key_Left:
            seq = b"\x1b[D"
        elif key == Qt.Key.Key_Home:
            seq = b"\x1b[1~"
        elif key == Qt.Key.Key_End:
            seq = b"\x1b[4~"
        elif key == Qt.Key.Key_PageUp:
            seq = b"\x1b[5~"
        elif key == Qt.Key.Key_PageDown:
            seq = b"\x1b[6~"
        elif key == Qt.Key.Key_Insert:
            seq = b"\x1b[2~"
        elif key == Qt.Key.Key_Delete:
            seq = b"\x1b[3~"
        elif key == Qt.Key.Key_F1:
            seq = b"\x1bOP"
        elif key == Qt.Key.Key_F2:
            seq = b"\x1bOQ"
        elif key == Qt.Key.Key_F3:
            seq = b"\x1bOR"
        elif key == Qt.Key.Key_F4:
            seq = b"\x1bOS"
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            seq = b"\r"
        elif key == Qt.Key.Key_Backspace:
            seq = b"\x7f"  # Standard Unix erase (DEL)
        elif key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                return
            seq = b"\t"
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            # Control combinations: Ctrl+A -> \x01, Ctrl+C -> \x03, etc.
            if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                seq = bytes([key - Qt.Key.Key_A + 1])
            elif key in (Qt.Key.Key_6, Qt.Key.Key_AsciiCircum):
                seq = b"\x1e"  # Cisco break sequence (Ctrl+^ / Ctrl+Shift+6)
            elif key == Qt.Key.Key_BracketLeft:
                seq = b"\x1b"
            elif key == Qt.Key.Key_Backslash:
                seq = b"\x1c"
            elif key == Qt.Key.Key_BracketRight:
                seq = b"\x1d"
            elif key in (Qt.Key.Key_Underscore, Qt.Key.Key_Minus):
                seq = b"\x1f"
            elif key in (Qt.Key.Key_Space, Qt.Key.Key_At):
                seq = b"\x00"

        if seq:
            self.data_to_send.emit(seq)
            event.accept()
        elif text:
            self.data_to_send.emit(text.encode("utf-8"))
            event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not QT_API:
            return

        self.setFocus()
        if event.button() == Qt.MouseButton.RightButton:
            # Right click paste
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                self.data_to_send.emit(text.encode("utf-8"))
        elif event.button() == Qt.MouseButton.LeftButton:
            col = event.pos().x() // self.char_width
            row = event.pos().y() // self.char_height
            self.selection_start = (col, row)
            self.selection_end = (col, row)
            self.is_selecting = True

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not QT_API or not self.is_selecting:
            return
        col = event.pos().x() // self.char_width
        row = event.pos().y() // self.char_height
        self.selection_end = (col, row)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not QT_API:
            return
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            # Copy on select
            self._copy_selection_to_clipboard()

    def _copy_selection_to_clipboard(self) -> None:
        if not QT_API or not self.selection_start or not self.selection_end:
            return
        (c1, r1), (c2, r2) = self.selection_start, self.selection_end
        if (r1, c1) > (r2, c2):
            (r1, c1), (r2, c2) = (r2, c2), (r1, c1)

        buf = self.parser.buffer
        lines = []
        for r in range(r1, min(r2 + 1, buf.rows)):
            row = buf.grid[r]
            start_col = c1 if r == r1 else 0
            end_col = (c2 + 1) if r == r2 else buf.cols
            line_chars = "".join(row[c].char for c in range(start_col, min(end_col, len(row))))
            lines.append(line_chars.rstrip())

        selected_text = "\n".join(lines)
        if selected_text:
            QApplication.clipboard().setText(selected_text)
