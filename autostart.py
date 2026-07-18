import platform
import subprocess
import sys

from app_paths import executable_path, resource_path


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AirMouse"


def build_autostart_command():
    if getattr(sys, "frozen", False):
        arguments = [str(executable_path()), "--autostart"]
    else:
        arguments = [str(executable_path()), str(resource_path("server.py")), "--autostart"]
    return subprocess.list2cmdline(arguments)


def _winreg():
    if platform.system() != "Windows":
        raise OSError("开机自启动仅支持 Windows")
    import winreg

    return winreg


def is_enabled():
    if platform.system() != "Windows":
        return False
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False


def set_enabled(enabled):
    winreg = _winreg()
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, build_autostart_command())
        return

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass
