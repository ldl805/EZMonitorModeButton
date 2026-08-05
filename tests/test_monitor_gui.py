#!/usr/bin/env python3
"""Tests for the monitor_gui module."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ezmonitormode.monitor_gui import MonitorGUI, get_interface_details, VERSION


class TestMonitorGUI(unittest.TestCase):
    """Test cases for the MonitorGUI class."""

    def setUp(self):
        """Set up test fixtures."""
        # Patch all of tkinter to avoid issues in headless environments
        self.tk_patcher = patch('ezmonitormode.monitor_gui.tk')
        self.mock_tk = self.tk_patcher.start()
        # Ensure separate calls to tk.Label return distinct mocks
        self.mock_tk.Label.side_effect = lambda *args, **kwargs: MagicMock()
        
        self.ttk_patcher = patch('ezmonitormode.monitor_gui.ttk')
        self.mock_ttk = self.ttk_patcher.start()
        
        self.msgbox_patcher = patch('ezmonitormode.monitor_gui.messagebox')
        self.mock_msgbox = self.msgbox_patcher.start()
        
        self.mock_root = MagicMock()
        # Mock winfo_screenwidth/height for center_window
        self.mock_root.winfo_screenwidth.return_value = 1920
        self.mock_root.winfo_screenheight.return_value = 1080
        
        # Patch check_monitor_mode to avoid subprocess call in __init__
        with patch.object(MonitorGUI, 'check_monitor_mode'), \
             patch.object(MonitorGUI, 'update_interface_details_ui'):
            self.gui = MonitorGUI(self.mock_root, ["wlan0", "wlan1"])
            self.gui.airmon_ng_available = True

    def tearDown(self):
        """Clean up test fixtures."""
        self.tk_patcher.stop()
        self.ttk_patcher.stop()
        self.msgbox_patcher.stop()

    def test_gui_initialization(self):
        """Test that MonitorGUI initializes correctly."""
        self.assertIsNotNone(self.gui)
        self.assertEqual(self.gui.master, self.mock_root)
        self.assertEqual(self.gui.interface, "wlan0") # First interface
        self.assertFalse(self.gui.is_monitor_on)

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    @patch('ezmonitormode.monitor_gui.get_interface_details')
    def test_gui_initialization_full_unpatched(self, mock_details, mock_status):
        """Test that MonitorGUI initializes without error when unpatched."""
        mock_status.return_value = {"wlan0": "managed"}
        mock_details.return_value = {"channel": "1", "freq": "2412 MHz", "mac": "00:11:22:33:44:55", "txpower": "20 dBm", "mode": "managed"}
        app = MonitorGUI(self.mock_root, ["wlan0"])
        self.assertIsNotNone(app)
        self.assertTrue(hasattr(app, 'airmon_ng_available'))

    def test_gui_creates_widgets(self):
        """Test that GUI creates expected widgets."""
        self.mock_root.title.assert_called_with(f"EZ Monitor Mode {VERSION}")
        # Check that geometry was set via center_window
        self.mock_root.geometry.assert_called()

    def test_get_terminal_not_needed(self):
        """Test launch_in_terminal handles missing terminal."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None
            self.gui.launch_in_terminal("cmd", "Title")
            self.mock_msgbox.showerror.assert_called()

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test run_command_in_thread with successful execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        self.gui.run_command_in_thread(['echo', 'test'], 'Test Command')
        mock_run.assert_called_once_with(['echo', 'test'], capture_output=True, timeout=30)

    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run):
        """Test run_command_in_thread handles subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['echo', 'test'], timeout=30)
        
        with self.assertRaises(RuntimeError) as ctx:
            self.gui.run_command_in_thread(['echo', 'test'], 'Test Command')
        
        self.assertIn("timed out after 30 seconds", str(ctx.exception))

    def test_set_switch_state_on(self):
        """Test UI updates when monitor mode is ON."""
        with patch.object(self.gui, 'update_interface_details_ui'):
            self.gui.set_switch_state(True)
            self.assertTrue(self.gui.is_monitor_on)
            self.assertTrue(self.gui.toggle_widget.is_on)
            self.gui.lbl_on.config.assert_called_with(fg="#39ff14")
            self.gui.lbl_off.config.assert_called_with(fg="#502020")

    def test_set_switch_state_off(self):
        """Test UI updates when monitor mode is OFF."""
        with patch.object(self.gui, 'update_interface_details_ui'):
            self.gui.set_switch_state(False)
            self.assertFalse(self.gui.is_monitor_on)
            self.assertFalse(self.gui.toggle_widget.is_on)
            self.gui.lbl_off.config.assert_called_with(fg="#ff1744")
            self.gui.lbl_on.config.assert_called_with(fg="#204020")

    def test_toggle_monitor_calls_enable(self):
        """Test toggle calls enable when off."""
        self.gui.is_monitor_on = False
        with patch.object(self.gui, 'enable_monitor') as mock_enable:
            self.gui.toggle_monitor()
            mock_enable.assert_called_once()

    def test_toggle_monitor_calls_disable(self):
        """Test toggle calls disable when on."""
        self.gui.is_monitor_on = True
        self.gui.airmon_ng_available = True
        with patch.object(self.gui, 'disable_monitor') as mock_disable:
            self.gui.toggle_monitor()
            mock_disable.assert_called_once()

    def test_toggle_monitor_no_airmon_ng(self):
        """Test toggle monitor fails gracefully when airmon-ng is not installed."""
        self.gui.airmon_ng_available = False
        with patch.object(self.gui, 'enable_monitor') as mock_enable, \
             patch.object(self.gui, 'disable_monitor') as mock_disable:
            self.gui.toggle_monitor()
            mock_enable.assert_not_called()
            mock_disable.assert_not_called()
            self.mock_msgbox.showerror.assert_called_once_with(
                "Dependency Error",
                "airmon-ng is not installed.\n\nPlease install aircrack-ng:\nsudo apt install aircrack-ng"
            )

    def test_check_monitor_mode_no_airmon_ng(self):
        """Test check_monitor_mode sets status warning when airmon-ng is missing."""
        self.gui.airmon_ng_available = False
        with patch.object(self.gui, 'update_interface_details_ui'):
            self.gui.check_monitor_mode()
            self.gui.status_var.set.assert_called_with("Error: airmon-ng not found. Please install aircrack-ng.")
            self.assertFalse(self.gui.is_monitor_on)

    def test_toggle_tools_section(self):
        """Test toggling the tools section visibility and geometry."""
        self.assertTrue(self.gui.tools_visible)
        
        # Collapse tools
        self.gui.toggle_tools_section()
        self.assertFalse(self.gui.tools_visible)
        self.gui.tools_container.pack_forget.assert_called_once()
        self.gui.btn_toggle_tools.config.assert_called_with(text="Show Quick Tools ▼")
        self.mock_root.geometry.assert_called_with("420x370")
        
        # Expand tools
        self.gui.toggle_tools_section()
        self.assertTrue(self.gui.tools_visible)
        self.gui.tools_container.pack.assert_called_with(fill="x", pady=5)
        self.gui.btn_toggle_tools.config.assert_called_with(text="Hide Quick Tools ▲")
        self.mock_root.geometry.assert_called_with("420x580")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    def test_get_active_monitor_interface_direct(self, mock_status):
        """Test get_active_monitor_interface when the base interface itself is in monitor mode."""
        self.gui.interface = "wlan0"
        mock_status.return_value = {"wlan0": "monitor"}
        self.assertEqual(self.gui.get_active_monitor_interface(), "wlan0")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    def test_get_active_monitor_interface_suffix(self, mock_status):
        """Test get_active_monitor_interface when suffix interface (e.g. wlan0mon) is in monitor mode."""
        self.gui.interface = "wlan0"
        mock_status.return_value = {"wlan0": "managed", "wlan0mon": "monitor"}
        self.assertEqual(self.gui.get_active_monitor_interface(), "wlan0mon")

    @patch('ezmonitormode.monitor_gui.get_interfaces_status')
    def test_get_active_monitor_interface_none(self, mock_status):
        """Test get_active_monitor_interface when no interface is in monitor mode."""
        self.gui.interface = "wlan0"
        mock_status.return_value = {"wlan0": "managed", "wlan1": "managed"}
        self.assertIsNone(self.gui.get_active_monitor_interface())

    @patch('subprocess.check_output')
    def test_get_interface_details_iw(self, mock_check_output):
        """Test parsing iw dev info output for interface details."""
        mock_check_output.return_value = b"""Interface wlan0
\taddr 11:22:33:44:55:66
\ttype monitor
\tchannel 6 (2437 MHz), width: 20 MHz
\ttxpower 20.00 dBm
"""
        details = get_interface_details("wlan0")
        self.assertEqual(details["mac"], "11:22:33:44:55:66")
        self.assertEqual(details["mode"], "monitor")
        self.assertEqual(details["channel"], "6")
        self.assertEqual(details["freq"], "2437 MHz")
        self.assertEqual(details["txpower"], "20.00 dBm")

    def test_channel_hopping_toggle_requires_monitor_mode(self):
        """Test enabling channel hopping when monitor mode is OFF shows warning."""
        self.gui.is_monitor_on = False
        self.gui.hop_var.get.return_value = True
        self.gui.toggle_channel_hopping()
        self.mock_msgbox.showwarning.assert_called_with(
            "Monitor Mode Required",
            "Channel hopping requires monitor mode to be active."
        )


if __name__ == '__main__':
    unittest.main()
