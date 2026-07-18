import ctypes
import logging
import platform
import webbrowser

from app_paths import resource_path
from autostart import is_enabled, set_enabled


LOGGER = logging.getLogger(__name__)
CONTROL_URL = "https://localhost:5888/"


def open_control_center():
    webbrowser.open(CONTROL_URL)


def copy_to_clipboard(text):
    if platform.system() != "Windows":
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    cf_unicode_text = 13
    gmem_moveable = 0x0002
    data = ctypes.create_unicode_buffer(text)
    size = ctypes.sizeof(data)
    handle = kernel32.GlobalAlloc(gmem_moveable, size)
    if not handle:
        return False

    locked = kernel32.GlobalLock(handle)
    if not locked:
        kernel32.GlobalFree(handle)
        return False

    ctypes.memmove(locked, ctypes.addressof(data), size)
    kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        return False

    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(cf_unicode_text, handle):
            kernel32.GlobalFree(handle)
            return False
        handle = None
        return True
    finally:
        user32.CloseClipboard()


def run_tray(addresses, on_exit):
    import pystray
    from PIL import Image

    image = Image.open(resource_path("static", "touchpad.png"))

    def open_page(icon, item):
        open_control_center()

    def toggle_autostart(icon, item):
        try:
            set_enabled(not is_enabled())
            icon.update_menu()
        except Exception:
            LOGGER.exception("切换开机自启动失败")
            icon.notify("无法修改开机自启动设置，请查看日志。", "AirMouse")

    def copy_address(address):
        def handler(icon, item):
            if copy_to_clipboard(address):
                icon.notify(f"已复制：{address}", "AirMouse")
            else:
                icon.notify("复制访问地址失败。", "AirMouse")

        return handler

    def exit_app(icon, item):
        on_exit()
        icon.stop()

    address_items = tuple(
        pystray.MenuItem(address, copy_address(address)) for address in addresses
    )
    menu = pystray.Menu(
        pystray.MenuItem("打开控制中心", open_page, default=True),
        pystray.MenuItem("复制访问地址", pystray.Menu(*address_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("开机自启动", toggle_autostart, checked=lambda item: is_enabled()),
        pystray.MenuItem("退出", exit_app),
    )
    icon = pystray.Icon("AirMouse", image, "AirMouse Remote", menu)
    icon.run()
