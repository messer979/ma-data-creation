#!/bin/bash

# Startup script for testing the inventory transfer UI with dummy server
# This script starts both the dummy server and Streamlit app

echo "🚀 Starting Inventory Transfer Test Environment"
echo "=============================================="

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python -c "import streamlit, flask, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Required packages not installed. Installing..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies OK"

# Create log directory
mkdir -p logs

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "$DUMMY_PID" ]; then
        kill $DUMMY_PID 2>/dev/null
        echo "   Stopped dummy server (PID: $DUMMY_PID)"
    fi
    if [ ! -z "$STREAMLIT_PID" ]; then
        kill $STREAMLIT_PID 2>/dev/null
        echo "   Stopped Streamlit app (PID: $STREAMLIT_PID)"
    fi
    echo "✅ Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo ""
echo "🌐 Starting dummy server on http://localhost:5000..."
python dummy_server.py > logs/dummy_server.log 2>&1 &
DUMMY_PID=$!

# Wait a moment for server to start
sleep 3

# Test if dummy server is running
echo "🧪 Testing dummy server..."
python test_setup.py
if [ $? -ne 0 ]; then
    echo "❌ Dummy server test failed"
    cleanup
    exit 1
fi

echo ""
echo "🎨 Starting Streamlit app on http://localhost:8501..."
streamlit run app.py --server.port 8501 > logs/streamlit.log 2>&1 &
STREAMLIT_PID=$!

echo ""
echo "✅ Both services are starting up!"
echo ""
echo "📋 Available Services:"
echo "   🌐 Dummy Server: http://localhost:5000"
echo "   🎨 Streamlit App: http://localhost:8501"
echo ""
echo "📖 Usage Instructions:"
echo "1. Open http://localhost:8501 in your browser"
echo "2. Navigate to 'Data Import' page"
echo "3. Check the '🧪 Test Mode' checkbox"
echo "4. Configure your transfer settings"
echo "5. Click 'Start Transfer' to test"
echo ""
echo "📁 Logs are being written to:"
echo "   - logs/dummy_server.log"
echo "   - logs/streamlit.log"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Wait for both processes
wait $DUMMY_PID $STREAMLIT_PID
