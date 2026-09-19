"""Windows 文本注入；结构使用固定宽度，便于在其他平台验证编码。"""
import ctypes


WORD = ctypes.c_uint16
DWORD = ctypes.c_uint32
ULONG_PTR = ctypes.c_size_t
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MODIFIER_KEYS = (0x10, 0x11, 0x12, 0x5B, 0x5C,
                 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5)


class InputBusyError(RuntimeError):
    """按键尚未释放，发送前拒绝请求。"""


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', WORD), ('wScan', WORD), ('dwFlags', DWORD),
                ('time', DWORD), ('dwExtraInfo', ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', ctypes.c_int32), ('dy', ctypes.c_int32),
                ('mouseData', DWORD), ('dwFlags', DWORD), ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', DWORD), ('wParamL', WORD), ('wParamH', WORD)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', DWORD), ('data', INPUTUNION)]


def encode_text(text):
    # 严格编码先验证整段文本，孤立代理项不会造成半段输入。
    encoded = text.replace('\r\n', '\n').encode('utf-16-le')
    events = []
    for offset in range(0, len(encoded), 2):
        unit = int.from_bytes(encoded[offset:offset + 2], 'little')
        vk = {9: 0x09, 10: 0x0D, 13: 0x0D}.get(unit, 0)
        scan = 0 if vk else unit
        flags = 0 if vk else KEYEVENTF_UNICODE
        for state in (flags, flags | KEYEVENTF_KEYUP):
            events.append(INPUT(type=1, ki=KEYBDINPUT(vk, scan, state, 0, 0)))
    return (INPUT * len(events))(*events)


def load_user32():
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.SendInput.argtypes = (ctypes.c_uint32, ctypes.POINTER(INPUT), ctypes.c_int)
    api.SendInput.restype = ctypes.c_uint32
    api.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    api.GetAsyncKeyState.restype = ctypes.c_int16
    return api


def type_text(text):
    events = encode_text(text)
    if not events:
        return
    api = load_user32()
    if any(api.GetAsyncKeyState(key) & 0x8000 for key in MODIFIER_KEYS):
        raise InputBusyError()
    # 只提交一次；部分提交后重试会重复输入，不能退回物理按键路径。
    sent = api.SendInput(len(events), events, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise OSError('Windows 未接受全部文本输入事件')
