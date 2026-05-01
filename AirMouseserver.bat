@echo off
echo checking python dependencies...
pip install flask flask-socketio pyOpenSSL pynput psutil 
cd /d "%~dp0"
start https://localhost:5888
python server.py
pause