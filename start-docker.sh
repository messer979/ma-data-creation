#!/bin/bash

echo "Starting MA Data Creation Tool with Docker"
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

# Start the core services
docker-compose up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo "🔍 Service Status:"
docker-compose ps

echo ""
echo "✅ MA Data Creation Tool is running!"
echo "📊 Access the application at: http://localhost:8080"
echo ""
echo "Useful commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart:       docker-compose restart"
echo ""

# Make script executable
chmod +x "$0" 2>/dev/null || true
