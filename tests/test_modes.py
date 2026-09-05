import importlib.machinery
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import amc_windows

loader = importlib.machinery.SourceFileLoader('masker_gui', str(pathlib.Path(__file__).resolve().parents[1] / 'amc_windows_gui.pyw'))
spec = importlib.util.spec_from_loader(loader.name, loader)
gui = importlib.util.module_from_spec(spec)
loader.exec_module(gui)


class ModesTest(unittest.TestCase):
    def test_manual_startup_does_not_touch_network(self):
        with patch.object(gui.masker_secure_state, 'load_state', return_value={'startup_enabled': False}), patch.object(amc_windows, 'get_adapters') as adapters:
            self.assertEqual(gui.startup_randomize(), 0)
            adapters.assert_not_called()

    def test_automatic_uses_saved_adapter(self):
        state = {'startup_enabled': True, 'adapter': 'Ethernet'}
        with patch.object(gui.masker_secure_state, 'load_state', return_value=state), patch.object(gui.masker_secure_state, 'save_state') as save, patch.object(amc_windows, 'get_adapters', return_value=[{'Name': 'Ethernet'}]), patch.object(amc_windows, 'set_mac') as change:
            self.assertEqual(gui.startup_randomize(), 0)
            self.assertEqual(change.call_args.args[0], 'Ethernet')
            self.assertEqual(save.call_args.args[0]['last_result'], 'success')

    def test_disable_during_startup_retry(self):
        with patch.object(gui.masker_secure_state, 'load_state', side_effect=[{'startup_enabled': True}, {'startup_enabled': False}]), patch.object(amc_windows, 'get_adapters') as adapters:
            self.assertEqual(gui.startup_randomize(), 0)
            adapters.assert_not_called()

    def test_driver_rejection_is_not_success(self):
        with patch.object(amc_windows, 'run_powershell', return_value='00-11-22-33-44-55'):
            with self.assertRaises(RuntimeError):
                amc_windows.set_mac('Ethernet', '02AABBCCDDEE')

    def test_driver_acceptance(self):
        with patch.object(amc_windows, 'run_powershell', return_value='02-AA-BB-CC-DD-EE'):
            amc_windows.set_mac('Ethernet', '02AABBCCDDEE')

    def test_manual_persists_guard_before_task_removal(self):
        events = []
        with patch.object(gui.masker_secure_state, 'load_state', return_value={'startup_enabled': True}), patch.object(gui.masker_secure_state, 'save_state', side_effect=lambda state: events.append(('save', state.copy()))), patch.object(gui.subprocess, 'run', side_effect=lambda *a, **k: events.append(('remove', a)) or subprocess.CompletedProcess([], 0)):
            gui.remove_startup_task()
        self.assertEqual(events[0], ('save', {'startup_enabled': False}))
        self.assertEqual(events[1][0], 'remove')

    def test_task_removal_error_is_reported(self):
        with patch.object(gui.masker_secure_state, 'load_state', return_value={}), patch.object(gui.masker_secure_state, 'save_state') as save, patch.object(gui.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'denied')):
            with self.assertRaisesRegex(RuntimeError, 'denied'):
                gui.remove_startup_task()
            self.assertFalse(save.call_args.args[0]['startup_enabled'])

    def test_install_uses_protected_copy_and_selected_adapter(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(gui.os.environ, {'ProgramFiles': folder}), patch.object(sys, 'frozen', True, create=True), patch.object(gui.shutil, 'copy2') as copy, patch.object(gui.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run, patch.object(gui.masker_secure_state, 'load_state', return_value={}), patch.object(gui.masker_secure_state, 'save_state') as save:
            gui.install_startup_task('Ethernet 2')
            self.assertEqual(save.call_args.args[0]['adapter'], 'Ethernet 2')
            self.assertTrue(save.call_args.args[0]['startup_enabled'])
            self.assertEqual(copy.call_args.args[1], str(pathlib.Path(folder) / 'Masker' / 'Masker.exe'))
            task_args = run.call_args_list[1].args[0]
            self.assertIn('ONSTART', task_args)
            self.assertIn('SYSTEM', task_args)
            self.assertIn('--startup-randomize', task_args[task_args.index('/TR') + 1])

    def test_random_addresses_are_local_unicast(self):
        for _ in range(100):
            address = amc_windows.random_mac()
            self.assertEqual(amc_windows.normalize_mac(address), address)
            self.assertEqual(int(address[:2], 16) & 3, 2)


if __name__ == '__main__':
    unittest.main()
