#!/bin/bash

echo "Starting MA Data Creation Tool with Redis and Celery..."
echo "=========================================="

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p logs data

echo "🚀 Building and starting services..."

# Build and start all services
docker-compose up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Redis
if docker-compose exec redis redis-cli ping &> /dev/null; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not responding"
fi

# Check if Streamlit app is accessible
if curl -f http://localhost:8080/_stcore/health &> /dev/null; then
    echo "✅ Streamlit app is running"
else
    echo "❌ Streamlit app is not responding"
fi

# Check Celery worker
if docker-compose logs celery-worker | grep -q "ready"; then
    echo "✅ Celery worker is running"
else
    echo "⚠️  Celery worker may not be ready yet"
fi

echo ""
echo "🎉 All services started!"
echo "📊 Access the application at: http://localhost:8080"
echo "🔧 View logs with: docker-compose logs -f [service-name]"
echo "🛑 Stop services with: docker-compose down"
echo ""
echo "Available services:"
echo "  - app: Streamlit application"
echo "  - redis: Redis server"
echo "  - celery-worker: Celery worker for background tasks"
echo "  - celery-beat: Celery beat scheduler (if needed)"
