# EZMonitorModeButton

A simple yet robust Python GUI for the Raspberry Pi to easily enable and disable monitor mode on a wireless interface.

<img width="384" height="197" alt="guiez" src="https://repository-images.githubusercontent.com/1140614965/7aa3f1f6-befa-4039-afb9-df3dae1b58b8" />

## Version 1.3.1 (New!)
*   **Custom Glowing Toggle Switch:** Features a Canvas-based sliding switch flanked by status labels. Both ON and OFF are visible, with only the active state glowing (neon green for ON, bright red for OFF).
*   **Smooth Non-Freezing GUI:** Ported command executions (`airmon-ng start/stop`) to background threads. The interface stays responsive and updates status messages in real-time during transitions.
*   **Precise Interface Tracking:** Implemented exact status checking using a custom `iw dev` parser (with `iwconfig` fallback) to eliminate false positive states when multiple wireless adapters are active.
*   **Smart Tool Launcher Validation:** Detects if Wifite, Wireshark, or Kismet are installed. If a tool is missing, its launch button is gracefully disabled and labeled `(N/A)`.
*   **Slate Dark Theme:** Upgraded to a modern slate/charcoal styling configured via `ttk.Style`.
*   **Window Centering:** GUI centers itself on launch for better desktop UX.
*   **Interface Refresh:** Clear button to scan and refresh the list of available wireless cards.

## Installation (Recommended)

### Option 1: Debian Package (Pi/Ubuntu/Debian)

Download the latest `.deb` file from the [Releases](https://github.com/ldl805/EZMonitorModeButton/releases) page and install it using:

```bash
sudo apt update
sudo apt install ./ezmonitormode_1.3.1_all.deb
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
