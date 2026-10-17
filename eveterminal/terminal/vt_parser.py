"""
ANSI / VT100 / VT220 / Xterm Terminal Escape Sequence Parser and Screen Buffer.
Maintains a 2D grid of characters with styling, scrollback buffer, cursor coordinates,
and alternate screen buffer.
"""

import re
from typing import List, Dict, Tuple, Optional, Callable


class Cell:
    __slots__ = ("char", "fg", "bg", "bold", "italic", "underline", "reverse")

    def __init__(
        self,
        char: str = " ",
        fg: Optional[str] = None,
        bg: Optional[str] = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        reverse: bool = False,
    ):
        self.char = char
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.reverse = reverse

    def copy(self) -> "Cell":
        return Cell(
            self.char,
            self.fg,
            self.bg,
            self.bold,
            self.italic,
            self.underline,
            self.reverse,
        )


class ScreenBuffer:
    """Represents a terminal screen grid with scrollback history."""

    def __init__(self, cols: int = 80, rows: int = 24, max_scrollback: int = 10000):
        self.cols = cols
        self.rows = rows
        self.max_scrollback = max_scrollback

        self.cursor_x = 0
        self.cursor_y = 0
        self.saved_cursor = (0, 0)

        # Style state
        self.current_fg: Optional[str] = None
        self.current_bg: Optional[str] = None
        self.bold: bool = False
        self.italic: bool = False
        self.underline: bool = False
        self.reverse: bool = False

        # Active grid: list of rows, each row is a list of Cell
        self.grid: List[List[Cell]] = [
            [Cell() for _ in range(self.cols)] for _ in range(self.rows)
        ]
        self.scrollback: List[List[Cell]] = []

        # Margins for scrolling (top, bottom 0-indexed)
        self.top_margin = 0
        self.bottom_margin = self.rows - 1

    def resize(self, new_cols: int, new_rows: int) -> None:
        """Resizes the terminal grid."""
        new_grid = []
        for r in range(new_rows):
            if r < len(self.grid):
                old_row = self.grid[r]
                if len(old_row) < new_cols:
                    new_row = [c.copy() for c in old_row] + [
                        Cell() for _ in range(new_cols - len(old_row))
                    ]
                else:
                    new_row = [c.copy() for c in old_row[:new_cols]]
            else:
                new_row = [Cell() for _ in range(new_cols)]
            new_grid.append(new_row)

        self.grid = new_grid
        self.cols = new_cols
        self.rows = new_rows
        self.top_margin = 0
        self.bottom_margin = new_rows - 1
        self.cursor_x = min(self.cursor_x, new_cols - 1)
        self.cursor_y = min(self.cursor_y, new_rows - 1)

    def write_char(self, char: str) -> None:
        """Writes a printable character at the cursor position."""
        if self.cursor_x >= self.cols:
            self.cursor_x = 0
            self.cursor_y += 1
            if self.cursor_y > self.bottom_margin:
                self.scroll_up()
                self.cursor_y = self.bottom_margin

        if 0 <= self.cursor_y < self.rows and 0 <= self.cursor_x < self.cols:
            cell = self.grid[self.cursor_y][self.cursor_x]
            cell.char = char
            cell.fg = self.current_fg
            cell.bg = self.current_bg
            cell.bold = self.bold
            cell.italic = self.italic
            cell.underline = self.underline
            cell.reverse = self.reverse

        self.cursor_x += 1

    def scroll_up(self, count: int = 1) -> None:
        """Scrolls lines upward within the active scroll margins."""
        for _ in range(count):
            if self.top_margin == 0:
                # Top row moves to scrollback
                top_row = self.grid.pop(0)
                self.scrollback.append(top_row)
                if len(self.scrollback) > self.max_scrollback:
                    self.scrollback.pop(0)
            else:
                self.grid.pop(self.top_margin)

            # Insert empty row at bottom margin
            new_row = [Cell() for _ in range(self.cols)]
            self.grid.insert(self.bottom_margin, new_row)

    def scroll_down(self, count: int = 1) -> None:
        """Scrolls lines downward within the active scroll margins."""
        for _ in range(count):
            self.grid.pop(self.bottom_margin)
            new_row = [Cell() for _ in range(self.cols)]
            self.grid.insert(self.top_margin, new_row)

    def clear_screen(self, mode: int = 2) -> None:
        """ED (Erase in Display). Mode 0: cursor to end, 1: start to cursor, 2: entire."""
        if mode == 2 or mode == 3:
            for r in range(self.rows):
                self.grid[r] = [Cell() for _ in range(self.cols)]
            self.cursor_x = 0
            self.cursor_y = 0
        elif mode == 0:
            # Clear from cursor to end of screen
            for x in range(self.cursor_x, self.cols):
                self.grid[self.cursor_y][x] = Cell()
            for y in range(self.cursor_y + 1, self.rows):
                self.grid[y] = [Cell() for _ in range(self.cols)]
        elif mode == 1:
            # Clear from top of screen to cursor
            for y in range(self.cursor_y):
                self.grid[y] = [Cell() for _ in range(self.cols)]
            for x in range(0, self.cursor_x + 1):
                self.grid[self.cursor_y][x] = Cell()

    def clear_line(self, mode: int = 0) -> None:
        """EL (Erase in Line). Mode 0: cursor to end, 1: start to cursor, 2: entire."""
        if 0 <= self.cursor_y < self.rows:
            if mode == 0:
                for x in range(self.cursor_x, self.cols):
                    self.grid[self.cursor_y][x] = Cell()
            elif mode == 1:
                for x in range(0, min(self.cursor_x + 1, self.cols)):
                    self.grid[self.cursor_y][x] = Cell()
            elif mode == 2:
                self.grid[self.cursor_y] = [Cell() for _ in range(self.cols)]


