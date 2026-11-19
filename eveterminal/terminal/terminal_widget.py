"""
PyQt6 / PySide6 Terminal Screen Widget.
Renders the character grid with monospace font, scrollback handling,
vertical scrollbar, mouse wheel scrolling, visual selection highlight,
copy-on-select, right-click context menu, and keyboard navigation.
"""

import sys
from typing import Optional, Callable, List
from .vt_parser import ScreenBuffer, VTParser, Cell
from .color_schemes import get_scheme

try:
    from PyQt6.QtWidgets import QWidget, QScrollBar, QApplication, QMenu
    from PyQt6.QtGui import (
        QPainter, QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent,
        QWheelEvent, QKeySequence
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QEvent, QPoint
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import QWidget, QScrollBar, QApplication, QMenu
        from PySide6.QtGui import (
            QPainter, QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent,
            QWheelEvent, QKeySequence
        )
        from PySide6.QtCore import Qt, QTimer, Signal as pyqtSignal, QRect, QEvent, QPoint
        QT_API = "PySide6"
    except ImportError:
        QWidget = object
        QT_API = None


class TerminalWidget(QWidget if QT_API else object):
    """
    Interactive GUI Terminal Canvas displaying the VT buffer with
    full scrollback history, mouse wheel support, and visual selection/copy.
    """

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
        self.selection_start = None  # (col, row)
        self.selection_end = None    # (col, row)
        self.is_selecting = False

        self.scroll_offset = 0  # 0 means view bottom (live output)
        self.on_resize_callback: Optional[Callable[[int, int], None]] = None

        if QT_API:
            self._update_font_metrics()

            # Vertical Scrollbar on the right edge
            self.scrollbar = QScrollBar(Qt.Orientation.Vertical, self)
            self.scrollbar.setRange(0, 0)
            self.scrollbar.setValue(0)
            self.scrollbar.valueChanged.connect(self._on_scrollbar_value_changed)
            self.scrollbar.setStyleSheet("""
                QScrollBar:vertical {
                    background: #181a1f;
                    width: 12px;
                    margin: 0px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background: #3e4451;
                    min-height: 25px;
                    border-radius: 4px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #61afef;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)

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
        self.char_width = max(6, fm.horizontalAdvance("W"))
        self.char_height = max(12, fm.lineSpacing())
        self.setMinimumSize(self.char_width * 20, self.char_height * 5)

    def resizeEvent(self, event) -> None:
        if not QT_API:
            return
        super().resizeEvent(event)
        sb_w = 12
        if hasattr(self, "scrollbar"):
            self.scrollbar.setGeometry(self.width() - sb_w, 0, sb_w, self.height())

        avail_w = max(self.char_width * 10, self.width() - sb_w)
        avail_h = max(self.char_height * 4, self.height())
        new_cols = max(20, avail_w // self.char_width)
        new_rows = max(5, avail_h // self.char_height)

        if new_cols != self.cols or new_rows != self.rows:
            self.cols = new_cols
            self.rows = new_rows
            self.buffer.resize(new_cols, new_rows)
            if self.on_resize_callback:
                self.on_resize_callback(new_cols, new_rows)
            self._update_scrollbar()
            self.update()

    def _on_scrollbar_value_changed(self, value: int) -> None:
        max_val = self.scrollbar.maximum()
        self.scroll_offset = max(0, max_val - value)
        self.update()

    def _update_scrollbar(self) -> None:
        if not QT_API or not hasattr(self, "scrollbar"):
            return
        total_sb = len(self.parser.buffer.scrollback)
        self.scrollbar.blockSignals(True)
        self.scrollbar.setMaximum(total_sb)
        if self.scroll_offset == 0:
            self.scrollbar.setValue(total_sb)
        else:
            self.scrollbar.setValue(max(0, total_sb - self.scroll_offset))
        self.scrollbar.blockSignals(False)

    def scroll_by(self, delta_lines: int) -> None:
        """Positive delta scrolls down toward live output; negative scrolls up into history."""
        total_sb = len(self.parser.buffer.scrollback)
        new_offset = max(0, min(self.scroll_offset - delta_lines, total_sb))
        if new_offset != self.scroll_offset:
            self.scroll_offset = new_offset
            self._update_scrollbar()
            self.update()

    def scroll_to_bottom(self) -> None:
        """Snaps view directly to the live output."""
        if self.scroll_offset != 0:
            self.scroll_offset = 0
            self._update_scrollbar()
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Mouse wheel scrolling for terminal scrollback."""
        if not QT_API:
            return
        delta = event.angleDelta().y()
        lines = delta // 40  # 3 lines per standard wheel notch
        if lines != 0:
            self.scroll_by(lines)
        event.accept()

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
            # Automatically lock view to bottom so last output is always visible
            if self.scroll_offset == 0:
                self._update_scrollbar()
            else:
                total_sb = len(self.parser.buffer.scrollback)
                if hasattr(self, "scrollbar"):
                    self.scrollbar.blockSignals(True)
                    self.scrollbar.setMaximum(total_sb)
                    self.scrollbar.setValue(max(0, total_sb - self.scroll_offset))
                    self.scrollbar.blockSignals(False)
            self.update()

    def set_color_scheme(self, name: str) -> None:
        self.color_scheme_name = name
        self.scheme = get_scheme(name)
        if QT_API:
            self.update()

    def get_visible_row(self, row_idx: int) -> List[Cell]:
        """
        Returns the cells to render for visual screen row row_idx (0 to self.rows - 1),
        seamlessly blending the scrollback history buffer and active screen grid.
        """
        buf = self.parser.buffer
        sb = buf.scrollback
        total_rows = len(sb) + len(buf.grid)

        virtual_idx = total_rows - self.rows - self.scroll_offset + row_idx
        if virtual_idx < 0:
            return [Cell() for _ in range(buf.cols)]
        elif virtual_idx < len(sb):
            return sb[virtual_idx]
        else:
            grid_idx = virtual_idx - len(sb)
            if grid_idx < len(buf.grid):
                return buf.grid[grid_idx]
            else:
                return [Cell() for _ in range(buf.cols)]

    def has_selection(self) -> bool:
        return (
            self.selection_start is not None
            and self.selection_end is not None
            and self.selection_start != self.selection_end
        )

    def clear_selection(self) -> None:
        self.selection_start = None
        self.selection_end = None
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
        selection_bg = QColor("#264f78")  # Highlight selection background
        selection_fg = QColor("#ffffff")

        # Fill background
        painter.fillRect(self.rect(), bg_color)

        buf = self.parser.buffer

        # Calculate normalized selection coordinates
        has_sel = self.has_selection()
        if has_sel:
            (sc1, sr1), (sc2, sr2) = self.selection_start, self.selection_end
            if (sr1, sc1) > (sr2, sc2):
                (sc1, sr1), (sc2, sr2) = (sc2, sr2), (sc1, sr1)

        # Render rows
        for r_idx in range(self.rows):
            row = self.get_visible_row(r_idx)
            y = (r_idx + 1) * self.char_height - 4

            is_row_in_sel = has_sel and (sr1 <= r_idx <= sr2)

            for c_idx in range(min(self.cols, len(row))):
                cell = row[c_idx]
                x = c_idx * self.char_width

                # Determine if this cell is highlighted
                is_selected = False
                if is_row_in_sel:
                    if sr1 == sr2:
                        is_selected = (sc1 <= c_idx <= sc2)
                    elif r_idx == sr1:
                        is_selected = (c_idx >= sc1)
                    elif r_idx == sr2:
                        is_selected = (c_idx <= sc2)
                    else:
                        is_selected = True

                if is_selected:
                    # Highlight selection rectangle
                    painter.fillRect(QRect(x, r_idx * self.char_height, self.char_width, self.char_height), selection_bg)
                    painter.setPen(selection_fg)
                else:
                    # Normal cell background override
                    if cell.bg or cell.reverse:
                        c_bg = QColor(cell.fg if cell.reverse else cell.bg)
                        painter.fillRect(QRect(x, r_idx * self.char_height, self.char_width, self.char_height), c_bg)

                    # Normal cell foreground
                    if cell.reverse:
                        fg = bg_color if not cell.bg else QColor(cell.bg)
                    elif cell.fg:
                        fg = QColor(cell.fg)
                    else:
                        fg = default_fg
                    painter.setPen(fg)

                if cell.char and cell.char != " ":
                    painter.drawText(x, y, cell.char)

        # Draw cursor only when viewing live output (scroll_offset == 0)
        if self.scroll_offset == 0 and self.parser.cursor_visible and self.cursor_blink_visible:
            cx = buf.cursor_x * self.char_width
            cy = buf.cursor_y * self.char_height
            painter.fillRect(QRect(cx, cy, self.char_width, self.char_height), cursor_color)
            if 0 <= buf.cursor_y < len(buf.grid) and 0 <= buf.cursor_x < len(buf.grid[buf.cursor_y]):
                under_char = buf.grid[buf.cursor_y][buf.cursor_x].char
                if under_char and under_char != " ":
                    painter.setPen(bg_color)
                    painter.drawText(cx, (buf.cursor_y + 1) * self.char_height - 4, under_char)

    def focusNextPrevChild(self, next: bool) -> bool:
        """Prevent Qt focus engine from intercepting Tab and Shift+Tab."""
        return False

    def event(self, event) -> bool:
        """Deliver Tab, Backtab, and navigation keys directly to keyPressEvent."""
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

        # Scrolling shortcuts
        if key == Qt.Key.Key_PageUp and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.scroll_by(max(1, self.rows // 2))
            event.accept()
            return
        elif key == Qt.Key.Key_PageDown and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.scroll_by(-max(1, self.rows // 2))
            event.accept()
            return
        elif key == Qt.Key.Key_Home and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.scroll_by(len(self.buffer.scrollback))
            event.accept()
            return
        elif key == Qt.Key.Key_End and (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.scroll_to_bottom()
            event.accept()
            return

        # Clipboard Copy (Ctrl+Shift+C or Ctrl+C when text is selected)
        if (modifiers & Qt.KeyboardModifier.ControlModifier):
            if (modifiers & Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_C:
                self._copy_selection_to_clipboard()
                event.accept()
                return
            elif (modifiers & Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_V:
                clip_text = QApplication.clipboard().text()
                if clip_text:
                    self.scroll_to_bottom()
                    self.data_to_send.emit(clip_text.encode("utf-8"))
                event.accept()
                return
            elif (modifiers & Qt.KeyboardModifier.ShiftModifier) and key == Qt.Key.Key_A:
                self.selection_start = (0, 0)
                self.selection_end = (self.cols - 1, self.rows - 1)
                self._copy_selection_to_clipboard()
                self.update()
                event.accept()
                return
            elif key == Qt.Key.Key_C and self.has_selection():
                self._copy_selection_to_clipboard()
                event.accept()
                return

        # If user is typing any command while scrolled up, snap view to live bottom
        if self.scroll_offset > 0 and key not in (
            Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta
        ):
            self.scroll_to_bottom()

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
            # Right-click context menu (Copy, Paste, Select All)
            pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            self._show_context_menu(pos)
        elif event.button() == Qt.MouseButton.LeftButton:
            col = event.pos().x() // self.char_width
            row = event.pos().y() // self.char_height
            self.selection_start = (col, row)
            self.selection_end = (col, row)
            self.is_selecting = True
            self.update()

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
            # Copy to clipboard automatically on mouse selection
            if self.has_selection():
                self._copy_selection_to_clipboard()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double click selects the word or token under cursor and copies to clipboard."""
        if not QT_API or event.button() != Qt.MouseButton.LeftButton:
            return
        col = event.pos().x() // self.char_width
        row = event.pos().y() // self.char_height
        if 0 <= row < self.rows:
            line = self.get_visible_row(row)
            if 0 <= col < len(line):
                # Expand to word boundaries
                sc = col
                while sc > 0 and sc - 1 < len(line) and line[sc - 1].char not in (" ", "\t", ""):
                    sc -= 1
                ec = col
                while ec < len(line) and line[ec].char not in (" ", "\t", ""):
                    ec += 1
                if sc < ec:
                    self.selection_start = (sc, row)
                    self.selection_end = (ec - 1, row)
                    self._copy_selection_to_clipboard()
                    self.update()

    def _copy_selection_to_clipboard(self) -> str:
        """Copies highlighted text to system clipboard."""
        if not QT_API or not self.selection_start or not self.selection_end:
            return ""
        (c1, r1), (c2, r2) = self.selection_start, self.selection_end
        if (r1, c1) > (r2, c2):
            (c1, r1), (c2, r2) = (c2, r2), (r1, c1)

        r1 = max(0, min(r1, self.rows - 1))
        r2 = max(0, min(r2, self.rows - 1))

        lines = []
        for r in range(r1, r2 + 1):
            row = self.get_visible_row(r)
            start_col = c1 if r == r1 else 0
            end_col = (c2 + 1) if r == r2 else self.cols
            start_col = max(0, min(start_col, len(row)))
            end_col = max(0, min(end_col, len(row)))
            line_chars = "".join(row[c].char for c in range(start_col, end_col))
            lines.append(line_chars.rstrip())

        selected_text = "\n".join(lines)
        if selected_text:
            QApplication.clipboard().setText(selected_text)
        return selected_text

    def _show_context_menu(self, global_pos: QPoint) -> None:
        """Right-click context menu providing Copy, Paste, Select All, and Broadcast."""
        if not QT_API:
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #21252b;
                color: #abb2bf;
                border: 1px solid #3c3f41;
                padding: 4px;
            }
            QMenu::item {
                padding: 5px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #3e4451;
                color: #61afef;
            }
            QMenu::separator {
                height: 1px;
                background: #3c3f41;
                margin: 4px 8px;
            }
        """)

        act_copy = menu.addAction("📋 Copy")
        act_copy.setShortcut(QKeySequence("Ctrl+Shift+C"))
        act_copy.setEnabled(self.has_selection())

        clipboard_text = QApplication.clipboard().text()
        act_paste = menu.addAction("📥 Paste")
        act_paste.setShortcut(QKeySequence("Ctrl+Shift+V"))
        act_paste.setEnabled(bool(clipboard_text))

        menu.addSeparator()
        act_select_all = menu.addAction("Select All")
        act_select_all.setShortcut(QKeySequence("Ctrl+Shift+A"))

        act_clear_scrollback = menu.addAction("Clear Scrollback")

        menu.addSeparator()
        act_broadcast = menu.addAction("📢 Send Command to All Sessions...")

        action = menu.exec(global_pos)
        if action == act_copy:
            self._copy_selection_to_clipboard()
        elif action == act_paste:
            if clipboard_text:
                self.scroll_to_bottom()
                self.data_to_send.emit(clipboard_text.encode("utf-8"))
        elif action == act_select_all:
            self.selection_start = (0, 0)
            self.selection_end = (self.cols - 1, self.rows - 1)
            self._copy_selection_to_clipboard()
            self.update()
        elif action == act_clear_scrollback:
            self.parser.buffer.scrollback.clear()
            self.scroll_to_bottom()
        elif action == act_broadcast:
            mw = self.window()
            if hasattr(mw, "show_command_window"):
                mw.show_command_window(send_to_all=True)
