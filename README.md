# EZMonitorModeButton

A simple yet robust Python GUI for the Raspberry Pi to easily enable and disable monitor mode on a wireless interface.

 _________________________
 

NEW VERSION 2.0 -  CHANGELOG:
  1.  Packet Injection Testing Button (aireplay-ng --test)
      • Added a one-click "Test Injection" button in monitor_gui.py.
      • Validates that monitor mode is active and automatically targets the live monitor interface to verify adapter frame injection capability.
  2.  Direct Airodump-ng Quick Launcher
      • Added a "Launch Airodump-ng" button to instantly spawn a live channel and BSSID packet sniffing terminal.
  3.  Multi-Band Channel Hopping Engine & Presets
      • Expanded channel control with selectable hopping profiles:
	  • 1, 6, 11 (2.4GHz)
	  • All 2.4GHz (1-14)
	  • 5GHz UNII-1/3 (36-165)
	  • All Channels (combined 2.4 & 5 GHz)

  4.  RFKill Driver Soft-Block Safeguards
      • Added rfkill unblock wifi || rfkill unblock all to stop_monitor_mode.sh to prevent kernel/hardware soft-blocks on USB Wi-Fi dongles during service restoration.
  5.  Broad Linux & Raspberry Pi Terminal Compatibility
      • Upgraded monitor_gui.py:714-753 with automatic detection for lxterminal, xfce4-terminal, mate-terminal, konsole, terminator, tilix, alacritty, kitty, foot, xterm, and gnome-terminal.
  6.  Safe Parsing & Exception Hardening
      • Hardened iw dev and iwconfig output decoding with .decode(errors='replace') across all subprocess calls.
      • Filtered out non-wireless interfaces (no wireless extensions) in iwconfig fallback mode.
  7.  Packaging, Documentation, & Tests
      • Bumped version to 2.0.0 in pyproject.toml, build_deb.sh, ezmonitormode.desktop, and monitor_gui.py.
      • Updated README.md with the Version 2.0.0 changelog.
      • Expanded test_monitor_gui.py to 24 unit tests covering injection testing, terminal detection, hopping controls, and interface decoders.


   _________________________

  
In wireless security auditing, the standard way to enable monitor mode is using the  aircrack-ng  suite:

   1.  sudo airmon-ng check kill  (kills network managers,  wpa_supplicant ,  dhcpcd , etc.)
   2.  sudo airmon-ng start wlan0 
    
         While entering monitor mode is easy, exiting it can be tedious and frustrating:

_________________________
The Annoyance:

   
 When  airmon-ng check kill  runs, it completely destroys the system's normal internet connectivity. To get back online, a user has to stop monitor mode and manually restart all networking services in the correct sequence.


_________________________

  
How EZMonitorModeButton solves this: 


   This program automatically stops the monitor interface and sequentially restarts  NetworkManager, wpa_supplicant, avahi-daemon,and dhcpcd .
   
_________________________

  
The Value: 

  
   It acts as a safety net. Instead of leaving the user with broken internet, a single click restores normal network state cleanly.
   
_________________________


              ┌────────────────┐
    ⋮         │ Start Auditing │
    ⋮         └────────────────┘
    ⋮                  │
    ⋮                  ▼
    ⋮         ◇───────────────◇
    ⋮         │ Choose Method │
    ⋮         ◇───────────────◇
    ⋮                 │ Command Line                      EZMONITORMODEBUTTON
    ⋮                 ▼
    ⋮         ┌────────────────────────────────┐    ┌──────────────────────┐
    ⋮         │ Type sudo airmon-ng check kill │    │ Click Glow Switch ON │
    ⋮         └────────────────────────────────┘    └──────────────────────┘
    ⋮                          │
    ⋮                          ▼
    ⋮         ┌─────────────────────────────────┐
    ⋮         │ Type sudo airmon-ng start wlan0 │
    ⋮         └─────────────────────────────────┘
    ⋮                          │
    ⋮                          ▼
    ⋮         ┌────────────────────┐
    ⋮         │ Auditing Completed │
    ⋮         └────────────────────┘
    ⋮                    │ Manual Cleanup
    ⋮                    ▼
    ⋮         ┌────────────────────────────────────────────────────────────┐    ┌───────────────────────┐
    ⋮         │ Type stop commands + restart NetworkManager/wpa_supplicant │    │ Click Glow Switch OFF │
    ⋮         └────────────────────────────────────────────────────────────┘    └───────────────────────┘
    ⋮                                                                                       │
    ⋮                                                                                       ▼
    ⋮         ┌─────────────────────────────────┐
    ⋮         │ Internet Restored Automatically │
    ⋮         └─────────────────────────────────┘
    ⋮
    ⋮     


## Version 2.0.0 (Major Release!)
*   **Packet Injection Testing:** Integrated one-click frame injection test via `aireplay-ng --test <interface>` with live terminal output.
*   **Airodump-ng Quick Launcher:** Direct launcher for live network scanning and BSSID discovery.
*   **Multi-Band Channel Hopping Engine:** Selectable auto-hopping presets including `1, 6, 11 (2.4GHz)`, `All 2.4GHz (1-14)`, `5GHz UNII-1/3 (36-165)`, and `All Channels`.
*   **RFKill Driver Safeguards:** Automatically unblocks wireless interfaces (`rfkill unblock wifi`) during network restoration to prevent hardware soft-blocks on USB dongles.
*   **Broad Terminal Compatibility:** Auto-detects and supports `lxterminal`, `xfce4-terminal`, `mate-terminal`, `konsole`, `terminator`, `tilix`, `alacritty`, `kitty`, `foot`, `xterm`, and `gnome-terminal`.
*   **Hardened Device Parsing:** Unicode-safe decoding and robust `iwconfig` filtering to ignore non-wireless interfaces.

## Version 1.5.1
*   **Attribute Order Fix:** Fixed initialization sequence in MonitorGUI.
*   **Live Channel Controls:** Added real-time channel switching and interface telemetry.

## Version 1.4.2
*   **Subprocess Timeout Safeguards:** Protects GUI thread from freezing if a wireless driver hangs.
*   **Smart Interface Injection:** Automatically passes target monitor interfaces to Wireshark (`-i`), Wifite (`-i`), and Kismet (`-c`).
*   **Robust Dependency Guard:** Gracefully warns and disables action if the `airmon-ng` suite is missing.

## Version 1.4.1
*   **Targeted Interface Disabling:** Stop scripts now target specific monitor interfaces rather than alphabetically first.
*   **Crash Safeguards:** Fixed a GUI refresh crash when started with no adapters connected, and added safe Unicode error decoding.
*   **Legacy OS Compatibility:** Restores `dhcpcd` networking services on legacy Pi OS installations.
*   **UX/Aesthetics:** Added interactive mouse cursor indicator and hover outline animations for the custom slider.
*   **Subprocess Compatibility:** Runs terminal emulators as the original desktop user when launched via root wrapper to bypass desktop permission blocks.

## Version 1.4.0
*   **Collapsible Tools Panel:** Added a toggle button to collapse the Quick Tools section at the bottom, dynamically resizing the window to make only the main button/switch GUI visible.
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
sudo apt install ./ezmonitormode_2.0.0_all.deb
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
