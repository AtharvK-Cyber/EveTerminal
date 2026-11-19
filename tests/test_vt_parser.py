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

    def test_scrollback_and_scrolling(self):
        # Feed 30 lines with newlines into a 24-row buffer
        for i in range(30):
            self.parser.feed(f"Line {i}\r\n")

        # Lines 0..23 fill initial 24 rows; line 23's newline triggers 1st scroll,
        # followed by lines 24..29 triggering 6 more scrolls = 7 lines in scrollback.
        self.assertEqual(len(self.buf.scrollback), 7)
        first_scrollback_line = "".join(c.char for c in self.buf.scrollback[0]).rstrip()
        self.assertEqual(first_scrollback_line, "Line 0")

        last_scrollback_line = "".join(c.char for c in self.buf.scrollback[-1]).rstrip()
        self.assertEqual(last_scrollback_line, "Line 6")

        # The active grid first row should now be Line 7
        active_first_line = "".join(c.char for c in self.buf.grid[0]).rstrip()
        self.assertEqual(active_first_line, "Line 7")

    def test_touchpad_and_wheel_accumulator(self):
        # Simulating smooth 2-finger touchpad scrolling accumulator
        char_height = 18
        accumulator = 0.0
        lines_scrolled = 0

        # User swipes up gently in 3 small events of 12 pixels each (total 36 pixels = 2 lines)
        for _ in range(3):
            accumulator += 12.0 / char_height
            lines = int(accumulator)
            if lines != 0:
                accumulator -= lines
                lines_scrolled += lines

        self.assertEqual(lines_scrolled, 2)
        self.assertAlmostEqual(accumulator, 0.0)

    def test_network_word_delimiters(self):
        # Test that IP address and interface names don't get split by delimiters
        delims = set(" \t\r\n`'\"()[]{}<>,;|")
        line = "show ip route 192.168.1.1 GigabitEthernet0/1"
        words = []
        cur = []
        for ch in line:
            if ch in delims:
                if cur:
                    words.append("".join(cur))
                    cur = []
            else:
                cur.append(ch)
        if cur:
            words.append("".join(cur))

        self.assertIn("192.168.1.1", words)
        self.assertIn("GigabitEthernet0/1", words)


if __name__ == "__main__":
    unittest.main()
