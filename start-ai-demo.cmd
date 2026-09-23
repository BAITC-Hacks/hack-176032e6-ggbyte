@echo off
cd /d "%~dp0"
python run.py --demo-ai --open-browser
if errorlevel 1 pause
