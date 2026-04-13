@echo off
setlocal
echo ==========================================
echo   HiveMind AI - One-Click Launcher
echo ==========================================

:: Check if .venv exists
if not exist ".venv" (
    echo [ERROR] Virtual environment .venv not found!
    echo Please run 'python -m venv .venv' first.
    pause
    exit /b
)

:: Killing existing processes
echo [INFO] Cleaning up existing Python processes...
taskkill /F /IM python.exe /T >nul 2>&1

:: Start Backend
echo [INFO] Starting Backend (Port 8000)...
start "HiveMind-Backend" cmd /k "cd backend && ..\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Start Frontend
echo [INFO] Starting Frontend (Port 5173)...
start "HiveMind-Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ==========================================
echo   Services are starting in new windows.
echo   - Backend: http://localhost:8000
echo   - Frontend: http://localhost:5173
echo ==========================================
pause
