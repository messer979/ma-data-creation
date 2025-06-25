#!/bin/bash

echo "Starting MA Data Creation Tool (Docker only)"
echo "============================================"

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
    -p 2222:22 \
    -v "$(pwd)/logs:/app/logs" \
    -v "$(pwd)/data:/app/data" \
    -v ma-data-redis-volume:/var/lib/redis \
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
    exit 1
fi
