@echo off
title Spend Smart - Database Migration Manager
cd /d "%~dp0"
echo ============================================================
echo   Spend Smart - Database Migration & Backup Manager
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe' database_migration_manager.py"

echo.
pause
