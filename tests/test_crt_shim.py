"""
Unit tests for SecureCRT Python scripting compatibility shim.
"""

import unittest
try:
    from eveterminal.scripting.crt_shim import CrtFacade, ScreenShim, SessionShim
except ImportError:
    from securecrt_linux.scripting.crt_shim import CrtFacade, ScreenShim, SessionShim


class TestCrtShim(unittest.TestCase):

    def test_screen_send_and_wait(self):
        sent_data = []
        screen = ScreenShim(send_fn=lambda d: sent_data.append(d), get_buffer_fn=lambda: "")
        session = SessionShim("TestSession")
        crt = CrtFacade(screen, session)

        # Send command
        crt.Screen.Send("show version\r\n")
        self.assertEqual(sent_data, [b"show version\r\n"])

        # Simulate incoming remote data
        screen.feed_rx("Cisco IOS Software, 7200 Software\r\nRouter>")

        # WaitForString
        matched = crt.Screen.WaitForString("Router>", timeout=1)
        self.assertTrue(matched)

    def test_read_string(self):
        screen = ScreenShim(send_fn=lambda d: None, get_buffer_fn=lambda: "")
        session = SessionShim("TestSession")
        crt = CrtFacade(screen, session)

        screen.feed_rx("interface GigabitEthernet0/0\r\n ip address 10.0.0.1\r\n!END")
        captured = crt.Screen.ReadString("!END", timeout=1)
        self.assertIn("GigabitEthernet0/0", captured)
        self.assertIn("10.0.0.1", captured)
        self.assertNotIn("!END", captured)


if __name__ == "__main__":
    unittest.main()
