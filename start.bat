@echo off

:: Kill anything on these ports
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a 2>nul

timeout /t 1 /nobreak >nul

:: Start FastAPI backend
cd /d %~dp0JustBidIt\backend
call venv\Scripts\activate
start "Backend" cmd /k "uvicorn main:app --reload"

:: Start frontend
cd /d %~dp0JustBidIt\frontend
start "Frontend" cmd /k "python -m http.server 3000"

echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Two terminal windows have opened. Close them to stop the servers.
pause
