@echo off
rem Abre el Descargador. Si algo falla, el error queda visible en esta ventana.
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
".venv\Scripts\python.exe" -m downloader
if errorlevel 1 pause
