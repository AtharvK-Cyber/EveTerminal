# EveTerminal 🚀
### Free & Open-Source SecureCRT Alternative for Linux
*Multi-tab terminal client built for EVE-NG, GNS3, PNETLab, Cisco, Juniper, and Linux infrastructure labs*

<p align="center">
  <a href="https://github.com/AtharvK-Cyber/EveTerminal/actions/workflows/ci.yml"><img src="https://github.com/AtharvK-Cyber/EveTerminal/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://debian.org"><img src="https://img.shields.io/badge/Platform-Debian%20%7C%20Ubuntu%20%7C%20Mint%20%7C%20Kali-red.svg?style=for-the-badge" alt="Platform: Debian/Ubuntu"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg?style=for-the-badge" alt="Python: 3.9+"></a>
  <a href="https://riverbankcomputing.com"><img src="https://img.shields.io/badge/GUI-PyQt6%20%7C%20Wayland%20%26%20X11-purple.svg?style=for-the-badge" alt="GUI: PyQt6"></a>
  <a href="https://github.com"><img src="https://img.shields.io/badge/EVE--NG-Ready%20%E2%9C%93-orange.svg?style=for-the-badge" alt="EVE-NG Ready"></a>
</p>

<p align="center">
  <img src="Screenshot/terminal.jpeg" alt="EveTerminal Interface" width="900" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
</p>

---

## 📑 Table of Contents

