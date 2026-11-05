@echo off
REM ForexNews AI - Windows Startup Script

echo 🚀 Starting ForexNews AI...

REM Check if .env exists
if not exist .env (
    echo ⚠️  .env file not found. Copying from .env.example...
    copy .env.example .env
    echo ❌ Please edit .env with your API keys before running!
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist backend\ml\models mkdir backend\ml\models
if not exist data\raw mkdir data\raw
if not exist data\processed mkdir data\processed
if not exist data\cache mkdir data\cache
if not exist logs mkdir logs

REM Pull latest images
echo 📦 Pulling Docker images...
docker-compose pull

REM Start services
echo 🔧 Starting services...
docker-compose up -d

REM Wait for services to be healthy
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo 🎉 ForexNews AI is running!
echo.
echo 📊 Access points:
echo    Frontend:     http://localhost:3000
echo    Backend API:  http://localhost:8000
echo    API Docs:     http://localhost:8000/docs
echo    Flower:       http://localhost:5555
echo.
echo 📝 Logs:
echo    docker-compose logs -f backend
echo    docker-compose logs -f frontend
echo    docker-compose logs -f celery-worker
echo.
echo 🛑 To stop: docker-compose down
echo.
pause