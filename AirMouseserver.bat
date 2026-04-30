@echo off
echo 正在检查 Python 依赖...
pip install flask flask-socketio pyOpenSSL pynput psutil 
start https://localhost:5888
python server.py
pause