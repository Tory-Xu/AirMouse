import time
import threading
import platform
from functools import wraps
import windows_text_input
from pynput.keyboard import Controller as KeyController, Key, KeyCode
from config_manager import get_special_keys

keyboard = KeyController()
active_repeats = {} # {key_code: stop_event}
input_lock = threading.RLock()
repeat_lock = input_lock


def serialized_input(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with input_lock:
            return function(*args, **kwargs)
    return wrapped

def repeat_key(key_obj, stop_event):
    """模拟系统自动重复按键的线程"""
    # 释放操作与重复线程共享锁，避免切换模式后迟到的线程再次按下按键。
    with repeat_lock:
        if stop_event.is_set(): return
        keyboard.press(key_obj)
    if stop_event.wait(0.4): return
    
    while not stop_event.is_set():
        with repeat_lock:
            if stop_event.is_set(): return
            keyboard.press(key_obj)
        if stop_event.wait(0.05): break

def handle_key_action(data):
    action = data['action'] # 'down' 或 'up'
    key_code = data['key'].lower().strip()
    special_keys = get_special_keys()
    
    target_key = special_keys.get(key_code, key_code)

    with repeat_lock:
        if action == 'down':
            if key_code in active_repeats:
                return
            stop_event = threading.Event()
            active_repeats[key_code] = stop_event
            threading.Thread(target=repeat_key, args=(target_key, stop_event), daemon=True).start()
        else:
            if key_code in active_repeats:
                stop_event = active_repeats[key_code]
                stop_event.set()
                del active_repeats[key_code]
            keyboard.release(target_key)

@serialized_input
def handle_type_text(data):
    if platform.system() == 'Windows':
        if active_repeats:
            raise windows_text_input.InputBusyError()
        windows_text_input.type_text(data['text'])
    else:
        keyboard.type(data['text'])

@serialized_input
def handle_clear_text():
    """在当前焦点全选并删除；组合键完全释放后才执行退格。"""
    modifier = Key.cmd if platform.system() == 'Darwin' else Key.ctrl
    pressed = []
    try:
        for target in (modifier, 'a'):
            # press 抛错时也可能已产生按键事件，因此提前登记以便释放。
            pressed.append(target)
            keyboard.press(target)
            time.sleep(0.05)
        for target in reversed(pressed[:]):
            keyboard.release(target)
            pressed.remove(target)
        time.sleep(0.05)
        pressed.append(Key.backspace)
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)
        pressed.remove(Key.backspace)
    finally:
        release_error = None
        for target in reversed(pressed):
            try:
                keyboard.release(target)
            except Exception as error:
                # 一个键释放失败也必须继续释放剩余按键。
                release_error = error
        if release_error is not None:
            raise release_error

@serialized_input
def handle_combo(data):
    keys = data['keys']
    if not keys: return
    
    special_keys = get_special_keys()
    is_mac = platform.system() == 'Darwin'
    
    pressed_keys = []
    try:
        # 按顺序按下所有键
        for k in keys:
            k_clean = k.lower().strip()
            target = special_keys.get(k_clean, k_clean)
            
            # macOS 修复：对于符号键，直接使用硬件虚拟键码同步位移标志
            # 这样 shift + 47 (dot) 就能被系统和浏览器（如 YouTube）正确识别为 >
            if is_mac and isinstance(target, str) and len(target) == 1:
                # 常见符号的 Mac 虚拟键码 (ANSI 布局)
                vk_map = {
                    '.': 47, ',': 43, '/': 44, ';': 41, "'": 39, 
                    '[': 33, ']': 30, '`': 50, '-': 27, '=': 24, '\\': 42
                }
                if target in vk_map:
                    target = KeyCode.from_vk(vk_map[target])
                else:
                    target = KeyCode.from_char(target)
            
            keyboard.press(target)
            pressed_keys.append(target)
            
            # macOS 下在按下 Shift 等修饰键后增加延迟，确保后续按键能识别到修饰状态
            if is_mac and target in (Key.shift, Key.shift_r, Key.ctrl, Key.ctrl_r, Key.alt, Key.alt_r, Key.cmd):
                time.sleep(0.1)
            else:
                # 维持组合键状态的时间
                delay = 0.05 if is_mac else 0.02
                time.sleep(delay)
        
        # 维持组合键状态的时间
        hold_time = 0.1 if is_mac else 0.05
        time.sleep(hold_time)
        
    finally:
        # 逆序释放所有键
        for target in reversed(pressed_keys):
            keyboard.release(target)
            if is_mac:
                time.sleep(0.01)
