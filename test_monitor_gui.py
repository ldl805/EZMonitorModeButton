#!/usr/bin/env python3
"""Tests for the monitor_gui module."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

# Add src to path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ezmonitormode.monitor_gui import MonitorGUI


class TestMonitorGUI(unittest.TestCase):
    """Test cases for the MonitorGUI class."""

    def setUp(self):
        """Set up test fixtures."""
        # Patch all of tkinter to avoid issues in headless environments
        self.tk_patcher = patch('ezmonitormode.monitor_gui.tk')
        self.mock_tk = self.tk_patcher.start()
        
        self.msgbox_patcher = patch('ezmonitormode.monitor_gui.messagebox')
        self.mock_msgbox = self.msgbox_patcher.start()
        
        self.mock_root = MagicMock()
        
        # Patch check_monitor_mode to avoid subprocess call in __init__
        with patch.object(MonitorGUI, 'check_monitor_mode'):
            self.gui = MonitorGUI(self.mock_root, ["wlan0", "wlan1"])

    def tearDown(self):
        """Clean up test fixtures."""
        self.tk_patcher.stop()
        self.msgbox_patcher.stop()

    def test_gui_initialization(self):
        """Test that MonitorGUI initializes correctly."""
        self.assertIsNotNone(self.gui)
        self.assertEqual(self.gui.master, self.mock_root)
        self.assertEqual(self.gui.interface, "wlan0") # First interface
        self.assertFalse(self.gui.is_monitor_on)

    def test_gui_creates_widgets(self):
        """Test that GUI creates expected widgets."""
        self.mock_root.title.assert_called_with("EZ Monitor Mode 1.1.0")
        # Check that geometry was set (now 400x500)
        self.mock_root.geometry.assert_called_with("400x500")

    def test_get_terminal_with_valid_terminal(self):
        """Test get_terminal returns a terminal when available."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/x-terminal-emulator'
            terminal = self.gui.get_terminal()
            self.assertEqual(terminal, '/usr/bin/x-terminal-emulator')

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test run_command with successful execution."""
        result = self.gui.run_command(['echo', 'test'], 'Test Command')
        self.assertTrue(result)
        mock_run.assert_called_once_with(['echo', 'test'], check=True)

    def test_set_switch_state_on(self):
        """Test UI updates when monitor mode is ON."""
        self.gui.set_switch_state(True)
        self.assertTrue(self.gui.is_monitor_on)
        self.gui.btn_switch.config.assert_called()
        # Verify text was updated to ON
        last_call_args = self.gui.btn_switch.config.call_args[1]
        self.assertIn("ON", last_call_args['text'])
        self.assertEqual(last_call_args['bg'], "#44ff44")

    def test_set_switch_state_off(self):
        """Test UI updates when monitor mode is OFF."""
        self.gui.set_switch_state(False)
        self.assertFalse(self.gui.is_monitor_on)
        self.gui.btn_switch.config.assert_called()
        # Verify text was updated to OFF
        last_call_args = self.gui.btn_switch.config.call_args[1]
        self.assertIn("OFF", last_call_args['text'])
        self.assertEqual(last_call_args['bg'], "#ff4444")

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
