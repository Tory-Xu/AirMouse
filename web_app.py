import base64
import io
import ipaddress
import socket
from urllib.parse import urlsplit

import psutil
import qrcode
from qrcode.image.pil import PilImage
from flask import Flask, make_response, render_template, request
from flask_socketio import SocketIO
from app_paths import resource_path

PORT = 5888

app = Flask(
    __name__,
    template_folder=str(resource_path('templates')),
    static_folder=str(resource_path('static')),
)
# 允许所有来源跨域，确保手机能连上
socketio = SocketIO(app, cors_allowed_origins="*")

def get_all_ip_addresses():
    """只展示已启用网卡上的可用 IPv4，保留网卡名称以便选择。"""
    ip_list = []
    try:
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
    except (OSError, psutil.Error):
        app.logger.warning('无法读取本机网卡地址')
        return ip_list

    for interface, addrs in interfaces.items():
        if interface not in stats or not stats[interface].isup:
            continue
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue
            try:
                ip = ipaddress.IPv4Address(addr.address)
            except ipaddress.AddressValueError:
                continue
            if (ip.is_loopback or ip.is_link_local or ip.is_unspecified
                    or ip.is_multicast or ip.is_reserved):
                continue
            entry = (interface, str(ip))
            if entry not in ip_list:
                ip_list.append(entry)
    return ip_list


def get_default_ip_address():
    """UDP connect 只查询本机路由，不发送数据，也不依赖外网响应。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('192.0.2.1', 9))
            return probe.getsockname()[0]
    except OSError:
        return None


def make_qr_data_uri(url):
    output = io.BytesIO()
    qrcode.make(url, image_factory=PilImage, box_size=8, border=4).save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode('ascii')


@app.route('/')
def index():
    addresses = get_all_ip_addresses()
    current_host = urlsplit(request.host_url).hostname
    preferred_ip = None
    if addresses:
        preferred_ip = current_host if any(ip == current_host for _, ip in addresses) else get_default_ip_address()
    connections = []
    selected_index = 0
    for interface, ip in addresses:
        url = f'https://{ip}:{PORT}/'
        if ip == preferred_ip:
            selected_index = len(connections)
        connections.append({'interface': interface, 'ip': ip, 'url': url, 'qr': make_qr_data_uri(url)})

    response = make_response(render_template(
        'dashboard.html', connections=connections, selected_index=selected_index,
    ))
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/touchpad')
def touchpad_page():
    return render_template('index.html')

@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html')

@app.route('/v')
def voice_page():
    return render_template('voice.html')

@app.route('/test')
def vibe_test():
    return render_template('vibe_test.html')

@app.route('/t')
def air_mouse_test():
    return render_template('t.html')

@app.route('/r')
def real_mouse_page():
    return render_template('realmouse.html')

@app.route('/b')
def buttons_page():
    return render_template('buttons.html')

@app.route('/controller')
def controller_page():
    return render_template('controller.html')
