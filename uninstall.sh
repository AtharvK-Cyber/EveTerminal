#!/usr/bin/env bash
# ==============================================================================
# EveTerminal — Uninstaller Script
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run with sudo: sudo ./uninstall.sh"
    exit 1
fi

echo "[*] Removing EveTerminal from system..."

rm -rf /opt/eveterminal
rm -f /usr/local/bin/eveterminal
rm -f /usr/local/bin/securecrt-linux
rm -f /usr/share/applications/eveterminal.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/eveterminal.svg

# Remove desktop icons for users
REAL_USER="${SUDO_USER:-$USER}"
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
    USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    rm -f "${USER_HOME}/Desktop/eveterminal.desktop"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

echo "✓ EveTerminal successfully removed."
