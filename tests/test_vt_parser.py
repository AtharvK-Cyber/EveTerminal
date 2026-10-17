"""
Unit tests for ANSI / VT100 / VT220 screen buffer and escape sequence parser.
"""

import unittest
try:
    from eveterminal.terminal.vt_parser import ScreenBuffer, VTParser
except ImportError:
    from securecrt_linux.terminal.vt_parser import ScreenBuffer, VTParser


class TestVTParser(unittest.TestCase):

    def setUp(self):
        self.buf = ScreenBuffer(cols=80, rows=24)
        self.parser = VTParser(self.buf)

    def test_plain_text(self):
        self.parser.feed("Hello World!\r\nLine 2")
        self.assertEqual(self.buf.cursor_y, 1)
        self.assertEqual(self.buf.cursor_x, 6)
        row0 = "".join(c.char for c in self.buf.grid[0]).rstrip()
        row1 = "".join(c.char for c in self.buf.grid[1]).rstrip()
        self.assertEqual(row0, "Hello World!")
        self.assertEqual(row1, "Line 2")

    def test_cursor_movement_cup(self):
        # Move cursor to row 5, col 10 (1-indexed: \x1b[5;10H)
        self.parser.feed("\x1b[5;10HTest")
        self.assertEqual(self.buf.cursor_y, 4)
        self.assertEqual(self.buf.cursor_x, 13)
        row4 = "".join(c.char for c in self.buf.grid[4]).rstrip()
        self.assertTrue(row4.endswith("Test"))

    def test_sgr_formatting(self):
        # Bold and red text: \x1b[1;31mAlert\x1b[0m
        self.parser.feed("\x1b[1;31mAlert\x1b[0m")
        cell = self.buf.grid[0][0]
        self.assertEqual(cell.char, "A")
        self.assertTrue(cell.bold)
        self.assertIsNotNone(cell.fg)

        # After reset, cell should not be bold
        self.parser.feed("Normal")
        cell_norm = self.buf.grid[0][5]
        self.assertEqual(cell_norm.char, "N")
        self.assertFalse(cell_norm.bold)

    def test_clear_screen(self):
        self.parser.feed("Some text here\x1b[2J")
        # Screen should be cleared
        for r in range(self.buf.rows):
            for c in range(self.buf.cols):
                self.assertEqual(self.buf.grid[r][c].char, " ")


if __name__ == "__main__":
    unittest.main()
