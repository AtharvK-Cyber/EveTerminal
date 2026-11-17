#!/usr/bin/env bash
# ==============================================================================
# EveTerminal — One-Line Automated Updater for Linux
# Updates EveTerminal to the latest version while automatically preserving
# a backup at /opt/eveterminal.backup for instant one-command rollback.
# ==============================================================================

set -e

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}          EveTerminal — Automated Software Updater              ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Check for root / sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] This updater requires administrative privileges.${NC}"
    if [ -t 0 ]; then
        echo -e "    Re-running with sudo..."
        exec sudo "$0" "$@"
    else
        echo -e "${RED}[ERROR] Please run with sudo: curl -fsSL https://raw.githubusercontent.com/AtharvK-Cyber/EveTerminal/main/update.sh | sudo bash${NC}"
        exit 1
    fi
fi

INSTALL_DIR="/opt/eveterminal"
BACKUP_DIR="/opt/eveterminal.backup"
BIN_LINK="/usr/local/bin/eveterminal"
ALIAS_LINK="/usr/local/bin/securecrt-linux"
ROLLBACK_LINK="/usr/local/bin/eveterminal-rollback"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor/scalable/apps"

# 1. Automatic Safe Backup
if [ -d "${INSTALL_DIR}" ] && [ -n "$(ls -A "${INSTALL_DIR}" 2>/dev/null)" ]; then
    echo -e "\n${BLUE}[1/5] Creating safety snapshot at ${BACKUP_DIR}...${NC}"
    rm -rf "${BACKUP_DIR}"
    cp -r "${INSTALL_DIR}" "${BACKUP_DIR}"
    echo -e "      ${GREEN}✓ Backup created. If needed, rollback anytime with: sudo eveterminal-rollback${NC}"
else
    echo -e "\n${YELLOW}[1/5] No prior installation detected at ${INSTALL_DIR}. Performing fresh deployment...${NC}"
fi

# 2. Acquire latest source
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
TEMP_DIR=""
CLEANUP_TEMP=false

echo -e "\n${BLUE}[2/5] Fetching latest release from GitHub (AtharvK-Cyber/EveTerminal)...${NC}"
if [ -n "$SCRIPT_DIR" ] && [ -d "${SCRIPT_DIR}/eveterminal" ] && [ -d "${SCRIPT_DIR}/.git" ]; then
    echo -e "      Updating current Git workspace..."
    cd "${SCRIPT_DIR}"
    git fetch --all -q
    git reset --hard origin/main -q || git pull origin main -q
    SOURCE_DIR="${SCRIPT_DIR}"
elif [ -n "$SCRIPT_DIR" ] && [ -d "${SCRIPT_DIR}/eveterminal" ]; then
    SOURCE_DIR="${SCRIPT_DIR}"
else
    TEMP_DIR=$(mktemp -d /tmp/eveterminal_update_XXXXXX)
    CLEANUP_TEMP=true
    if ! command -v git >/dev/null 2>&1; then
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update -qq && apt-get install -y -qq git
        fi
    fi
    git clone --depth 1 https://github.com/AtharvK-Cyber/EveTerminal.git "${TEMP_DIR}" -q
    SOURCE_DIR="${TEMP_DIR}"
fi

# 3. Check and install any new prerequisites
echo -e "${BLUE}[3/5] Verifying system dependencies...${NC}"
if command -v apt-get >/dev/null 2>&1; then
    apt-get install -y -qq python3 python3-pyqt6 python3-paramiko python3-serial libgl1 2>/dev/null || true
fi

