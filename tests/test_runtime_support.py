import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

import app_paths
import autostart
import config_manager
from single_instance import SingleInstance


class AppPathsTests(unittest.TestCase):
    def test_windows_config_and_log_paths_use_user_directories(self):
        with tempfile.TemporaryDirectory() as roaming, tempfile.TemporaryDirectory() as local:
            with mock.patch.object(sys, 'platform', 'win32'), mock.patch.dict(
                os.environ,
                {'APPDATA': roaming, 'LOCALAPPDATA': local},
                clear=False,
            ):
                self.assertEqual(app_paths.config_dir(), Path(roaming) / 'AirMouse')
                self.assertEqual(app_paths.log_dir(), Path(local) / 'AirMouse' / 'logs')

    def test_default_config_is_copied_only_once(self):
        with tempfile.TemporaryDirectory() as resources, tempfile.TemporaryDirectory() as user_data:
            source = Path(resources) / 'example.json'
            source.write_text('{"value": 1}', encoding='utf-8')
            with mock.patch('app_paths.resource_root', return_value=Path(resources)), mock.patch(
                'app_paths.config_dir', return_value=Path(user_data)
            ):
                destination = app_paths.ensure_user_config('example.json')
                self.assertEqual(destination.read_text(encoding='utf-8'), '{"value": 1}')
                destination.write_text('{"value": 2}', encoding='utf-8')
                app_paths.ensure_user_config('example.json')
                self.assertEqual(destination.read_text(encoding='utf-8'), '{"value": 2}')


class ConfigManagerTests(unittest.TestCase):
    def test_save_macros_does_not_fail_on_non_unicode_console(self):
        class Cp1252Console:
            encoding = 'cp1252'

            def __init__(self):
                self.messages = []

            def write(self, message):
                message.encode(self.encoding)
                self.messages.append(message)

            def flush(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'macro_configs.json'
            console = Cp1252Console()
            with mock.patch('config_manager.ensure_user_config', return_value=path), mock.patch.object(
                config_manager.sys, 'stdout', console
            ):
                config_manager.save_macros({'name': '测试'})

            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'name': '测试'})
            self.assertFalse(Path(f'{path}.tmp').exists())
            self.assertTrue(any('?' in message for message in console.messages))

    def test_save_json_replaces_file_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'macro_configs.json'
            with mock.patch('config_manager.ensure_user_config', return_value=path):
                config_manager.save_macros({'name': '测试'})
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'name': '测试'})
                self.assertFalse(Path(f'{path}.tmp').exists())

    def test_invalid_gamepad_config_returns_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'gamepad_configs.json'
            path.write_text('{invalid', encoding='utf-8')
            with mock.patch('config_manager.ensure_user_config', return_value=path):
                config = config_manager.load_gp_macros()
                self.assertEqual(config['current'], 'Default')


class AutostartTests(unittest.TestCase):
    def test_frozen_command_contains_autostart_argument(self):
        with mock.patch.object(sys, 'frozen', True, create=True), mock.patch(
            'autostart.executable_path', return_value=Path(r'C:\Program Files\AirMouse\AirMouse.exe')
        ):
            command = autostart.build_autostart_command()
            self.assertIn('AirMouse.exe', command)
            self.assertTrue(command.endswith('--autostart'))


class SingleInstanceTests(unittest.TestCase):
    def test_second_instance_is_rejected_until_first_releases(self):
        name = f'AirMouse.Test.{uuid.uuid4()}'
        first = SingleInstance(name)
        second = SingleInstance(name)
        self.assertTrue(first.acquire())
        try:
            self.assertFalse(second.acquire())
        finally:
            first.release()
        self.assertTrue(second.acquire())
        second.release()


if __name__ == '__main__':
    unittest.main()
