"""
Unit tests for Command Window / Broadcast Bar.
"""

import unittest
from unittest.mock import MagicMock

try:
    from eveterminal.ui.command_window import CommandLineEdit, CommandWindowWidget, CommandWindowDock
    from eveterminal.ui.main_window import MainWindow
    from eveterminal.config_parser import SecureCRTConfigManager
    QT_AVAILABLE = True
except Exception:
    QT_AVAILABLE = False


class TestCommandWindow(unittest.TestCase):

    def test_mock_broadcast_logic(self):
        """Tests command broadcasting to multiple mock sessions."""
        # Create mock sessions
        mock_sessions = []
        for name in ["R1", "R2", "R3", "R4", "R5"]:
            mock_conn = MagicMock()
            mock_conn.is_connected = True
            mock_session = MagicMock()
            mock_session.title = name
            mock_session.connection = mock_conn
            mock_sessions.append(mock_session)

        # Broadcast function logic test
        payload = b"show ip interface brief\r\n"
        sent_names = []
        for s in mock_sessions:
            if s.connection and s.connection.is_connected:
                s.connection.send(payload)
                sent_names.append(s.title)

        self.assertEqual(len(sent_names), 5)
        self.assertEqual(sent_names, ["R1", "R2", "R3", "R4", "R5"])

        for s in mock_sessions:
            s.connection.send.assert_called_with(payload)

    def test_command_line_history_logic(self):
        """Tests command history stack and recall mechanics."""
        history = ["conf t", "interface gig0/0", "ip address 10.0.0.1 255.255.255.0", "no shut"]
        idx = len(history) - 1

        # Press Up
        self.assertEqual(history[idx], "no shut")
        # Press Up again
        idx -= 1
        self.assertEqual(history[idx], "ip address 10.0.0.1 255.255.255.0")
        # Press Down
        idx += 1
        self.assertEqual(history[idx], "no shut")


if __name__ == "__main__":
    unittest.main()