class VTParser:
    """Parses incoming byte streams into terminal commands and buffer updates."""

    CSI_PATTERN = re.compile(r"^\x1b\[([?0-9;]*)([a-zA-Z])")
    OSC_PATTERN = re.compile(r"^\x1b\]([^\x07\x1b]*)(?:\x07|\x1b\\)")

    def __init__(self, buffer: ScreenBuffer, on_title_change: Optional[Callable[[str], None]] = None):
        self.buffer = buffer
        self.on_title_change = on_title_change
        self.main_buffer = buffer
        self.alt_buffer = ScreenBuffer(buffer.cols, buffer.rows, max_scrollback=0)
        self.in_alt_buffer = False
        self.cursor_visible = True

    def feed(self, text: str) -> None:
        """Feeds string data into the VT state machine."""
        i = 0
        n = len(text)
        buf = self.buffer

        while i < n:
            ch = text[i]

            if ch == "\r":
                buf.cursor_x = 0
                i += 1
            elif ch == "\n":
                buf.cursor_y += 1
                if buf.cursor_y > buf.bottom_margin:
                    buf.scroll_up()
                    buf.cursor_y = buf.bottom_margin
                i += 1
            elif ch == "\b":
                buf.cursor_x = max(0, buf.cursor_x - 1)
                i += 1
            elif ch == "\t":
                buf.cursor_x = min(buf.cols - 1, (buf.cursor_x // 8 + 1) * 8)
                i += 1
            elif ch == "\a":  # Bell
                i += 1
            elif ch == "\x1b":  # ESC sequence
                rem = text[i:]
                # Check CSI (ESC [)
                m_csi = self.CSI_PATTERN.match(rem)
                if m_csi:
                    params_str, cmd = m_csi.group(1), m_csi.group(2)
                    self._handle_csi(params_str, cmd)
                    i += len(m_csi.group(0))
                    continue

                # Check OSC (ESC ])
                m_osc = self.OSC_PATTERN.match(rem)
                if m_osc:
                    content = m_osc.group(1)
                    if ";" in content:
                        code, val = content.split(";", 1)
                        if code in ("0", "2") and self.on_title_change:
                            self.on_title_change(val)
                    i += len(m_osc.group(0))
                    continue

                # Unrecognized or short ESC sequence
                if len(rem) > 1 and rem[1] in ("7", "8", "c", "M", "E"):
                    esc_cmd = rem[1]
                    if esc_cmd == "7":  # Save cursor
                        buf.saved_cursor = (buf.cursor_x, buf.cursor_y)
                    elif esc_cmd == "8":  # Restore cursor
                        buf.cursor_x, buf.cursor_y = buf.saved_cursor
                    elif esc_cmd == "c":  # Reset
                        buf.clear_screen(2)
                    elif esc_cmd == "M":  # Reverse Index (scroll down)
                        if buf.cursor_y == buf.top_margin:
                            buf.scroll_down()
                        else:
                            buf.cursor_y = max(0, buf.cursor_y - 1)
                    i += 2
                    continue

                i += 1
            else:
                buf.write_char(ch)
                i += 1

    def _handle_csi(self, params_str: str, cmd: str) -> None:
        buf = self.buffer
        is_private = params_str.startswith("?")
        if is_private:
            params_str = params_str[1:]

        params = []
        if params_str:
            for p in params_str.split(";"):
                try:
                    params.append(int(p))
                except ValueError:
                    params.append(0)
        else:
            params = [0]

        p0 = params[0] if params else 0

        # Cursor movements
        if cmd in ("H", "f"):  # CUP: Cursor Position [row;col] (1-indexed)
            row = (params[0] - 1) if len(params) > 0 and params[0] > 0 else 0
            col = (params[1] - 1) if len(params) > 1 and params[1] > 0 else 0
            buf.cursor_y = max(0, min(row, buf.rows - 1))
            buf.cursor_x = max(0, min(col, buf.cols - 1))
        elif cmd == "A":  # CUU: Cursor Up
            buf.cursor_y = max(0, buf.cursor_y - max(1, p0))
        elif cmd == "B":  # CUD: Cursor Down
            buf.cursor_y = min(buf.rows - 1, buf.cursor_y + max(1, p0))
        elif cmd == "C":  # CUF: Cursor Forward
            buf.cursor_x = min(buf.cols - 1, buf.cursor_x + max(1, p0))
        elif cmd == "D":  # CUB: Cursor Back
            buf.cursor_x = max(0, buf.cursor_x - max(1, p0))
        elif cmd == "G":  # CHA: Cursor Horizontal Absolute
            buf.cursor_x = max(0, min(max(1, p0) - 1, buf.cols - 1))
        elif cmd == "d":  # VPA: Line Position Absolute
            buf.cursor_y = max(0, min(max(1, p0) - 1, buf.rows - 1))
        elif cmd == "J":  # ED: Erase in Display
            buf.clear_screen(p0)
        elif cmd == "K":  # EL: Erase in Line
            buf.clear_line(p0)
        elif cmd == "m":  # SGR: Select Graphic Rendition
            self._handle_sgr(params)
        elif cmd == "r":  # DECSTBM: Set Top and Bottom Margins
            top = (params[0] - 1) if len(params) > 0 and params[0] > 0 else 0
            bottom = (params[1] - 1) if len(params) > 1 and params[1] > 0 else (buf.rows - 1)
            buf.top_margin = max(0, min(top, buf.rows - 1))
            buf.bottom_margin = max(buf.top_margin, min(bottom, buf.rows - 1))
        elif cmd in ("h", "l") and is_private:
            enable = (cmd == "h")
            if p0 == 25:  # Cursor visibility
                self.cursor_visible = enable
            elif p0 in (47, 1047, 1049):  # Alternate screen buffer
                if enable and not self.in_alt_buffer:
                    self.in_alt_buffer = True
                    self.buffer = self.alt_buffer
                    self.buffer.clear_screen(2)
                elif not enable and self.in_alt_buffer:
                    self.in_alt_buffer = False
                    self.buffer = self.main_buffer

    def _handle_sgr(self, params: List[int]) -> None:
        buf = self.buffer
        if not params or params == [0]:
            buf.current_fg = None
            buf.current_bg = None
            buf.bold = False
            buf.italic = False
            buf.underline = False
            buf.reverse = False
            return

        i = 0
        n = len(params)
        from .color_schemes import ANSI_16_COLORS

        while i < n:
            code = params[i]
            if code == 0:
                buf.current_fg = None
                buf.current_bg = None
                buf.bold = False
                buf.italic = False
                buf.underline = False
                buf.reverse = False
            elif code == 1:
                buf.bold = True
            elif code == 2:
                buf.bold = False
            elif code == 3:
                buf.italic = True
            elif code == 4:
                buf.underline = True
            elif code == 7:
                buf.reverse = True
            elif code == 22:
                buf.bold = False
            elif code == 23:
                buf.italic = False
            elif code == 24:
                buf.underline = False
            elif code == 27:
                buf.reverse = False
            elif 30 <= code <= 37:
                idx = code - 30 + (8 if buf.bold else 0)
                buf.current_fg = ANSI_16_COLORS[idx]
            elif code == 39:
                buf.current_fg = None
            elif 40 <= code <= 47:
                idx = code - 40
                buf.current_bg = ANSI_16_COLORS[idx]
            elif code == 49:
                buf.current_bg = None
            elif 90 <= code <= 97:
                idx = code - 90 + 8
                buf.current_fg = ANSI_16_COLORS[idx]
            elif 100 <= code <= 107:
                idx = code - 100 + 8
                buf.current_bg = ANSI_16_COLORS[idx]
            elif code == 38:  # Extended foreground
                if i + 2 < n and params[i + 1] == 5:  # 256 color
                    c_idx = params[i + 2]
                    if c_idx < 16:
                        buf.current_fg = ANSI_16_COLORS[c_idx]
                    i += 2
                elif i + 4 < n and params[i + 1] == 2:  # 24-bit RGB
                    r, g, b = params[i + 2], params[i + 3], params[i + 4]
                    buf.current_fg = f"#{r:02x}{g:02x}{b:02x}"
                    i += 4
            elif code == 48:  # Extended background
                if i + 2 < n and params[i + 1] == 5:
                    c_idx = params[i + 2]
                    if c_idx < 16:
                        buf.current_bg = ANSI_16_COLORS[c_idx]
                    i += 2
                elif i + 4 < n and params[i + 1] == 2:
                    r, g, b = params[i + 2], params[i + 3], params[i + 4]
                    buf.current_bg = f"#{r:02x}{g:02x}{b:02x}"
                    i += 4
            i += 1
