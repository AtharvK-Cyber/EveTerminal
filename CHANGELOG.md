# Changelog

All notable changes to **EveTerminal** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-17

### Added
- **Single-Instance IPC Engine**: Intercepts external CLI launches and browser links to keep all terminal sessions inside a single main window.
- **Multi-Tab & Horizontal Rows (`R1, R2, R3`) Layout**: Seamlessly switch between tabbed mode and vertically stacked rows with dedicated title bars.
- **RFC 854/855 Telnet Protocol Engine**:
  - Full SGA, ECHO, NAWS (window size), and TTYPE negotiation.
  - Background `IAC NOP` keepalive thread (every 15s) and TCP socket keepalives (`SO_KEEPALIVE`) solving EVE-NG 30-second dropouts.
  - Non-blocking socket reader loop preventing thread hangs during handshake.
- **Cisco IOS Native Autocompletion**: Overrode Qt widget focus traversal (`focusNextPrevChild`), routing `Tab` directly to router CLI for command expansion (`show ip interface bri` -> `brief`).
- **Cisco Break Sequence Support**: Implemented `Ctrl+Shift+6` / `Ctrl+^` (`\x1e`) break sequence.
- **Live Device Hostname & Prompt Detection**: Real-time regex parser syncs tab and row headers dynamically to device prompts (`R1#`, `R2>`, `Core-SW1#`).
- **SecureCRT Configuration Compatibility**:
  - Parser and serializer for VanDyke line-oriented `.ini` formats (`S:`, `D:`, `B:`, `Z:`).
  - Authentic color schemes (*Traditional Green*, *Monochrome Amber*, *Yellow on Black*, etc.).
- **Desktop & Browser Integration**:
  - `xdg-mime` associations for `telnet://` and `ssh://` schemes.
  - High-resolution SVG application icon and `.desktop` launcher.
  - Double-clickable standalone `.deb` package builder (`package_deb.sh`).
  - Automated one-click installer (`install.sh`) and uninstaller (`uninstall.sh`).
