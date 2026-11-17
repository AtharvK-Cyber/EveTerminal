#!/usr/bin/env bash
# ==============================================================================
# EveTerminal — Automatic Rollback Script
# Restores previous working installation from /opt/eveterminal.backup
# ==============================================================================

set -e

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${YELLOW}        EveTerminal — Automatic Version Rollback                ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Check for root / sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Administrative privileges required.${NC}"
    echo -e "    Re-running with sudo..."
    exec sudo "$0" "$@"
fi

INSTALL_DIR="/opt/eveterminal"
BACKUP_DIR="/opt/eveterminal.backup"
BIN_LINK="/usr/local/bin/eveterminal"
ALIAS_LINK="/usr/local/bin/securecrt-linux"
ROLLBACK_LINK="/usr/local/bin/eveterminal-rollback"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor/scalable/apps"

# 1. Check if backup exists
if [ ! -d "${BACKUP_DIR}" ] || [ -z "$(ls -A "${BACKUP_DIR}" 2>/dev/null)" ]; then
    echo -e "\n${RED}[ERROR] No previous backup found at ${BACKUP_DIR}.${NC}"
    echo -e "An automatic backup is created whenever you run an update or installation."
    echo -e "If you wish to reinstall the stable release from scratch, run:"
    echo -e "  ${YELLOW}git clone https://github.com/AtharvK-Cyber/EveTerminal.git && cd EveTerminal && sudo ./install.sh${NC}\n"
    exit 1
fi

echo -e "\n${BLUE}[1/4] Found verified backup at ${BACKUP_DIR}${NC}"
echo -e "${BLUE}[2/4] Restoring previous EveTerminal files...${NC}"

# Move current installation aside and restore backup
rm -rf "${INSTALL_DIR}"
cp -r "${BACKUP_DIR}" "${INSTALL_DIR}"

# 2. Ensure executable permissions
echo -e "${BLUE}[3/4] Restoring launcher permissions and symlinks...${NC}"
chmod +x "${INSTALL_DIR}/bin/eveterminal"
chmod +x "${INSTALL_DIR}/bin/securecrt-linux"
if [ -f "${INSTALL_DIR}/rollback.sh" ]; then
    chmod +x "${INSTALL_DIR}/rollback.sh"
fi

ln -sf "${INSTALL_DIR}/bin/eveterminal" "${BIN_LINK}"
chmod +x "${BIN_LINK}"

ln -sf "${INSTALL_DIR}/bin/securecrt-linux" "${ALIAS_LINK}"
chmod +x "${ALIAS_LINK}"

if [ -f "${INSTALL_DIR}/rollback.sh" ]; then
    ln -sf "${INSTALL_DIR}/rollback.sh" "${ROLLBACK_LINK}"
    chmod +x "${ROLLBACK_LINK}"
fi

# 3. Refresh desktop & icon caches
echo -e "${BLUE}[4/4] Updating desktop database and icon caches...${NC}"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

echo -e "\n${GREEN}================================================================${NC}"
echo -e "${GREEN}  ✓ Rollback Successful!${NC}"
echo -e "  EveTerminal has been restored to your previous working version."
echo -e "  Launch it with: ${YELLOW}eveterminal${NC} or from your Desktop / Application Menu."
echo -e "${GREEN}================================================================${NC}\n"
