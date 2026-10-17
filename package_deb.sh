#!/usr/bin/env bash
# ==============================================================================
# Script to build a standalone, double-clickable .deb installer for EveTerminal
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="eveterminal"
VERSION="1.0.0"
ARCH="amd64"
DEB_DIR="${SCRIPT_DIR}/build_deb/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "Building Debian package: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb..."

rm -rf "${SCRIPT_DIR}/build_deb"
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}/opt/${PACKAGE_NAME}"
mkdir -p "${DEB_DIR}/usr/local/bin"
mkdir -p "${DEB_DIR}/usr/share/applications"
mkdir -p "${DEB_DIR}/usr/share/icons/hicolor/scalable/apps"

# Copy control file
cat << 'EOF' > "${DEB_DIR}/DEBIAN/control"
Package: eveterminal
Version: 1.0.0
Section: net
Priority: optional
Architecture: amd64
Provides: securecrt-linux
Maintainer: EveTerminal Developers <dev@local>
Depends: python3 (>= 3.9), python3-pyqt6 | python3-pyside6, python3-paramiko, python3-serial
Description: Multi-tab & horizontal tiled terminal client for EVE-NG & Cisco labs
 An independent clean-room terminal client providing multi-session tabbed
 and horizontal tiled row layouts (R1, R2, R3 format in the same window).
 Features Telnet keepalives, Cisco IOS command autocompletion, live hostname
 prompt detection, and full SecureCRT session configuration compatibility.
EOF

# Copy post-installation hook
cat << 'EOF' > "${DEB_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database /usr/share/applications || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
fi
if [ -x /usr/bin/xdg-mime ]; then
    xdg-mime default eveterminal.desktop x-scheme-handler/telnet || true
    xdg-mime default eveterminal.desktop x-scheme-handler/ssh || true
fi
exit 0
EOF
chmod 755 "${DEB_DIR}/DEBIAN/postinst"

# Copy application files
cp -r "${SCRIPT_DIR}/eveterminal" "${DEB_DIR}/opt/${PACKAGE_NAME}/"
cp -r "${SCRIPT_DIR}/bin" "${DEB_DIR}/opt/${PACKAGE_NAME}/"
chmod +x "${DEB_DIR}/opt/${PACKAGE_NAME}/bin/eveterminal"
chmod +x "${DEB_DIR}/opt/${PACKAGE_NAME}/bin/securecrt-linux"

# Create symlinks in /usr/local/bin
ln -sf "/opt/${PACKAGE_NAME}/bin/eveterminal" "${DEB_DIR}/usr/local/bin/eveterminal"
ln -sf "/opt/${PACKAGE_NAME}/bin/securecrt-linux" "${DEB_DIR}/usr/local/bin/securecrt-linux"

# Copy desktop and icon files
cp "${SCRIPT_DIR}/debian/eveterminal.desktop" "${DEB_DIR}/usr/share/applications/"
chmod 644 "${DEB_DIR}/usr/share/applications/eveterminal.desktop"

cp "${SCRIPT_DIR}/debian/eveterminal.svg" "${DEB_DIR}/usr/share/icons/hicolor/scalable/apps/"
chmod 644 "${DEB_DIR}/usr/share/icons/hicolor/scalable/apps/eveterminal.svg"

# Build package
dpkg-deb --build --root-owner-group "${DEB_DIR}" "${SCRIPT_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

rm -rf "${SCRIPT_DIR}/build_deb"
echo "✓ Successfully built: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "  You can double-click this file in Debian/Ubuntu to install via Software Center / GDebi."
