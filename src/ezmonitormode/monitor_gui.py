#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import os
import shutil
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
VERSION = "1.2.0"

def detect_interfaces():
    """Detects wireless interfaces and returns a list using 'iw dev' or 'iwconfig'."""
    interfaces = []
    # Try 'iw dev' first (modern)
    try:
        output = subprocess.check_output(["iw", "dev"], stderr=subprocess.STDOUT).decode()
        for line in output.split("\n"):
            if "Interface" in line:
                iface = line.split()[1]
                interfaces.append(iface)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to 'iwconfig'
        try:
            output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()
            for line in output.split("\n"):
                if "IEEE 802.11" in line:
                    iface = line.split()[0]
                    interfaces.append(iface)
        except Exception as e:
            logging.error(f"Failed to detect interfaces: {e}")
    
    return sorted(list(set(interfaces)))

def center_window(window, width, height):
    """Centers the window on the screen."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

class MonitorGUI:
    def __init__(self, master, interfaces):
        self.master = master
        self.interfaces = interfaces
        self.interface = interfaces[0] if interfaces else "wlan1"
        
        master.title(f"EZ Monitor Mode {VERSION}")
        center_window(master, 400, 520)
        master.resizable(False, False)

        # Style
        self.style = ttk.Style()
        
        # Monitor Mode State
        self.is_monitor_on = False

        # --- Top: Interface Selection ---
        iface_frame = tk.Frame(master)
        iface_frame.pack(fill="x", padx=15, pady=10)
        tk.Label(iface_frame, text="Wireless Interface:", font=("Helvetica", 10, "bold")).pack(side="left")
        
        if self.interfaces:
            self.iface_var = tk.StringVar(value=self.interface)
            self.iface_menu = ttk.OptionMenu(iface_frame, self.iface_var, self.interface, *self.interfaces, command=self.update_interface)
            self.iface_menu.pack(side="left", fill="x", expand=True, padx=5)
        else:
            tk.Label(iface_frame, text="No interfaces found!", fg="red").pack(side="left", padx=5)

        self.btn_refresh = tk.Button(iface_frame, text="↻", command=self.refresh_interfaces, width=2)
        self.btn_refresh.pack(side="right")

        # --- Middle: The "Light Switch" ---
        self.switch_frame = tk.Frame(master, height=180, relief="groove", borderwidth=2)
        self.switch_frame.pack(fill="x", side="top", padx=15, pady=5)
        self.switch_frame.pack_propagate(False)

        self.btn_switch = tk.Button(
            self.switch_frame, 
            text="MONITOR MODE\nOFF", 
            font=("Helvetica", 20, "bold"),
            bg="#ff4444", 
            fg="white",
            activebackground="#cc0000",
            activeforeground="white",
            relief="raised",
            command=self.toggle_monitor
        )
        self.btn_switch.pack(fill="both", expand=True)

        # --- Bottom: Status and Tools ---
        
        # Status Label
        self.status_var = tk.StringVar(master=master)
        self.status_var.set("Ready")
        self.status_label = tk.Label(master, textvariable=self.status_var, font=("Helvetica", 10, "italic"), wraplength=350)
        self.status_label.pack(pady=10)

        # Tools Section
        separator = ttk.Separator(master, orient='horizontal')
        separator.pack(fill='x', padx=15, pady=5)

        tk.Label(master, text="Quick Tools", font=("Helvetica", 12, "bold")).pack(pady=5)

        self.tools_frame = tk.Frame(master)
        self.tools_frame.pack(pady=5)

        # Tool Buttons with better styling
        btn_opts = {"width": 15, "height": 2}
        self.btn_wifite = tk.Button(self.tools_frame, text="Launch Wifite", **btn_opts, command=self.run_wifite)
        self.btn_wifite.grid(row=0, column=0, padx=5, pady=5)

        self.btn_wireshark = tk.Button(self.tools_frame, text="Launch Wireshark", **btn_opts, command=self.run_wireshark)
        self.btn_wireshark.grid(row=0, column=1, padx=5, pady=5)

        self.btn_kismet = tk.Button(self.tools_frame, text="Launch Kismet", **btn_opts, command=self.run_kismet)
        self.btn_kismet.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        # Initial check
        self.check_monitor_mode()

    def refresh_interfaces(self):
        self.interfaces = detect_interfaces()
        if not self.interfaces:
            self.status_var.set("No interfaces found.")
            return
        
        # Update OptionMenu
        menu = self.iface_menu["menu"]
        menu.delete(0, "end")
        for iface in self.interfaces:
            menu.add_command(label=iface, command=lambda v=iface: self.update_interface(v))
        
        if self.interface not in self.interfaces:
            self.interface = self.interfaces[0]
            self.iface_var.set(self.interface)
        
        self.status_var.set("Interfaces refreshed.")
        self.check_monitor_mode()

    def update_interface(self, val):
        self.interface = val
        self.iface_var.set(val)
        self.check_monitor_mode()

    def check_monitor_mode(self):
        """Checks if the selected interface is in monitor mode."""
        try:
            output = subprocess.check_output(["iwconfig", self.interface], stderr=subprocess.STDOUT).decode()
            if "Mode:Monitor" in output:
                self.set_switch_state(True)
            else:
                self.set_switch_state(False)
        except Exception:
            # Maybe it's named differently now (e.g. wlan0mon)
            try:
                output = subprocess.check_output(["iwconfig"], stderr=subprocess.STDOUT).decode()
                if f"{self.interface}mon" in output or "Mode:Monitor" in output:
                     # This is a bit loose but helps detection
                     self.set_switch_state(True)
                else:
                     self.set_switch_state(False)
            except:
                self.set_switch_state(False)

    def set_switch_state(self, is_on):
        self.is_monitor_on = is_on
        if is_on:
            self.btn_switch.config(
                text="MONITOR MODE\nON", 
                bg="#44ff44", 
                activebackground="#00cc00",
                fg="black",
                activeforeground="black",
                relief="sunken"
            )
            self.status_var.set(f"Monitoring enabled on {self.interface}")
        else:
            self.btn_switch.config(
                text="MONITOR MODE\nOFF", 
                bg="#ff4444", 
                activebackground="#cc0000",
                fg="white",
                activeforeground="white",
                relief="raised"
            )
            self.status_var.set(f"{self.interface} is in Managed Mode")

    def toggle_monitor(self):
        if self.is_monitor_on:
            self.disable_monitor()
        else:
            self.enable_monitor()

    def run_command(self, cmd_list, description):
        logging.info(f"Running: {' '.join(cmd_list)}")
        self.status_var.set(f"Executing: {description}...")
        self.master.update()
        try:
            subprocess.run(cmd_list, check=True, capture_output=True)
            self.status_var.set(f"Completed: {description}")
            return True
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode() if e.stderr else str(e)
            logging.error(f"Command failed: {description} - {err_msg}")
            self.status_var.set(f"Failed: {description}")
            messagebox.showerror("Error", f"Failed to {description}.\n\n{err_msg}")
            return False

    def enable_monitor(self):
        if not messagebox.askyesno("Confirm", f"Enable monitor mode on {self.interface}?\n\nThis will disconnect current WiFi connections."):
            return

        # Step 1: Kill conflicting processes
        if not self.run_command(["sudo", "airmon-ng", "check", "kill"], "Kill conflicting processes"):
            if not messagebox.askyesno("Warning", "Could not kill some processes. Continue?"):
                return

        # Step 2: Start monitor mode
        if self.run_command(["sudo", "airmon-ng", "start", self.interface], f"Enable monitor mode on {self.interface}"):
            self.check_monitor_mode()
            messagebox.showinfo("Success", f"Monitor mode enabled on {self.interface}.")

    def disable_monitor(self):
        if not messagebox.askyesno("Confirm", "Disable monitor mode and restore networking?"):
            return
        
        # Use the bundled stop script
        stop_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stop_monitor_mode.sh")
        if self.run_command(["sudo", "bash", stop_script], "Disable monitor mode"):
            self.check_monitor_mode()
            messagebox.showinfo("Success", "Monitor mode disabled. Network services restarted.")

    def launch_in_terminal(self, cmd, title):
        term = None
        for t in ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]:
            if shutil.which(t):
                term = t
                break
        
        if not term:
            messagebox.showerror("Error", "No terminal emulator found. Please install xterm or gnome-terminal.")
            return
        
        try:
            if term == "gnome-terminal" or term == "konsole":
                subprocess.Popen([term, "--", "sudo", cmd])
            else:
                subprocess.Popen([term, "-e", f"sudo {cmd}"])
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
    # Verify environment
    if "DISPLAY" not in os.environ:
        # Try to guess display if common
        if os.path.exists("/tmp/.X11-unix/X0"):
            os.environ["DISPLAY"] = ":0"
        else:
            print("Error: No graphical display detected. EZMonitorMode requires a desktop environment.")
            sys.exit(1)

    try:
        root = tk.Tk()
        interfaces = detect_interfaces()
        app = MonitorGUI(root, interfaces)
        root.mainloop()
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
