#!/bin/bash

echo "MA Data Creation Tool - Local Development Setup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i:$1 >/dev/null 2>&1
}

# Function to kill processes on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Killing processes on port $port...${NC}"
        kill -9 $pids 2>/dev/null
        sleep 2
    fi
}

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

if ! command_exists redis-server; then
    echo -e "${RED}❌ Redis is not installed. Please install it first:${NC}"
    echo "  Ubuntu/Debian: sudo apt-get install redis-server"
    exit 1
fi

if ! command_exists celery; then
    echo -e "${RED}❌ Celery is not installed. Installing from requirements.txt...${NC}"
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        pip install celery redis
    fi
fi

echo -e "${GREEN}✅ Dependencies check passed${NC}"
echo ""

# Create necessary directories
mkdir -p logs data

# Function to start Redis
start_redis() {
    echo -e "${BLUE}Starting Redis server...${NC}"
    touch logs/redis.log
    
    if port_in_use 6379; then
        echo -e "${GREEN}Redis already running on port 6379${NC}"
        echo -e "${GREEN}✅ Using existing Redis instance${NC}"
            return 
    fi
    # Start Redis in background
    redis-server --daemonize yes --port 6379 --bind 127.0.0.1 --logfile logs/redis.log --dir ./data
    
    # Wait for Redis to start
    sleep 2
    
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis started successfully on port 6379${NC}"
        echo "   Log file: logs/redis.log"
        return 0
    else
        echo -e "${RED}❌ Failed to start Redis${NC}"
        return 1
    fi
}

# Function to start Celery
start_celery() {
    echo -e "${BLUE}Starting Celery worker...${NC}"
    
    # Check if celery_app.py exists
    if [ ! -f "celery_app.py" ]; then
        echo -e "${RED}❌ celery_app.py not found in current directory${NC}"
        return 1
    fi
    
    # Set environment variables
    export REDIS_URL=redis://localhost:6379/0
    export CELERY_BROKER_URL=redis://localhost:6379/0
    export CELERY_RESULT_BACKEND=redis://localhost:6379/0
    
    # Start Celery worker in background
    echo -e "${YELLOW}Starting Celery worker with 4 concurrent processes...${NC}"
    touch logs/celery.log
    nohup celery -A celery_app worker --loglevel=info --concurrency=4 > logs/celery.log 2>&1 &
    CELERY_PID=$!
    
    # Wait a moment for Celery to start
    sleep 3
    
    # Check if Celery is running
    if kill -0 $CELERY_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Celery worker started successfully (PID: $CELERY_PID)${NC}"
        echo "   Log file: logs/celery.log"
        echo "   Monitor with: tail -f logs/celery.log"
        echo $CELERY_PID > logs/celery.pid
        return 0
    else
        echo -e "${RED}❌ Failed to start Celery worker${NC}"
        echo "Check logs/celery.log for details"
        return 1
    fi
}

# Function to show status
show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    echo "=============="
    
    # Redis status
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis: Running on port 6379${NC}"
    else
        echo -e "${RED}❌ Redis: Not running${NC}"
    fi
    
    # Celery status
    if [ -f "logs/celery.pid" ]; then
        CELERY_PID=$(cat logs/celery.pid)
        if kill -0 $CELERY_PID 2>/dev/null; then
            echo -e "${GREEN}✅ Celery: Running (PID: $CELERY_PID)${NC}"
        else
            echo -e "${RED}❌ Celery: Not running (stale PID file)${NC}"
            rm -f logs/celery.pid
        fi
    else
        echo -e "${RED}❌ Celery: Not running${NC}"
    fi
}

# Function to stop services
stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    
    # Stop Celery
    if [ -f "logs/celery.pid" ]; then
        CELERY_PID=$(cat logs/celery.pid)
        if kill -0 $CELERY_PID 2>/dev/null; then
            echo -e "${YELLOW}Stopping Celery worker (PID: $CELERY_PID)...${NC}"
            kill $CELERY_PID
            sleep 2
            if kill -0 $CELERY_PID 2>/dev/null; then
                echo -e "${YELLOW}Force killing Celery worker...${NC}"
                kill -9 $CELERY_PID
            fi
        fi
        rm -f logs/celery.pid
    fi
    
    # Stop Redis
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${YELLOW}Stopping Redis server...${NC}"
        redis-cli shutdown
    fi
    
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}Available log files:${NC}"
    echo "1. Redis logs: logs/redis.log"
    echo "2. Celery logs: logs/celery.log"
    echo "3. Follow Celery logs (live)"
    echo "4. Follow Redis logs (live)"
    echo "5. Back to main menu"
    echo ""
    
    read -p "Enter your choice (1-5): " choice
    
    case $choice in
        1)
            if [ -f "logs/redis.log" ]; then
                cat logs/redis.log
            else
                echo -e "${RED}Redis log file not found${NC}"
            fi
            ;;
        2)
            if [ -f "logs/celery.log" ]; then
                cat logs/celery.log
            else
                echo -e "${RED}Celery log file not found${NC}"
            fi
            ;;
        3)
            if [ -f "logs/celery.log" ]; then
                echo -e "${BLUE}Following Celery logs (Ctrl+C to exit)...${NC}"
                tail -f logs/celery.log
            else
                echo -e "${RED}Celery log file not found${NC}"
            fi
            ;;
        4)
            if [ -f "logs/redis.log" ]; then
                echo -e "${BLUE}Following Redis logs (Ctrl+C to exit)...${NC}"
                tail -f logs/redis.log
            else
                echo -e "${RED}Redis log file not found${NC}"
            fi
            ;;
        5)
            return
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

# Main menu
while true; do
    echo ""
    echo -e "${BLUE}Choose an action:${NC}"
    echo "1. Start Redis and Celery"
    echo "2. Stop all services"
    echo "3. Show service status"
    echo "4. View logs"
    echo "5. Restart services"
    echo "6. Exit"
    echo ""
    
    read -p "Enter your choice (1-6): " choice
    
    case $choice in
        1)
            start_redis
            if [ $? -eq 0 ]; then
                start_celery
                if [ $? -eq 0 ]; then
                    echo ""
                    echo -e "${GREEN}🎉 All services started successfully!${NC}"
                    echo ""
                    echo -e "${BLUE}Now you can:${NC}"
                    echo "• Run Streamlit: streamlit run app.py"
                    echo "• Monitor logs: tail -f logs/celery.log"
                    echo "• Test Redis: redis-cli ping"
                    echo ""
                fi
            fi
            ;;
        2)
            stop_services
            ;;
        3)
            show_status
            ;;
        4)
            show_logs
            ;;
        5)
            stop_services
            sleep 2
            start_redis
            if [ $? -eq 0 ]; then
                start_celery
            fi
            ;;
        6)
            echo -e "${BLUE}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please enter 1-6.${NC}"
            ;;
    esac
done
