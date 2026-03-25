@echo off
echo ==========================================
echo   HiveMind AI - Starting REAL Backend
echo ==========================================

:: Start Backend in a new window
echo [DEBUG] Starting Backend on port 8000...
start "HiveMind-Backend" cmd /k "cd backend && ..\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Start Frontend in a new window
echo [DEBUG] Starting Frontend...
start "HiveMind-Frontend" cmd /k "cd frontend && npm run dev"

echo Done. Both services are launching in separate windows.
pause
