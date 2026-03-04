@echo off
echo ==========================================
echo   HiveMind AI - Starting MOCK Mode
echo ==========================================

:: Start Backend (Optional but included for stability)
start "HiveMind-Backend" cmd /k "cd backend && ..\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Start Frontend in MOCK mode
echo [DEBUG] Starting Frontend with --mode mock...
start "HiveMind-Frontend" cmd /k "cd frontend && npm run dev -- --mode mock"

echo Done. Check the Frontend console for "Running in MOCK Mode" warning.
pause
