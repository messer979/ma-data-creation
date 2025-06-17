@echo off
REM Startup script for testing the inventory transfer UI with dummy server
REM This script starts both the dummy server and Streamlit app

echo 🚀 Starting Inventory Transfer Test Environment
echo ==============================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if required packages are installed
echo 📦 Checking dependencies...
python -c "import streamlit, flask, requests" >nul 2>&1
if errorlevel 1 (
    echo ❌ Required packages not installed. Installing...
    pip install -r requirements.txt
)

echo ✅ Dependencies OK

REM Create log directory
if not exist logs mkdir logs

echo.
echo 🌐 Starting dummy server on http://localhost:5000...
start /b python dummy_server.py > logs\dummy_server.log 2>&1

REM Wait a moment for server to start
timeout /t 3 /nobreak >nul

REM Test if dummy server is running
echo 🧪 Testing dummy server...
python test_setup.py
if errorlevel 1 (
    echo ❌ Dummy server test failed
    pause
    exit /b 1
)

echo.
echo 🎨 Starting Streamlit app on http://localhost:8501...
start /b streamlit run app.py --server.port 8501 > logs\streamlit.log 2>&1

echo.
echo ✅ Both services are starting up!
echo.
echo 📋 Available Services:
echo    🌐 Dummy Server: http://localhost:5000
echo    🎨 Streamlit App: http://localhost:8501
echo.
echo 📖 Usage Instructions:
echo 1. Open http://localhost:8501 in your browser
echo 2. Navigate to 'Data Import' page
echo 3. Check the '🧪 Test Mode' checkbox
echo 4. Configure your transfer settings
echo 5. Click 'Start Transfer' to test
echo.
echo 📁 Logs are being written to:
echo    - logs\dummy_server.log
echo    - logs\streamlit.log
echo.
echo Press any key to open the Streamlit app in browser...
pause >nul

REM Open browser to Streamlit app
start http://localhost:8501

echo.
echo Services are running in background.
echo Press any key to stop all services...
pause >nul

REM Kill background processes
taskkill /f /im python.exe /t >nul 2>&1

echo ✅ Services stopped
