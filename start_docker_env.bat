@echo off
echo Starting MA Data Creation Tool with Redis and Celery...
echo ==========================================

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

REM Create necessary directories
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo 🚀 Building and starting services...

REM Build and start all services
docker-compose up --build -d

echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo 🔍 Checking service health...

REM Check Redis
docker-compose exec redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis is running
) else (
    echo ❌ Redis is not responding
)

echo.
echo 🎉 All services started!
echo 📊 Access the application at: http://localhost:8080
echo 🔧 View logs with: docker-compose logs -f [service-name]
echo 🛑 Stop services with: docker-compose down
echo.
echo Available services:
echo   - app: Streamlit application
echo   - redis: Redis server
echo   - celery-worker: Celery worker for background tasks
echo   - celery-beat: Celery beat scheduler (if needed)
echo.
pause