- [Why EveTerminal?](#-why-eveterminal)
- [Feature Comparison Matrix](#-feature-comparison-matrix)
- [Key Capabilities](#-key-capabilities)
- [System Architecture](#-system-architecture)
- [Supported Platforms](#-supported-platforms)
- [Quick 1-Command Installation](#-quick-1-command-installation)
- [Updating & Automatic Rollback Guide](#-updating--automatic-rollback-guide)
- [Installation via Standalone .deb Package](#-installation-via-standalone-deb-package)
- [EVE-NG & Browser One-Click Integration](#-eve-ng--browser-one-click-integration)
- [CLI Flags & Usage Guide](#-cli-flags--usage-guide)
- [Keyboard Shortcuts Reference](#-keyboard-shortcuts-reference)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Contributing](#-contributing)
- [Clean-Room Notice & Legal Disclaimers](#-clean-room-notice--legal-disclaimers)
- [License](#-license)

---

## 💡 Why EveTerminal?

Network engineers running **EVE-NG, GNS3, or PNETLab** on modern Linux systems (Debian, Ubuntu, Kali, Mint) have historically had to compromise:
- **Default terminals** (GNOME Terminal, Konsole, XFCE) spawn a separate floating window for every router clicked, cluttering your desktop with 20+ disconnected windows.
- **PuTTY** lacks a native multi-session tab bar and doesn't auto-tile into horizontal rows.
- **SecureCRT®** requires commercial activation licenses, and running older Windows releases under Wine suffers from socket disconnects, font scaling glitches, and desktop integration bugs.
- **The 30-Second Disconnect Problem**: Standard Linux telnet clients drop idle router sessions after 30 seconds due to virtual NAT timeouts.

**EveTerminal solves all of this out-of-the-box in a 100% free, open-source application.**

---

## 📊 Feature Comparison Matrix

| Feature | **EveTerminal** | **PuTTY / KiTTY** | **Default Terminals** | **SecureCRT® (Commercial)** |
| :--- | :---: | :---: | :---: | :---: |
| **Single-Window IPC** (all nodes open in 1 window) | ✅ **Yes** | ❌ No | ❌ Separate Windows | ✅ Yes |
| **Horizontal Tiled Rows** (`R1, R2, R3` layout) | ✅ **Yes** | ❌ No | ⚠️ Complex setup | ✅ Yes |
| **1-Click EVE-NG Browser Interception** (`telnet://`) | ✅ **Native** | ⚠️ Needs scripts | ⚠️ Opens separate apps | ⚠️ Complex config |
| **30-Second Keepalive Drop Fix** (`IAC NOP` keepalives) | ✅ **Built-in** | ⚠️ Manual config | ❌ Drops after 30s | ⚠️ Requires tweaking |
| **Cisco Command Autocomplete** (`Tab` key) | ✅ **Native** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Cisco Break Sequence** (`Ctrl+Shift+6` / `Ctrl+^`) | ✅ **Native** | ⚠️ Mapping needed | ⚠️ Mapping needed | ✅ Yes |
| **Live Device Prompt Detection** (`R1#` $\rightarrow$ Tab sync) | ✅ **Automatic** | ❌ No | ❌ No | ❌ No |
| **Command Window (Broadcast to All Sessions)** | ✅ **Native (`Ctrl+Shift+B`)** | ❌ No | ❌ No | ✅ Native |
| **Visual Select & Copy / Right-Click Menu** | ✅ **Native (`Ctrl+Shift+C`)** | ⚠️ Basic | ⚠️ Basic | ✅ Yes |
| **Scrollback History & Mouse Wheel Scroll** | ✅ **Native (`QScrollBar` + Wheel)** | ⚠️ Basic | ✅ Yes | ✅ Yes |
| **SecureCRT `.ini` Sessions Import** | ✅ **Native** | ❌ No | ❌ No | ✅ Native |
| **Native Wayland & X11 Support** | ✅ **Qt6 Native** | ❌ X11 only | ✅ Yes | ❌ Wine/Legacy |
| **License Requirement** | 🆓 **100% Free / MIT** | 🆓 Free | 🆓 Free | 💲 Paid License |

---

## ⚡ Key Capabilities

### 1. 🪟 Single-Instance Window Management
- When you click router nodes in EVE-NG (`R1`, `R2`, `R3`), they attach seamlessly to the **same running window**.
- Built-in `QLocalServer` Unix domain socket IPC receives connection requests from browsers and CLI invocations, forwarding them to the existing window without spawning multiple instances.

### 2. 🛡️ Bulletproof Telnet Session Engine
- Implements full **RFC 854/855 Option Negotiation**:
  - `SGA` (Suppress Go Ahead) & `ECHO` for character-by-character interactive routers.
  - `NAWS` (Negotiate About Window Size - RFC 1073) dynamically synchronizing terminal dimensions.
  - `TTYPE` (Terminal Type - RFC 1091) advertising `VT100` compatibility.
- **Background Keepalive Heartbeat**: Sends Telnet `IAC NOP` (`\xff\xf1`) packets every 15 seconds during idle periods, keeping virtual NAT sessions, hypervisors, and reverse proxies alive indefinitely.
- **OS-Level Socket Tuning**: Automatically configures Linux kernel TCP keepalives (`SO_KEEPALIVE`, `TCP_KEEPIDLE=10s`, `TCP_KEEPINTVL=3s`, `TCP_KEEPCNT=5`).

### 3. ⌨️ Cisco IOS Command Autocompletion & Control Keys
- Custom Qt event handling bypasses widget focus navigation, routing the **`Tab`** key directly to the router CLI so typing `show ip interface bri` and pressing `Tab` expands to `brief`.
- Native Cisco break sequence: **`Ctrl+Shift+6`** or **`Ctrl+^`** (`\x1e`) halts runaway pings, traceroutes, or hung DNS queries instantly.
- Ergonomic Unix editing keys: `Ctrl+A` (home), `Ctrl+E` (end), `Ctrl+U` (erase line), `Ctrl+W` (erase word), `Ctrl+C` (abort).

### 4. 🏷️ Live Router Naming & Prompt Synchronization
- **Automatic Default Naming**: When you open nodes from EVE-NG, tabs are named **`R1`**, **`R2`**, **`R3`**, **`R4`** sequentially instead of displaying confusing IP/port numbers.
- **Real-Time Hostname Sync**: As soon as the router prompt arrives over the socket (`R1#`, `R2>`, `Core-SW1(config)#`), EveTerminal detects the hostname and updates the tab and row headers dynamically.
- **Right-Click Tab Rename**: Right-click any tab at any time to type a custom name or clone the session.

### 5. 🧱 Horizontal Rows Layout (`R1, R2, R3` Format)
- Switch between **Tabbed Mode** and **Tiled Horizontal Rows Mode** with one click via `View -> Window Layout -> Tile Horizontally (Rows: R1, R2, R3...)`.
- View all your lab routers simultaneously in vertically stacked rows with distinct title headers (`● R1`, `● R2`, `● R3`).

### 6. 📁 SecureCRT `.ini` Compatibility
- Reads and parses VanDyke line-oriented configuration schemas (`S:"Key"=String`, `D:"Key"=Hex32`, `B:"Key"=Binary`, `Z:"Key"=List`).
- Supports SecureCRT color schemes: *Traditional (Green on Black)*, *Monochrome (Amber on Black)*, *Yellow on Black*, *Black on White*, and custom ANSI palettes.
- Python scripting shim compatible with `crt.Screen`, `crt.Session`, `crt.Dialog`, and `crt.GetScriptTab()`.

### 7. 📢 Command Window / Broadcast to All Sessions (`R1, R2, R3...`)
- **Execute Commands Across All Devices**: Send commands (`conf t`, `no shut`, `show ip int br`, `wr mem`) to **every open router or switch session simultaneously**.
- **Split-Screen Bottom Terminal**: Toggle the dockable bottom command bar via **`View -> Command Window`**, shortcut **`Ctrl+Shift+B`** (or `Alt+F3`), or by right-clicking any tab or bottom button bar and clicking **"Send to All Devices"**.
- **Interactive Target Switching**: Choose between `📢 Send to All Sessions (Broadcast)` or `🎯 Send to Active Session Only` with instant visual indicators.
- **Command History**: Browse through previously executed commands using **`Up`** and **`Down`** arrows.
- **Session Count & Device Summary**: Real-time badge displays the exact count and names of receiving devices (`● 5 sessions: R1, R2, R3, R4, R5`).

### 8. 📜 Smooth Scrolling & Rich Mouse Selection / Copy
- **Full Scrollback Buffer (10,000 Lines)**: Output never disappears. Seamlessly scroll up through thousands of lines of output (`show tech-support`, `show run`) using your **mouse wheel** or the integrated **vertical scrollbar**.
- **Auto-Snap to Live Output**: As soon as new data arrives or you type any command, the view automatically locks to the bottom so the **latest output is always visible**.
- **Visual Selection Highlight**: Drag with your mouse to visually highlight any command or IP address with crisp `#264f78` highlighting.
- **Instant Copy**: Automatically copies highlighted text to your clipboard upon mouse release, via **`Ctrl+Shift+C`**, or via **`Ctrl+C`**.
- **Word / IP Quick Copy**: Double-click any word or IP address (e.g. `192.168.1.1` or `GigabitEthernet0/1`) to instantly highlight and copy it.
- **Right-Click Context Menu**: Right-click anywhere in the terminal canvas to access Copy, Paste, Select All, and Clear Scrollback.

---

## 🏛️ System Architecture

```
+-----------------------------------------------------------------------------+
|                            User Desktop Interface                           |
|       (Browser: Firefox / Chrome)             (CLI: eveterminal /T /N R1)   |
+------------------------------------+----------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                      Single-Instance IPC Dispatcher                         |
|      (/tmp/eveterminal_single_instance_ipc Unix Domain Local Socket)        |
+------------------------------------+----------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                           EveTerminal Main Window                           |
|  +--------------------+  +-----------------------------------------------+  |
|  | Session Tree Dock  |  | Multi-Tab & Tiled Rows Manager (R1, R2, R3)    |  |
|  | (Saved Sessions)   |  | +-------------------------------------------+ |  |
|  +--------------------+  | | Interactive Monospace Canvas              | |  |
|  | Macro Button Bar   |  | | - VT100 / VT220 / ANSI Screen Buffer      | |  |
|  | [sh ip int br] [+] |  | | - Copy on Select & Right-Click Paste       | |  |
|  +--------------------+  | +-------------------------------------------+ |  |
|                          +-----------------------------------------------+  |
+------------------------------------+----------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                       Asynchronous Protocol Backends                        |
|  [RFC 854/855 Telnet Engine]   [Paramiko SSHv2]   [PySerial]   [PTY Bash]   |
|  - Keepalives (IAC NOP 15s)    - Keepalives (15s) - /dev/ttyUSB- Local Shell|
|  - SGA, ECHO, NAWS, TTYPE      - RSA/Ed25519 Keys - Baud Config- Termios    |
+------------------------------------+----------------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------------+
|                       Lab & Production Endpoints                            |
|       (EVE-NG Routers)        (GNS3 Nodes)        (Cisco / Juniper Devices) |
+-----------------------------------------------------------------------------+
```

---

## 🐧 Supported Platforms

| Distribution | Version | Architecture | Display Server |
| :--- | :--- | :--- | :--- |
| **Debian** | 11 (Bullseye), 12 (Bookworm), 13 (Trixie) | `amd64`, `arm64` | Wayland & X11 / Xwayland |
| **Ubuntu** | 20.04, 22.04, 24.04 LTS | `amd64`, `arm64` | Wayland & X11 |
| **Linux Mint** | 20, 21, 22 | `amd64` | X11 & Wayland |
| **Kali Linux** | 2023.x, 2024.x | `amd64`, `arm64` | X11 & Wayland |
| **Pop!_OS** | 22.04, COSMIC | `amd64` | Wayland & X11 |
| **Fedora / RHEL** | 38, 39, 40+ | `amd64` | Wayland & X11 |
| **Arch Linux** | Rolling | `amd64` | Wayland & X11 |

---

## 🚀 Quick 1-Command Installation

Open your terminal and run:

```bash
git clone https://github.com/AtharvK-Cyber/EveTerminal.git
cd EveTerminal
sudo bash install.sh
```

### What `install.sh` handles automatically:
1. Installs all required dependencies (`python3-pyqt6`, `python3-paramiko`, `python3-serial`).
2. Deploys the application payload to `/opt/eveterminal`.
3. Creates global CLI launchers (`/usr/local/bin/eveterminal` and alias `/usr/local/bin/securecrt-linux`).
4. Installs the high-resolution vector icon (`eveterminal.svg`) and desktop menu launcher.
5. Places a direct shortcut on your desktop (`~/Desktop/eveterminal.desktop`) and marks it trusted.
6. **Registers EveTerminal as default handler for `telnet://` and `ssh://`** across your desktop environment and browser.

---

## 🔄 Updating & Automatic Rollback Guide

Already using EveTerminal on your laptop? You can easily upgrade to get all the latest features (such as the **Command Window Broadcast Bar**, tab auto-completion improvements, and performance patches) without losing your sessions or settings.

### ⚡ One-Line Instant Updater

Run this single command from your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/AtharvK-Cyber/EveTerminal/main/update.sh | sudo bash
```

*(Or if you already have the repository cloned on your laptop:)*
```bash
cd ~/EveTerminal && git pull && sudo ./update.sh
```

#### What the updater does automatically:
1. **Safety Backup**: Creates an automatic snapshot of your current working version at `/opt/eveterminal.backup`.
2. **Pulls Latest Code**: Fetches the newest release with all new features and bugfixes.
3. **Deploys Application**: Updates binaries, launchers, desktop entries, and icon caches without disrupting your saved sessions.
4. **Installs Rollback Utility**: Equips your system with the global `eveterminal-rollback` command.

---

### 🛡️ One-Command Automatic Rollback

If an update ever causes an unexpected issue or behavior on your laptop, **you can instantly roll back to your previous working version with one command**:

```bash
sudo eveterminal-rollback
```

*(Or via one-line curl from anywhere:)*
```bash
curl -fsSL https://raw.githubusercontent.com/AtharvK-Cyber/EveTerminal/main/rollback.sh | sudo bash
```

*(Or inside your cloned repository:)*
```bash
sudo ./rollback.sh
```

#### How the Rollback Works:
- Instantly detects `/opt/eveterminal.backup`.
- Restores all previous binaries, libraries, and launchers.
- Requires zero manual configuration or file editing.
- Leaves your user settings and saved sessions in `~/.config/eveterminal` completely untouched.

---

## 📦 Installation via Standalone `.deb` Package

You can also compile and install a standalone Debian package:

```bash
# Build the .deb installer
bash package_deb.sh

# Install with dpkg
sudo dpkg -i eveterminal_1.0.0_amd64.deb
sudo apt-get install -f   # Resolve dependencies if needed
```

---

## 🌐 EVE-NG & Browser One-Click Integration

Once installed, **no complex browser setup is needed**:

1. Open your EVE-NG lab in **Firefox**, **Chrome**, **Brave**, or **Edge**.
2. Click any router node (e.g., `R1`).
3. Your browser will show a prompt:
   - *"Open with EveTerminal?"*
   - Check **"Always allow <eve-ip> to open these links"**.
   - Click **Open Link**.
4. The router console opens immediately inside EveTerminal.
5. Click `R2`, `R3`, `R4` $\rightarrow$ they attach automatically as new tabs (`R2`, `R3`) in the **same window**!

---

## 💻 CLI Flags & Usage Guide

```bash
# Connect to a router in a new tab (named R1)
eveterminal /T /N "R1" telnet://192.168.1.100:32769

# Connect with explicit IP and port
eveterminal /TELNET 192.168.1.100 32770

# Connect via SSHv2
eveterminal /SSH2 admin@192.168.1.1 22

# Connect to serial console (/dev/ttyUSB0 at 9600 baud)
eveterminal /SERIAL /dev/ttyUSB0 9600

# Open in horizontal tiled rows layout (R1, R2, R3 format)
eveterminal --rows /N "R1" telnet://192.168.1.100 32769

# Run a Python automation script
eveterminal /SCRIPT /path/to/backup_configs.py
```

### Full CLI Options Reference

| Flag | Equivalent | Description |
| :--- | :--- | :--- |
| `/T` | `--tab` | Forces connection to open in a new tab inside running window |
| `/N "<name>"` | `--name`, `-t`, `/TITLE=` | Specifies tab and pane title (e.g. `R1`, `Core-SW1`) |
| `/ROWS` | `--rows` | Displays open terminals tiled horizontally as stacked rows |
| `/COLS` | `--columns` | Displays open terminals tiled vertically as side-by-side columns |
| `/TELNET <h> <p>`| `telnet://<h>:<p>` | Connects via RFC 854/855 Telnet |
| `/SSH2 <h> <p>` | `ssh://<u>@<h>:<p>` | Connects via SSHv2 |
| `/SERIAL <p> <b>`| `-serial <p> <b>` | Connects to hardware serial port (e.g. `/dev/ttyUSB0 9600`) |
| `/SCRIPT <path>` | `--script <path>` | Executes Python automation script via `crt` shim |

---

## ⌨️ Keyboard Shortcuts Reference

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Tab`** | Autocomplete | Native Cisco IOS command completion (`show ip int bri` $\rightarrow$ `brief`) |
| **`Ctrl+Shift+6`** or **`Ctrl+^`** | Cisco Break | Aborts running ping, traceroute, or DNS lookup |
| **`Ctrl+Tab`** | Next Tab | Cycles to the next open session tab |
| **`Left-Click + Drag`** | Select & Copy | Highlights text with visual feedback and copies to clipboard |
| **`Double-Click`** | Word Copy | Instantly selects and copies word, IP address, or interface name |
| **`Right-Click (Canvas)`** | Context Menu | Context menu with Copy, Paste, Select All, and Clear Scrollback |
| **`Ctrl+Shift+C`** | Copy | Copies selected terminal text to clipboard (also `Ctrl+C` if text selected) |
| **`Ctrl+Shift+V`** | Paste | Pastes clipboard text directly into the active session |
| **`Ctrl+Shift+A`** | Select All | Selects all visible screen content |
| **`Mouse Wheel`** | Scroll | Smoothly scrolls up/down through full terminal output history |
| **`Shift+PageUp / Down`** | Page Scroll | Scrolls up or down by half a page |
| **`Shift+End`** | Snap to Live | Snaps view immediately to the live output (bottom) |
| **`Ctrl+Shift+B`** or **`Alt+F3`** | Command Window | Toggles split bottom Command Window to broadcast commands to all sessions |
| **`Right-Click (Bottom/Tab)`** | Send to All | Opens Command Window preconfigured to broadcast to all devices |
| **`Alt+Q`** | Quick Connect | Opens Quick Connect dialog (Telnet/SSH/Serial) |
| **`Alt+C`** | Session Manager | Toggles the Saved Session Tree sidebar |
| **`Alt+B`** | Clone Session | Duplicates active session connection in a new tab |
| **`Ctrl+Q`** | Exit | Closes EveTerminal and disconnects active sessions |
| **`Right-Click (Tab)`** | Tab Menu | Rename tab, clone session, or close tab |

---

## 🔧 Troubleshooting & FAQ

### Q1: Clicking an EVE-NG node opens default terminal instead of EveTerminal
**Cause**: The desktop MIME association for `x-scheme-handler/telnet` was overwritten.  
**Fix**:
```bash
xdg-mime default eveterminal.desktop x-scheme-handler/telnet
xdg-mime default eveterminal.desktop x-scheme-handler/ssh
```

### Q2: Double-clicking the Desktop icon asks "Execute or View?"
**Cause**: GNOME / KDE security policy requires desktop shortcuts to be marked as trusted.  
**Fix**:
```bash
gio set ~/Desktop/eveterminal.desktop metadata::trusted true
chmod +x ~/Desktop/eveterminal.desktop
```

### Q3: Serial console permission denied (`/dev/ttyUSB0`)
**Cause**: Your Linux user does not belong to the serial dialout group.  
**Fix**:
```bash
sudo usermod -aG dialout $USER
```
*(Log out and log back in for group membership to take effect).*

### Q4: Running under pure Wayland shows fractional scaling font blur
**Cause**: Qt Wayland fractional scaling mismatch.  
**Fix**:
```bash
QT_QPA_PLATFORM=xcb eveterminal
```

---

## 🤝 Contributing

We welcome contributions from network engineers, developers, and lab enthusiasts!
Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, unit testing instructions, and pull request guidelines.

---

## ⚖️ Clean-Room Notice & Legal Disclaimers

- **Clean-Room Implementation**: EveTerminal is an independent, clean-room, open-source software project written from scratch in Python and Qt. It contains **no proprietary code, assembly, or libraries** from VanDyke Software, Inc. It does not tamper with, reverse engineer, or bypass any commercial licensing or activation mechanisms.
- **Trademark Notice**: *SecureCRT* is a registered trademark of VanDyke Software, Inc. *EVE-NG* is a registered trademark of EVE-NG Ltd. *Cisco* is a registered trademark of Cisco Systems, Inc. *Juniper* is a registered trademark of Juniper Networks, Inc. EveTerminal is an independent open-source project and is **not affiliated with, endorsed by, or sponsored by VanDyke Software, Inc., EVE-NG Ltd., Cisco Systems, Inc., or Juniper Networks, Inc.** All product names, trademarks, and registered trademarks are property of their respective owners.

---

## 📄 License

EveTerminal is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 Cleanroom Terminal Contributors.

---

<details>
<summary><b>🔍 Search Keywords</b></summary>

SecureCRT alternative, SecureCRT for Linux, SecureCRT replacement, free SecureCRT, open source SecureCRT, EVE-NG terminal, EVE-NG telnet client, EVE-NG console client, GNS3 terminal, PNETLab terminal, Cisco lab terminal, CCNA lab tools, CCNP lab tools, CCIE lab tools, network lab terminal emulator, Linux terminal emulator for networking, multi-tab telnet client, telnet keepalive, SSH terminal client, PyQt6 terminal, Paramiko SSH, Cisco IOS tab completion, telnet disconnect fix, EVE-NG session timeout fix, DevNet tools, network automation terminal

</details>
