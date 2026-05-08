# EZMonitorModeButton

A simple Python GUI for the Raspberry Pi to easily enable and disable monitor mode on a wireless interface.

<img width="400" height="542" alt="guiez" src="https://github.com/user-attachments/assets/dc761ae5-f772-4433-8b1e-be8df376c8b6" />

## Version 1.2.0 (New!)
- **Modern Interface Detection:** Uses `iw` for more reliable hardware detection.
- **Improved Display Handling:** Enhanced support for `sudo`, `pkexec`, and various graphical environments.
- **Window Centering:** GUI now centers itself on launch for better UX.
- **Interface Refresh:** New button to refresh the list of available wireless cards.
- **Quick Tools:** Shortcuts for Wireshark, Wifite, and Kismet.

## Installation (Recommended)

### Option 1: Debian Package (Pi/Ubuntu/Debian)

Download the latest `.deb` file from the [Releases](https://github.com/ldl805/EZMonitorModeButton/releases) page and install it using:

```bash
sudo apt update
sudo apt install ./ezmonitormode_1.2.0_all.deb
```

Once installed, you can launch it from your application menu or by running `ezmonitormode` in the terminal.

### Option 2: Via PyPI

```bash
pip install ezmonitormode
```

Once installed, run with `sudo -E ezmonitormode`.

### Option 3: Running from Source

1.  **Clone this repository:**
    ```bash
    git clone https://github.com/ldl805/EZMonitorModeButton.git
    cd EZMonitorModeButton
    ```
2.  **Install dependencies:**
    ```bash
    sudo apt update
    sudo apt install python3-tk aircrack-ng wireless-tools iw
    ```
3.  **Run the application:**
    ```bash
    sudo -E python3 src/ezmonitormode/monitor_gui.py
    ```

## Troubleshooting

### "no display name and no $DISPLAY environment variable"
This occurs if the GUI cannot find your screen.
- **Running via SSH:** Ensure you connected with X11 forwarding: `ssh -X user@pi`.
- **Running via sudo:** Use `sudo -E ezmonitormode` to preserve your display settings.
- **Running in Headless mode:** This application requires a graphical desktop (Pi Desktop, VNC, etc.).

## System Dependencies

Before running `ezmonitormode`, ensure you have the following system tools installed:

```bash
sudo apt update
sudo apt install python3-tk aircrack-ng wireless-tools
```

Optional tools for the shortcut buttons:
```bash
sudo apt install wifite wireshark kismet
```

## License
MIT License
