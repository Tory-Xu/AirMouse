import argparse
import logging
import platform
import socket
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler

from app_paths import log_dir, resource_path


if platform.system() == 'Darwin':
    try:
        from AppKit import NSBundle, NSApplication, NSApplicationActivationPolicyProhibited

        bundle = NSBundle.mainBundle()
        if bundle:
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info:
                info['LSUIElement'] = '1'
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    except Exception:
        pass

from web_app import app, socketio, get_all_ip_addresses
import config_manager
import gamepad_service
import keyboard_service
import mouse_service
from single_instance import SingleInstance


PORT = 5888
CONTROL_URL = f"https://localhost:{PORT}/"
LOGGER = logging.getLogger(__name__)


def configure_logging():
    directory = log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / 'AirMouse.log',
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8',
    )
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if not getattr(sys, 'frozen', False):
        root.addHandler(logging.StreamHandler())


def status_thread(stop_event):
    while not stop_event.wait(1):
        socketio.emit('gp_status', {
            'connected': gamepad_service.gamepad_connected,
            'name': gamepad_service.gamepad_name,
        })


def access_urls():
    urls = [CONTROL_URL]
    urls.extend(f"https://{ip}:{PORT}/" for _, ip in get_all_ip_addresses())
    return list(dict.fromkeys(urls))


def print_access_urls():
    print("\n" + "═" * 60)
    print("🚀 AirMouse Remote 已启动！")
    print(f"🏠 当前系统: {platform.system()}")
    print("📱 请在浏览器访问以下地址:")
    for url in access_urls():
        print(f"  ➤  {url}")
    print("═" * 60 + "\n")


def wait_until_ready(timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', PORT), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def run_socket_server():
    socketio.run(
        app,
        host='0.0.0.0',
        port=PORT,
        ssl_context=(str(resource_path('cert.pem')), str(resource_path('key.pem'))),
        allow_unsafe_werkzeug=True,
        use_reloader=False,
    )


def run_windows(autostart):
    instance = SingleInstance()
    if not instance.acquire():
        if not autostart:
            webbrowser.open(CONTROL_URL)
        return 0

    stop_event = threading.Event()
    try:
        gamepad_service.start_threads()
        threading.Thread(target=status_thread, args=(stop_event,), daemon=True).start()
        threading.Thread(target=run_socket_server, daemon=True).start()
        if not wait_until_ready():
            LOGGER.error("AirMouse 服务启动失败，端口 %s 可能已被占用", PORT)
            return 1

        if not autostart:
            threading.Thread(target=webbrowser.open, args=(CONTROL_URL,), daemon=True).start()

        from tray_app import run_tray

        run_tray(access_urls(), stop_event.set)
        return 0
    except Exception:
        LOGGER.exception("AirMouse 运行失败")
        return 1
    finally:
        stop_event.set()
        instance.release()


def run_console():
    stop_event = threading.Event()
    gamepad_service.start_threads()
    threading.Thread(target=status_thread, args=(stop_event,), daemon=True).start()
    print_access_urls()
    try:
        run_socket_server()
    finally:
        stop_event.set()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='AirMouse Remote Server')
    parser.add_argument(
        '--autostart',
        action='store_true',
        help='作为 Windows 登录自启动任务在后台运行，不自动打开浏览器',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    configure_logging()
    if platform.system() == 'Windows':
        return run_windows(args.autostart)
    run_console()
    return 0


# --- SocketIO 事件绑定 ---

@socketio.on('connect')
def handle_connect():
    socketio.emit('os_info', {'os': platform.system()})


@socketio.on('load_macros')
def handle_load():
    socketio.emit('macros_loaded', config_manager.load_macros())


@socketio.on('save_macros')
def handle_save(data):
    config_manager.save_macros(data)


@socketio.on('load_gp_macros')
def handle_gp_load():
    socketio.emit('gp_macros_loaded', config_manager.load_gp_macros())


@socketio.on('save_gp_macros')
def handle_gp_save(data):
    config_manager.save_gp_macros(data)
    gamepad_service.update_config(data)


@socketio.on('get_gamepads')
def handle_get_gps():
    socketio.emit('gamepads_list', gamepad_service.get_gamepad_list())


@socketio.on('select_gamepad')
def handle_select_gp(index):
    gamepad_service.selected_index = index
    handle_get_gps()


@socketio.on('move')
def on_move(data):
    mouse_service.handle_move(data)


@socketio.on('click')
def on_click(data):
    mouse_service.handle_click(data)


@socketio.on('drag_start')
def on_drag_start():
    mouse_service.handle_drag_start()


@socketio.on('drag_end')
def on_drag_end():
    mouse_service.handle_drag_end()


@socketio.on('mid_down')
def on_mid_down():
    mouse_service.handle_mid_down()


@socketio.on('mid_up')
def on_mid_up():
    mouse_service.handle_mid_up()


@socketio.on('scroll')
def on_scroll(data):
    mouse_service.handle_scroll(data)


@socketio.on('type_text')
def on_type(data):
    keyboard_service.handle_type_text(data)


@socketio.on('key_action')
def on_key(data):
    keyboard_service.handle_key_action(data)


@socketio.on('key_combo')
def on_combo(data):
    keyboard_service.handle_combo(data)


if __name__ == '__main__':
    raise SystemExit(main())
