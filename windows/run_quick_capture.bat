@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw "%~dp0quick_capture.py") || (start "" pythonw "%~dp0quick_capture.py")
