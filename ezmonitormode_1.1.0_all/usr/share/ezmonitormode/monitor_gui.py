#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import shutil
import sys

# Configuration
# Default interfaces - will be updated by detection
INTERFACE = "wlan1"
MON_INTERFACE = "wlan1mon"

# Look for script in the same directory as the python script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOP_SCRIPT = os.path.join(BASE_DIR, "stop_monitor_mode.sh")

def detect_interfaces():
    """Detects wireless interfaces and returns a list."""
    try:
        output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()
        interfaces = []
        for line in output.split("\n"):
            if "IEEE 802.11" in line:
                iface = line.split()[0]
                interfaces.append(iface)
        return interfaces
    except Exception:
        return []

class MonitorGUI:
    def __init__(self, master, interfaces):
        self.master = master
        self.interfaces = interfaces
        self.interface = interfaces[0] if interfaces else "wlan1"
        
        master.title("EZ Monitor Mode 1.1.0")
        master.geometry("400x500")
        master.resizable(False, False)

        # Monitor Mode State
        self.is_monitor_on = False

        # --- Top: Interface Selection (New) ---
        if len(self.interfaces) > 1:
            iface_frame = tk.Frame(master)
            iface_frame.pack(fill="x", padx=10, pady=5)
            tk.Label(iface_frame, text="Interface:").pack(side="left")
            self.iface_var = tk.StringVar(value=self.interface)
            self.iface_menu = tk.OptionMenu(iface_frame, self.iface_var, *self.interfaces, command=self.update_interface)
            self.iface_menu.pack(side="left", fill="x", expand=True)
        else:
            tk.Label(master, text=f"Interface: {self.interface}", font=("Helvetica", 10)).pack(pady=5)

        # --- Top Half: The "Light Switch" ---
        self.switch_frame = tk.Frame(master, height=180)
        self.switch_frame.pack(fill="x", side="top", padx=10, pady=10)
        self.switch_frame.pack_propagate(False) # Keep height

        self.btn_switch = tk.Button(
            self.switch_frame, 
            text="MONITOR MODE\nOFF", 
            font=("Helvetica", 20, "bold"),
            bg="#ff4444", 
            fg="white",
            activebackground="#cc0000",
            activeforeground="white",
            command=self.toggle_monitor
        )
        self.btn_switch.pack(fill="both", expand=True)

        # --- Bottom Half: Status and Tools ---
        
        # Status Label
        self.status_var = tk.StringVar(master=master)
        self.status_var.set("Ready")
        self.status_label = tk.Label(master, textvariable=self.status_var, font=("Helvetica", 10, "italic"))
        self.status_label.pack(pady=5)

        # Tools Label
        self.tools_label = tk.Label(master, text="Quick Tools", font=("Helvetica", 12, "bold"))
        self.tools_label.pack(pady=(10, 5))

        # Tools Frame
        self.tools_frame = tk.Frame(master)
        self.tools_frame.pack(pady=5)

        # Tool Buttons
        self.btn_wifite = tk.Button(self.tools_frame, text="Wifite", width=12, height=2, command=self.run_wifite)
        self.btn_wifite.grid(row=0, column=0, padx=5, pady=5)

        self.btn_wireshark = tk.Button(self.tools_frame, text="Wireshark", width=12, height=2, command=self.run_wireshark)
        self.btn_wireshark.grid(row=0, column=1, padx=5, pady=5)

        self.btn_kismet = tk.Button(self.tools_frame, text="Kismet", width=12, height=2, command=self.run_kismet)
        self.btn_kismet.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        # Initial check
        self.check_monitor_mode()

    def update_interface(self, val):
        self.interface = val
        self.check_monitor_mode()

    def check_monitor_mode(self):
        """Checks if any interface is in monitor mode."""
        try:
            # Check for common monitor interface names or 'Mode:Monitor' in iwconfig
            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()
            if "Mode:Monitor" in output:
                # If we're looking at a specific interface, see if it's the one in monitor mode
                # Or just generally check if ANY are. For now, general.
                self.set_switch_state(True)
            else:
                self.set_switch_state(False)
        except Exception:
            # Fallback if iwconfig fails
            self.set_switch_state(False)

    def set_switch_state(self, is_on):
        self.is_monitor_on = is_on
        if is_on:
            self.btn_switch.config(
                text="MONITOR MODE\nON", 
                bg="#44ff44", 
                activebackground="#00cc00",
                fg="black",
                activeforeground="black"
            )
            self.status_var.set(f"Status: Monitor Mode Enabled")
        else:
            self.btn_switch.config(
                text="MONITOR MODE\nOFF", 
                bg="#ff4444", 
                activebackground="#cc0000",
                fg="white",
                activeforeground="white"
            )
            self.status_var.set("Status: Managed Mode (Monitor Off)")

    def toggle_monitor(self):
        if self.is_monitor_on:
            self.disable_monitor()
        else:
            self.enable_monitor()

    def run_command(self, cmd_list, description):
        """Helper to run commands and update status."""
        self.status_var.set(f"Running: {description}...")
        self.master.update()
        try:
            # Note: we use sudo here but ideally the whole app runs as root
            subprocess.run(cmd_list, check=True)
            self.status_var.set(f"Success: {description}")
            return True
        except subprocess.CalledProcessError as e:
            self.status_var.set(f"Error: {description}")
            messagebox.showerror("Error", f"Failed to run {description}.\nExit code: {e.returncode}")
            return False
        except Exception as e:
            self.status_var.set(f"Error: {description}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            return False

    def enable_monitor(self):
        """Enables monitor mode."""
        if not messagebox.askyesno("Confirm", f"Enable monitor mode on {self.interface}?\nThis will kill network processes."):
            return

        # Step 1: Kill conflicting processes
        if not self.run_command(["sudo", "airmon-ng", "check", "kill"], "Kill processes"):
            if not messagebox.askyesno("Warning", "Failed to kill processes. Continue anyway?"):
                return

        # Step 2: Start monitor mode
        if self.run_command(["sudo", "airmon-ng", "start", self.interface], f"Start Monitor Mode on {self.interface}"):
            self.set_switch_state(True)
            messagebox.showinfo("Success", f"Monitor mode enabled.")

    def disable_monitor(self):
        """Disables monitor mode."""
        if not messagebox.askyesno("Confirm", "Disable monitor mode and restore networks?"):
            return
        
        # We pass the interface to the stop script if needed, 
        # but the current stop script attempts to find wlan1mon or wlan1.
        if self.run_command(["sudo", "bash", STOP_SCRIPT], "Disable Monitor & Restore"):
            self.set_switch_state(False)
            messagebox.showinfo("Success", "Monitor mode disabled. Network restarting...")

    def get_terminal(self):
        """Finds a suitable terminal emulator."""
        for t in ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]:
            term = shutil.which(t)
            if term: return term
        return None

    def launch_in_terminal(self, cmd, title):
        term = self.get_terminal()
        if not term:
            messagebox.showerror("Error", "No terminal emulator found.")
            return
        
        full_cmd = [term, "-e", f"sudo {cmd}"]
        try:
            subprocess.Popen(full_cmd)
            self.status_var.set(f"Launched {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch {title}:\n{e}")

    def run_wifite(self):
        self.launch_in_terminal("wifite", "Wifite")

    def run_kismet(self):
        self.launch_in_terminal("kismet", "Kismet")

    def run_wireshark(self):
        try:
            subprocess.Popen(["sudo", "wireshark"])
            self.status_var.set("Launched Wireshark")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Wireshark:\n{e}")

def main():
    # Check for DISPLAY
    if "DISPLAY" not in os.environ:
        print("Error: No DISPLAY environment variable found.")
        print("EZMonitorMode is a GUI application and requires a graphical environment.")
        print("If you are using SSH, ensure you have X11 forwarding enabled (ssh -X).")
        print("If you are using sudo, try: sudo -E ezmonitormode")
        sys.exit(1)

    try:
        root = tk.Tk()
    except tk.TclError as e:
        print(f"Error: Could not initialize GUI: {e}")
        print("Ensure you have a display available and appropriate permissions.")
        sys.exit(1)

    interfaces = detect_interfaces()
    app = MonitorGUI(root, interfaces)
    root.mainloop()

if __name__ == "__main__":
    main()
