import ctypes
import json
from pathlib import Path
import unittest
from unittest import mock

import windows_text_input as backend


class WindowsEncodingTests(unittest.TestCase):
    def test_native_layout(self):
        wide = ctypes.sizeof(ctypes.c_void_p) == 8
        self.assertEqual(ctypes.sizeof(backend.INPUT), 40 if wide else 28)
        self.assertEqual(backend.INPUT.data.offset, 8 if wide else 4)
        self.assertEqual(ctypes.sizeof(backend.KEYBDINPUT), 24 if wide else 16)

    def test_unicode_roundtrip_and_event_order(self):
        url = json.loads((Path(__file__).parent / 'text_samples.json').read_text(encoding='utf-8'))['url']
        for text in (url, '  AaZz0123456789 !@#$%^&*()_+-=[]{};:\'",.<>/?\\|`~ 中文😀  '):
            events = backend.encode_text(text)
            units = bytearray()
            for down, up in zip(events[::2], events[1::2]):
                self.assertEqual((down.type, down.ki.wVk, down.ki.dwFlags), (1, 0, 4))
                self.assertEqual((up.type, up.ki.wVk, up.ki.dwFlags), (1, 0, 6))
                self.assertEqual(down.ki.wScan, up.ki.wScan)
                self.assertEqual(down.ki.dwExtraInfo, 0)
                units.extend(down.ki.wScan.to_bytes(2, 'little'))
            self.assertEqual(units.decode('utf-16-le'), text)

    def test_enter_tab_and_crlf(self):
        events = backend.encode_text('\r\n\n\r\t')
        self.assertEqual(len(events), 8)
        self.assertEqual([e.ki.wVk for e in events[::2]], [13, 13, 13, 9])
        self.assertEqual([e.ki.dwFlags for e in events], [0, 2] * 4)
        self.assertTrue(all(e.ki.wScan == 0 for e in events))

    def test_one_batch_and_incomplete_submission_never_retries(self):
        for sent in (0, 1, 4):
            api = mock.Mock()
            api.GetAsyncKeyState.return_value = 0
            api.SendInput.return_value = sent
            with mock.patch.object(backend, 'load_user32', return_value=api):
                if sent == 4:
                    backend.type_text('Aa')
                else:
                    with self.assertRaises(OSError):
                        backend.type_text('Aa')
            api.SendInput.assert_called_once()
            count, events, size = api.SendInput.call_args.args
            self.assertEqual((count, len(events), size), (4, 4, ctypes.sizeof(backend.INPUT)))

    def test_modifiers_block_but_toggle_bit_does_not(self):
        for key in backend.MODIFIER_KEYS:
            api = mock.Mock()
            api.GetAsyncKeyState.side_effect = lambda vk: 0x8000 if vk == key else 0
            with mock.patch.object(backend, 'load_user32', return_value=api):
                with self.assertRaises(backend.InputBusyError):
                    backend.type_text('a')
            api.SendInput.assert_not_called()
        api.GetAsyncKeyState.side_effect = None
        api.GetAsyncKeyState.return_value = 1
        api.SendInput.return_value = 2
        with mock.patch.object(backend, 'load_user32', return_value=api):
            backend.type_text('a')
        api.SendInput.assert_called_once()

    def test_invalid_surrogate_rejected_before_system_calls(self):
        with mock.patch.object(backend, 'load_user32') as load:
            with self.assertRaises(UnicodeEncodeError):
                backend.type_text('valid prefix' + chr(0xD800))
            backend.type_text('')
            load.assert_not_called()
