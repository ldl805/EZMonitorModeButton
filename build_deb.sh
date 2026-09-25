#!/bin/bash
# Script to build a Debian package for EZMonitorMode v3.0.0

APP_NAME="ezmonitormode"
VERSION="3.0.0"
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
Depends: python3, python3-tk, aircrack-ng, iw, rfkill, iproute2
Recommends: wireless-tools, wifite, wireshark, kismet, lxterminal
Maintainer: ldl805 <ldl805@github.com>
Description: EZ Monitor Mode Manager
 High-performance GUI and CLI utility to switch wireless interfaces into monitor mode.
 Features sysfs kernel acceleration, active gateway protection, hardware/driver detection,
 headless SSH operations, multi-band scanning, and ultra-fast 0.5s network restoration.
EOF

# Create wrapper (Handles GUI elevation, Wayland/X11 display, and headless CLI)
cat <<EOF > "$PKG_DIR/usr/bin/$APP_NAME"
#!/bin/bash
# Wrapper for EZMonitorMode supporting GUI and headless CLI

# Check if running headless CLI commands
if [ "\$#" -gt 0 ]; then
    exec python3 /usr/share/$APP_NAME/monitor_gui.py "\$@"
fi

# Ensure DISPLAY is set for desktop GUI
if [ -z "\$DISPLAY" ] && [ -z "\$WAYLAND_DISPLAY" ]; then
    if [ -e "/tmp/.X11-unix/X0" ]; then
        export DISPLAY=:0
    fi
fi

# Function to grant X11 access to root if needed
grant_x11_access() {
    if command -v xhost >/dev/null 2>&1; then
        xhost +si:localuser:root >/dev/null 2>&1
    fi
}

# Check for root
if [ "\$EUID" -ne 0 ]; then
    grant_x11_access
    
    # Try to use pkexec for a GUI password prompt
    if command -v pkexec >/dev/null 2>&1 && [ -n "\$DISPLAY" ]; then
        exec pkexec env DISPLAY="\$DISPLAY" XAUTHORITY="\$XAUTHORITY" WAYLAND_DISPLAY="\$WAYLAND_DISPLAY" XDG_RUNTIME_DIR="\$XDG_RUNTIME_DIR" python3 /usr/share/$APP_NAME/monitor_gui.py "\$@"
    else
        exec python3 /usr/share/$APP_NAME/monitor_gui.py "\$@"
    fi
else
    grant_x11_access
    exec python3 /usr/share/$APP_NAME/monitor_gui.py "\$@"
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
