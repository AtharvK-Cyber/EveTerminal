"""
Unit tests for VanDyke .ini parser and config manager.
"""

import os
import unittest
try:
    from eveterminal.config_parser import VanDykeIniParser, SecureCRTConfigManager
except ImportError:
    from securecrt_linux.config_parser import VanDykeIniParser, SecureCRTConfigManager


class TestConfigParser(unittest.TestCase):

    def test_parse_real_default_ini(self):
        default_ini_path = r"C:\Users\admin\AppData\Roaming\VanDyke\Config\Sessions\Default.ini"
        if not os.path.exists(default_ini_path):
            self.skipTest("Default.ini not found at path")

        parsed = VanDykeIniParser.parse_file(default_ini_path)
        self.assertIn("Protocol Name", parsed)
        self.assertEqual(parsed["Protocol Name"], "SSH2")
        self.assertIn("[SSH2] Port", parsed)
        self.assertEqual(parsed["[SSH2] Port"], 22)
        self.assertEqual(parsed.get("Emulation"), "VT100")
        self.assertEqual(parsed.get("Rows"), 24)
        self.assertEqual(parsed.get("Cols"), 80)
        self.assertEqual(parsed.get("Color Scheme"), "Monochrome")

    def test_parse_real_global_ini(self):
        global_ini_path = r"C:\Users\admin\AppData\Roaming\VanDyke\Config\Global.ini"
        if not os.path.exists(global_ini_path):
            self.skipTest("Global.ini not found at path")

        parsed = VanDykeIniParser.parse_file(global_ini_path)
        self.assertEqual(parsed.get("Single Instance"), 1)
        self.assertEqual(parsed.get("Show Session Tabs"), 1)
        self.assertEqual(parsed.get("Copy On Select"), 1)

    def test_typed_round_trip(self):
        synthetic = {
            "Host": "router1.lab",
            "Port": 5001,
            "RawBlob": {"__type__": "binary", "length": 4, "hex": "deadbeef"},
            "ListItems": {"__type__": "list", "count": 2, "items": ["Item1", "Item2"]},
        }
        test_file = "test_roundtrip.ini"
        try:
            VanDykeIniParser.save_file(test_file, synthetic)
            reloaded = VanDykeIniParser.parse_file(test_file)
            self.assertEqual(reloaded["Host"], "router1.lab")
            self.assertEqual(reloaded["Port"], 5001)
            self.assertEqual(reloaded["RawBlob"]["hex"], "deadbeef")
            self.assertEqual(reloaded["ListItems"]["items"], ["Item1", "Item2"])
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


if __name__ == "__main__":
    unittest.main()
