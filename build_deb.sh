#!/bin/bash
# Script to build a Debian package for EZMonitorMode

APP_NAME="ezmonitormode"
VERSION="1.1.0"
PKG_DIR="${APP_NAME}_${VERSION}_all"

echo "Building Debian package $PKG_DIR..."

# Create structure
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/$APP_NAME"
mkdir -p "$PKG_DIR/usr/share/applications"

# Create control file
cat <<EOF > "$PKG_DIR/DEBIAN/control"
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-tk, aircrack-ng, wireless-tools
Recommends: wifite, wireshark, kismet
Maintainer: ldl805 <ldl805@github.com>
Description: EZ Monitor Mode Manager
 A simple GUI to switch wireless interfaces into monitor mode and launch security tools.
 Automates airmon-ng check kill and interface management.
EOF

# Create wrapper (Improved to handle DISPLAY)
cat <<EOF > "$PKG_DIR/usr/bin/$APP_NAME"
#!/bin/bash
# Wrapper for EZMonitorMode to handle sudo and DISPLAY

# Ensure DISPLAY is set for GUI
if [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Check for sudo/root
if [ "\$EUID" -ne 0 ]; then
    # Try to use pkexec for a GUI password prompt, preserving environment
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec env DISPLAY="\$DISPLAY" XAUTHORITY="\$XAUTHORITY" python3 /usr/share/$APP_NAME/monitor_gui.py "\$@"
    else
        echo "Error: Root privileges required. Please run with: sudo -E $APP_NAME"
        exit 1
    fi
else
    python3 /usr/share/$APP_NAME/monitor_gui.py "\$@"
fi
EOF
chmod 755 "$PKG_DIR/usr/bin/$APP_NAME"

# Copy application files
cp src/ezmonitormode/monitor_gui.py "$PKG_DIR/usr/share/$APP_NAME/"
cp src/ezmonitormode/monitor_mode.sh "$PKG_DIR/usr/share/$APP_NAME/"
cp src/ezmonitormode/stop_monitor_mode.sh "$PKG_DIR/usr/share/$APP_NAME/"
cp ezmonitormode.desktop "$PKG_DIR/usr/share/applications/"

# Build package
dpkg-deb --build --root-owner-group "$PKG_DIR"

echo "Package built: ${PKG_DIR}.deb"
