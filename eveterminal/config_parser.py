"""
VanDyke SecureCRT Configuration Parser & Importer.
Parses the typed .ini format:
  S:"Key"=StringValue
  D:"Key"=00000001 (Hex32 DWORD)
  B:"Key"=Length \n Hex bytes
  Z:"Key"=Count \n Items
"""

import os
import re
from typing import Dict, Any, Optional, List


class VanDykeIniParser:
    """Parses and serializes VanDyke .ini configuration files."""

    S_PATTERN = re.compile(r'^S:"([^"]+)"=(.*)$')
    D_PATTERN = re.compile(r'^D:"([^"]+)"=([0-9a-fA-F]{8})$')
    B_PATTERN = re.compile(r'^B:"([^"]+)"=([0-9a-fA-F]{8})$')
    Z_PATTERN = re.compile(r'^Z:"([^"]+)"=([0-9a-fA-F]{8})$')

    @classmethod
    def parse_file(cls, filepath: str) -> Dict[str, Any]:
        """Parses a VanDyke typed .ini file into a Python dictionary."""
        if not os.path.exists(filepath):
            return {}

        result: Dict[str, Any] = {}
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i].strip()
            if not line or line.startswith("//") or line.startswith("#"):
                i += 1
                continue

            # Check S: (String)
            m_s = cls.S_PATTERN.match(line)
            if m_s:
                result[m_s.group(1)] = m_s.group(2)
                i += 1
                continue

            # Check D: (DWORD / Integer)
            m_d = cls.D_PATTERN.match(line)
            if m_d:
                result[m_d.group(1)] = int(m_d.group(2), 16)
                i += 1
                continue

            # Check B: (Binary Blob)
            m_b = cls.B_PATTERN.match(line)
            if m_b:
                key = m_b.group(1)
                byte_len = int(m_b.group(2), 16)
                hex_data = []
                i += 1
                while i < n and lines[i].startswith(" "):
                    hex_data.append(lines[i].strip())
                    i += 1
                raw_hex = "".join(hex_data).replace(" ", "")
                result[key] = {
                    "__type__": "binary",
                    "length": byte_len,
                    "hex": raw_hex,
                }
                continue

            # Check Z: (Array / List)
            m_z = cls.Z_PATTERN.match(line)
            if m_z:
                key = m_z.group(1)
                count = int(m_z.group(2), 16)
                items = []
                i += 1
                for _ in range(count):
                    if i < n:
                        items.append(lines[i].rstrip("\r\n"))
                        i += 1
                result[key] = {
                    "__type__": "list",
                    "count": count,
                    "items": items,
                }
                continue

            # Fallback for unrecognized format
            if "=" in line:
                k, v = line.split("=", 1)
                result[k.strip()] = v.strip()
            i += 1

        return result

    @classmethod
    def save_file(cls, filepath: str, data: Dict[str, Any]) -> None:
        """Serializes dictionary back to VanDyke typed .ini format."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for k, v in data.items():
                if isinstance(v, str):
                    f.write(f'S:"{k}"={v}\n')
                elif isinstance(v, int):
                    f.write(f'D:"{k}"={v:08x}\n')
                elif isinstance(v, dict) and v.get("__type__") == "binary":
                    byte_len = v.get("length", 0)
                    hex_str = v.get("hex", "")
                    f.write(f'B:"{k}"={byte_len:08x}\n')
                    # Format hex bytes in groups of 32
                    chunks = [hex_str[j:j+2] for j in range(0, len(hex_str), 2)]
                    for line_start in range(0, len(chunks), 16):
                        line_chunk = " ".join(chunks[line_start:line_start+16])
                        f.write(f" {line_chunk}\n")
                elif isinstance(v, dict) and v.get("__type__") == "list":
                    items = v.get("items", [])
                    f.write(f'Z:"{k}"={len(items):08x}\n')
                    for item in items:
                        f.write(f"{item}\n")
                else:
                    f.write(f'S:"{k}"={str(v)}\n')


class SecureCRTConfigManager:
    """
    Manages loading, merging and querying SecureCRT configurations.
    Preserves user layout preferences (single instance, tabs vs rows/columns tiling).
    """

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or self.detect_config_dir()
        self.global_settings: Dict[str, Any] = {}
        self.default_session: Dict[str, Any] = {}
        self.color_schemes: Dict[str, Any] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.load_all()

    @staticmethod
    def detect_config_dir() -> str:
        """Locates VanDyke config directory on Windows or Linux."""
        # 1. Windows AppData
        appdata = os.environ.get("APPDATA")
        if appdata:
            win_path = os.path.join(appdata, "VanDyke", "Config")
            if os.path.exists(win_path):
                return win_path

        # 2. Linux XDG / home directories
        home = os.path.expanduser("~")
        linux_candidates = [
            os.path.join(home, ".config", "VanDyke", "SecureCRT", "Config"),
            os.path.join(home, ".config", "securecrt-linux"),
            os.path.join(home, ".vandyke"),
        ]
        for p in linux_candidates:
            if os.path.exists(p):
                return p

        # Default fallback
        fallback = os.path.join(home, ".config", "securecrt-linux")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def load_all(self) -> None:
        """Loads Global.ini, Sessions/Default.ini, Color Schemes.ini and all session profiles."""
        if not os.path.exists(self.config_dir):
            return

        global_path = os.path.join(self.config_dir, "Global.ini")
        if os.path.exists(global_path):
            self.global_settings = VanDykeIniParser.parse_file(global_path)

        cs_path = os.path.join(self.config_dir, "Color Schemes.ini")
        if os.path.exists(cs_path):
            self.color_schemes = VanDykeIniParser.parse_file(cs_path)

        sessions_dir = os.path.join(self.config_dir, "Sessions")
        if os.path.exists(sessions_dir):
            default_path = os.path.join(sessions_dir, "Default.ini")
            if os.path.exists(default_path):
                self.default_session = VanDykeIniParser.parse_file(default_path)

            # Discover all sessions recursively
            for root, _, files in os.walk(sessions_dir):
                for f in files:
                    if f.endswith(".ini") and f != "Default.ini":
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, sessions_dir)
                        # Name without .ini
                        session_name = os.path.splitext(rel_path)[0].replace("\\", "/")
                        self.sessions[session_name] = VanDykeIniParser.parse_file(full_path)

    def is_single_instance_enabled(self) -> bool:
        """Checks if 'Single Instance' mode is enabled in Global.ini."""
        return bool(self.global_settings.get("Single Instance", 1))

    def should_open_in_tab(self) -> bool:
        """Checks if sessions should open as tabs in the same window."""
        return bool(self.global_settings.get("Open Sessions In Tab", 1)) or bool(self.global_settings.get("Show Session Tabs", 1))

    def get_session_config(self, session_name: str) -> Dict[str, Any]:
        """Returns session config merged with Default.ini fallback defaults."""
        merged = dict(self.default_session)
        if session_name in self.sessions:
            merged.update(self.sessions[session_name])
        return merged
