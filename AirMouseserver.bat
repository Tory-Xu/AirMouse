@echo off
echo checking python dependencies...
cd /d "%~dp0"
py -3.11 -m pip install -r requirements.txt
py -3.11 server.py
pause
