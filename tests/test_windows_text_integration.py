"""显式启用的交互桌面测试，向专用 Win32 EDIT 控件输入并读取结果。"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import time
import unittest

import windows_text_input


@unittest.skipUnless(sys.platform == 'win32' and os.environ.get('AIRMOUSE_WINDOWS_INPUT_TEST') == '1',
                     '需要 Windows 交互桌面及 AIRMOUSE_WINDOWS_INPUT_TEST=1')
class WindowsDesktopTests(unittest.TestCase):
    def test_real_edit_control(self):
        api = windows_text_input.load_user32()
        signatures = {
            'CreateWindowExW': ([wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                wintypes.HINSTANCE, ctypes.c_void_p], wintypes.HWND),
            'SetForegroundWindow': ([wintypes.HWND], wintypes.BOOL),
            'GetForegroundWindow': ([], wintypes.HWND),
            'SetFocus': ([wintypes.HWND], wintypes.HWND),
            'GetFocus': ([], wintypes.HWND),
            'SetWindowTextW': ([wintypes.HWND, wintypes.LPCWSTR], wintypes.BOOL),
            'GetWindowTextW': ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            'DestroyWindow': ([wintypes.HWND], wintypes.BOOL),
            'PeekMessageW': ([ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                              wintypes.UINT, wintypes.UINT, wintypes.UINT], wintypes.BOOL),
            'TranslateMessage': ([ctypes.POINTER(wintypes.MSG)], wintypes.BOOL),
            'DispatchMessageW': ([ctypes.POINTER(wintypes.MSG)], ctypes.c_ssize_t),
        }
        for name, (args, result) in signatures.items():
            getattr(api, name).argtypes = args
            getattr(api, name).restype = result

        def pump():
            message = wintypes.MSG()
            while api.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                api.TranslateMessage(ctypes.byref(message))
                api.DispatchMessageW(ctypes.byref(message))

        # WS_POPUP | WS_VISIBLE | WS_BORDER，ES_MULTILINE | ES_WANTRETURN。
        window = api.CreateWindowExW(0, 'EDIT', '', 0x90801004,
                                     100, 100, 900, 400, None, None, None, None)
        self.assertTrue(window, '无法创建测试输入框')
        try:
            api.SetForegroundWindow(window)
            api.SetFocus(window)
            pump()
            url = json.loads((Path(__file__).parent / 'text_samples.json').read_text(encoding='utf-8'))['url']
            for text in [url] * 20 + ['  Aa09 中文😀\t尾行\r\n第二行\n第三行  ']:
                self.assertEqual(api.GetForegroundWindow(), window, '测试窗口必须处于前台')
                self.assertEqual(api.GetFocus(), window)
                self.assertTrue(api.SetWindowTextW(window, ''))
                windows_text_input.type_text(text)
                expected = text.replace('\r\n', '\n').replace('\n', '\r\n')
                deadline = time.monotonic() + 3
                result = ctypes.create_unicode_buffer(len(expected) * 2 + 32)
                while time.monotonic() < deadline:
                    pump()
                    api.GetWindowTextW(window, result, len(result))
                    if result.value == expected:
                        break
                    time.sleep(0.01)
                self.assertEqual(result.value, expected)
        finally:
            api.DestroyWindow(window)
