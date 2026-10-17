#!/usr/bin/env bash
# ==============================================================================
# EveTerminal — One-Click Automated Installer for Debian / Ubuntu / Mint / Kali
# ==============================================================================

set -e

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}        EveTerminal — Application Installer for Linux           ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Check for root / sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] This installer requires administrative privileges.${NC}"
    echo -e "    Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/eveterminal"
BIN_LINK="/usr/local/bin/eveterminal"
ALIAS_LINK="/usr/local/bin/securecrt-linux"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor/scalable/apps"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Install prerequisites via apt
echo -e "\n${BLUE}[1/5] Installing system dependencies (Python3, Qt6, Paramiko, Serial)...${NC}"
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-pyqt6 python3-paramiko python3-serial libgl1
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y python3 python3-qt6 python3-paramiko python3-pyserial
elif command -v pacman >/dev/null 2>&1; then
    pacman -Sy --noconfirm python python-pyqt6 python-paramiko python-pyserial
fi

# 2. Deploy application payload to /opt/eveterminal
echo -e "${BLUE}[2/5] Installing application files to ${INSTALL_DIR}...${NC}"
mkdir -p "${INSTALL_DIR}"
rm -rf "${INSTALL_DIR:?}"/*

cp -r "${SCRIPT_DIR}/eveterminal" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/bin" "${INSTALL_DIR}/"
chmod +x "${INSTALL_DIR}/bin/eveterminal"
chmod +x "${INSTALL_DIR}/bin/securecrt-linux"

# 3. Create global symlinks
echo -e "${BLUE}[3/5] Setting up global launcher commands...${NC}"
ln -sf "${INSTALL_DIR}/bin/eveterminal" "${BIN_LINK}"
chmod +x "${BIN_LINK}"

ln -sf "${INSTALL_DIR}/bin/securecrt-linux" "${ALIAS_LINK}"
chmod +x "${ALIAS_LINK}"

# 4. Install desktop icon and launcher
echo -e "${BLUE}[4/5] Registering Application Menu icon & desktop entry...${NC}"
mkdir -p "${ICON_DIR}"
cp "${SCRIPT_DIR}/debian/eveterminal.svg" "${ICON_DIR}/eveterminal.svg"

mkdir -p "${DESKTOP_DIR}"
cp "${SCRIPT_DIR}/debian/eveterminal.desktop" "${DESKTOP_DIR}/eveterminal.desktop"
chmod 644 "${DESKTOP_DIR}/eveterminal.desktop"

# If invoked via sudo, detect original user's Desktop and install a direct icon there too
REAL_USER="${SUDO_USER:-$USER}"
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
    USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    USER_DESKTOP="${USER_HOME}/Desktop"
    if [ -d "$USER_DESKTOP" ]; then
        echo -e "${BLUE}[*] Placing direct shortcut on ${REAL_USER}'s Desktop...${NC}"
        cp "${SCRIPT_DIR}/debian/eveterminal.desktop" "${USER_DESKTOP}/eveterminal.desktop"
        chown "$REAL_USER:$REAL_USER" "${USER_DESKTOP}/eveterminal.desktop"
        chmod +x "${USER_DESKTOP}/eveterminal.desktop"
        # Trust desktop file for GNOME / Cinnamon / KDE
        if command -v gio >/dev/null 2>&1; then
            sudo -u "$REAL_USER" gio set "${USER_DESKTOP}/eveterminal.desktop" metadata::trusted true 2>/dev/null || true
        fi
    fi
fi

# 5. Update system caches
echo -e "${BLUE}[5/5] Updating system desktop & icon caches...${NC}"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 6. Register default MIME handler for telnet:// and ssh:// protocols
echo -e "${BLUE}[*] Registering EveTerminal as default browser handler for telnet:// and ssh://...${NC}"
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
    sudo -u "$REAL_USER" xdg-mime default eveterminal.desktop x-scheme-handler/telnet 2>/dev/null || true
    sudo -u "$REAL_USER" xdg-mime default eveterminal.desktop x-scheme-handler/ssh 2>/dev/null || true
fi
if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default eveterminal.desktop x-scheme-handler/telnet 2>/dev/null || true
    xdg-mime default eveterminal.desktop x-scheme-handler/ssh 2>/dev/null || true
fi

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ Installation Complete!${NC}"
echo -e "  You can now launch EveTerminal directly:"
echo -e "    1. From your Desktop icon (double-click)."
echo -e "    2. From your Application Menu (under Network / System / Internet)."
echo -e "    3. Or by typing 'eveterminal' (or 'securecrt-linux') in terminal."
echo -e "    4. EVE-NG nodes clicked in Firefox/Chrome will now open in EveTerminal!"
echo -e "${GREEN}================================================================${NC}\n"
