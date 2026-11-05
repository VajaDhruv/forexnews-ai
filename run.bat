@echo off
REM Simple runner - no checks, just starts

echo Starting ForexNews AI...

REM Create .env if missing
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env >nul
)

echo Starting Docker containers...
docker-compose up -d

echo.
echo Waiting for services...
timeout /t 15 /nobreak >nul

echo.
echo ========================================
echo  ForexNews AI is running!
echo ========================================
echo.
echo Open browser: http://localhost:3000
echo API Docs:     http://localhost:8000/docs
echo.
echo Press any key to exit...
pause