# 4. Deploy updated payload
echo -e "${BLUE}[4/5] Deploying updated application payload to ${INSTALL_DIR}...${NC}"
mkdir -p "${INSTALL_DIR}"
rm -rf "${INSTALL_DIR:?}"/*

cp -r "${SOURCE_DIR}/eveterminal" "${INSTALL_DIR}/"
cp -r "${SOURCE_DIR}/bin" "${INSTALL_DIR}/"
if [ -f "${SOURCE_DIR}/rollback.sh" ]; then
    cp "${SOURCE_DIR}/rollback.sh" "${INSTALL_DIR}/rollback.sh"
    chmod +x "${INSTALL_DIR}/rollback.sh"
fi

chmod +x "${INSTALL_DIR}/bin/eveterminal"
chmod +x "${INSTALL_DIR}/bin/securecrt-linux"
if [ -f "${INSTALL_DIR}/bin/eveterminal-rollback" ]; then
    chmod +x "${INSTALL_DIR}/bin/eveterminal-rollback"
fi

# Symlinks
ln -sf "${INSTALL_DIR}/bin/eveterminal" "${BIN_LINK}"
chmod +x "${BIN_LINK}"

ln -sf "${INSTALL_DIR}/bin/securecrt-linux" "${ALIAS_LINK}"
chmod +x "${ALIAS_LINK}"

if [ -f "${INSTALL_DIR}/rollback.sh" ]; then
    ln -sf "${INSTALL_DIR}/rollback.sh" "${ROLLBACK_LINK}"
    chmod +x "${ROLLBACK_LINK}"
fi

# 5. Refresh Icons, Desktop entries, and MIME associations
echo -e "${BLUE}[5/5] Refreshing desktop integrations and icon caches...${NC}"
mkdir -p "${ICON_DIR}"
cp "${SOURCE_DIR}/debian/eveterminal.svg" "${ICON_DIR}/eveterminal.svg" 2>/dev/null || true

mkdir -p "${DESKTOP_DIR}"
cp "${SOURCE_DIR}/debian/eveterminal.desktop" "${DESKTOP_DIR}/eveterminal.desktop" 2>/dev/null || true
chmod 644 "${DESKTOP_DIR}/eveterminal.desktop" 2>/dev/null || true

REAL_USER="${SUDO_USER:-$USER}"
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
    USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    USER_DESKTOP="${USER_HOME}/Desktop"
    if [ -d "$USER_DESKTOP" ]; then
        cp "${SOURCE_DIR}/debian/eveterminal.desktop" "${USER_DESKTOP}/eveterminal.desktop" 2>/dev/null || true
        chown "$REAL_USER:$REAL_USER" "${USER_DESKTOP}/eveterminal.desktop" 2>/dev/null || true
        chmod +x "${USER_DESKTOP}/eveterminal.desktop" 2>/dev/null || true
        if command -v gio >/dev/null 2>&1; then
            sudo -u "$REAL_USER" gio set "${USER_DESKTOP}/eveterminal.desktop" metadata::trusted true 2>/dev/null || true
        fi
    fi
    sudo -u "$REAL_USER" xdg-mime default eveterminal.desktop x-scheme-handler/telnet 2>/dev/null || true
    sudo -u "$REAL_USER" xdg-mime default eveterminal.desktop x-scheme-handler/ssh 2>/dev/null || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# Clean up temp clone if used
if [ "$CLEANUP_TEMP" = true ] && [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ Update Successful! EveTerminal is now up-to-date.${NC}"
echo -e "  What's New in this update:"
echo -e "    • 📢 Command Window (Broadcast to R1, R2, R3... via Ctrl+Shift+C)"
echo -e "    • 🎯 Right-click bottom bar / tab 'Send to All Devices'"
echo -e "    • 📜 Command history navigation (Up / Down arrows)"
echo -e "    • 🔄 Automatic safety rollback support (sudo eveterminal-rollback)"
echo -e "  "
echo -e "  ${YELLOW}Rollback Safety Net:${NC}"
echo -e "  If you ever need to revert to your previous version, simply run:"
echo -e "    ${YELLOW}sudo eveterminal-rollback${NC}"
echo -e "${GREEN}================================================================${NC}\n"
