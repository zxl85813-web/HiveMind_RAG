@echo off
set PYTHONPATH=%~dp0backend
python %~dp0backend/app/main_cli.py %*
