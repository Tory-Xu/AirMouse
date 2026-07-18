import json
import platform
from pathlib import Path
from pynput.keyboard import Key
from app_paths import ensure_user_config

# 宏按键配置存储逻辑
CONFIG_FILE = "macro_configs.json"


def _load_json(filename, default=None):
    path = ensure_user_config(filename)
    if not path.exists():
        return default
    try:
        with path.open('r', encoding='utf-8') as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(filename, data):
    path = ensure_user_config(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{path}.tmp")
    with temporary.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    temporary.replace(path)

def load_macros():
    return _load_json(CONFIG_FILE)

def save_macros(data):
    _save_json(CONFIG_FILE, data)
    print("宏按键配置已保存到服务端")

GP_CONFIG_FILE = "gamepad_configs.json"

def load_gp_macros():
    default_cfg = {
        "current": "Default",
        "profiles": { "Default": {} }
    }
    return _load_json(GP_CONFIG_FILE, default_cfg)

def save_gp_macros(data):
    _save_json(GP_CONFIG_FILE, data)

# 特殊按键映射表
def get_special_keys():
    os_type = platform.system()
    # keys = {
    #     'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    #     'shift': Key.shift, 'shift_r': Key.shift_r,
    #     'alt': Key.alt, 'alt_r': Key.alt_r,
    #     'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
    #     'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    #     'space': Key.space, 'delete': Key.delete,
    #     'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    #     'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    #     'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
    #     # 符号别名
    #     'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';', 'quote': "'", 'bracket_l': '[', 'bracket_r': ']'
    # }

    keys = {
        # 修饰键 (Modifiers)
        'ctrl': Key.ctrl, 'ctrl_l': Key.ctrl_l, 'ctrl_r': Key.ctrl_r,
        'shift': Key.shift, 'shift_l': Key.shift_l, 'shift_r': Key.shift_r,
        'alt': Key.alt, 'alt_l': Key.alt_l, 'alt_r': Key.alt_r,
        'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd, 'cmd': Key.cmd,

        # 导航键 (Navigation) - 你的错误就在这里补全
        'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
        'page_up': Key.page_up, 'page_down': Key.page_down, 
        'home': Key.home, 'end': Key.end,
        'insert': Key.insert, 'delete': Key.delete,

        # 常用功能键 (Standard Keys)
        'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 
        'backspace': Key.backspace, 'space': Key.space,
        'caps_lock': Key.caps_lock, 'num_lock': Key.num_lock,
        'scroll_lock': Key.scroll_lock, 'print_screen': Key.print_screen,
        'pause': Key.pause,

        # F1-F20 (Function Keys)
        **{f'f{i}': getattr(Key, f'f{i}') for i in range(1, 21)},

        # 符号别名 (Symbols & Punctuation)
        'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';', 
        'quote': "'", 'bracket_l': '[', 'bracket_r': ']',
        'backslash': '\\', 'backtick': '`', 'minus': '-', 'equal': '=',
        
        # 额外补充可能用到的媒体键 (Media Keys)
        'media_play_pause': Key.media_play_pause,
        'media_volume_mute': Key.media_volume_mute,
        'media_volume_up': Key.media_volume_up,
        'media_volume_down': Key.media_volume_down,
        'media_next': Key.media_next,
        'media_previous': Key.media_previous
    }
    # Windows 特有
    if os_type == 'Windows':
        keys['prtsc'] = Key.print_screen
        
    return keys
