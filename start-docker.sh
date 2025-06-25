#!/bin/bash

echo "Starting MA Data Creation Tool with Docker"
echo "=========================================="
echo ""
echo "Choose how to run:"
echo "1. Docker Compose (recommended for development)"
echo "2. Plain Docker (simpler, single command)"
echo "3. Exit"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        start_with_compose
        ;;
    2)
        start_with_docker
        ;;
    3)
        exit 0
        ;;
    *)
        echo "Invalid choice. Using Docker Compose..."
        start_with_compose
        ;;
esac

start_with_compose() {
    echo ""
    echo "🐳 Starting with Docker Compose..."
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo "❌ Docker Compose is not available. Using plain Docker instead..."
        start_with_docker
        return
    fi

    # Create necessary directories
    mkdir -p logs data

    echo "🚀 Building and starting with Docker Compose..."

    # Try modern docker compose first, fallback to docker-compose
    if docker compose version &> /dev/null; then
        docker compose up --build -d
        COMPOSE_CMD="docker compose"
    else
        docker-compose up --build -d
        COMPOSE_CMD="docker-compose"
    fi

    echo "⏳ Waiting for services to be ready..."
    sleep 10

    echo "🔍 Service Status:"
    $COMPOSE_CMD ps

    echo ""
    echo "✅ MA Data Creation Tool is running!"
    echo "📊 Access the application at: http://localhost:8080"
    echo ""
    echo "Useful commands:"
    echo "  View logs:     $COMPOSE_CMD logs -f"
    echo "  Stop services: $COMPOSE_CMD down"
    echo "  Restart:       $COMPOSE_CMD restart"
}

start_with_docker() {
    echo ""
    echo "� Starting with plain Docker..."
    
    # Create necessary directories
    mkdir -p logs data

    # Build the image
    echo "🔨 Building Docker image..."
    docker build -t ma-data-creation .

    # Stop and remove existing container if it exists
    echo "🧹 Cleaning up existing container..."
    docker stop ma-data-app 2>/dev/null || true
    docker rm ma-data-app 2>/dev/null || true

    # Create and start the container
    echo "🚀 Starting container..."
    docker run -d \
        --name ma-data-app \
        -p 8080:8080 \
        -p 6379:6379 \
        -p 2222:22 \
        -v "$(pwd)/logs:/app/logs" \
        -v "$(pwd)/data:/app/data" \
        -v madata_redis_volume:/var/lib/redis \
        --restart unless-stopped \
        ma-data-creation

    echo "⏳ Waiting for services to be ready..."
    sleep 15

    # Check if container is running
    if docker ps | grep -q ma-data-app; then
        echo "✅ MA Data Creation Tool is running!"
        echo "📊 Access the application at: http://localhost:8080"
        echo ""
        echo "Useful commands:"
        echo "  View logs:     docker logs -f ma-data-app"
        echo "  Stop:          docker stop ma-data-app"
        echo "  Restart:       docker restart ma-data-app"
        echo "  Shell access:  docker exec -it ma-data-app bash"
        echo ""
        echo "Container status:"
        docker ps --filter name=ma-data-app --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "❌ Failed to start container. Check logs:"
        docker logs ma-data-app
    fi
}

# Make script executable
chmod +x "$0" 2>/dev/null || true
