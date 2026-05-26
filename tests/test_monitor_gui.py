#!/usr/bin/env python3
"""Tests for the monitor_gui module."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ezmonitormode.monitor_gui import MonitorGUI


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
        with patch.object(MonitorGUI, 'check_monitor_mode'):
            self.gui = MonitorGUI(self.mock_root, ["wlan0", "wlan1"])

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

    def test_gui_creates_widgets(self):
        """Test that GUI creates expected widgets."""
        from ezmonitormode.monitor_gui import VERSION
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
        mock_run.assert_called_once_with(['echo', 'test'], capture_output=True)

    def test_set_switch_state_on(self):
        """Test UI updates when monitor mode is ON."""
        self.gui.set_switch_state(True)
        self.assertTrue(self.gui.is_monitor_on)
        self.assertTrue(self.gui.toggle_widget.is_on)
        self.gui.lbl_on.config.assert_called_with(fg="#39ff14")
        self.gui.lbl_off.config.assert_called_with(fg="#502020")

    def test_set_switch_state_off(self):
        """Test UI updates when monitor mode is OFF."""
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
        with patch.object(self.gui, 'disable_monitor') as mock_disable:
            self.gui.toggle_monitor()
            mock_disable.assert_called_once()


if __name__ == '__main__':
    unittest.main()
