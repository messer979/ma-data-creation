#!/bin/bash

echo "SSH Debug Access to MA Data Creation Container"
echo "=============================================="
echo ""
echo "This script helps you connect to the running container via SSH"
echo "for debugging and log inspection."
echo ""

# Check if container is running
if ! docker ps | grep -q ma-data-app; then
    echo "❌ Container 'ma-data-app' is not running."
    echo "   Start it first with: ./start-docker.sh"
    exit 1
fi

echo "📊 Container Status:"
docker ps --filter name=ma-data-app --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🔗 SSH Connection Options:"
echo "1. Connect as root user (for system-level debugging)"
echo "2. Connect as appuser (application user)"
echo "3. Show container logs instead"
echo "4. Exit"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🔧 Connecting as root user..."
        echo "Password: debug123"
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@localhost -p 2222
        ;;
    2)
        echo "👤 Connecting as appuser..."
        echo "Password: debug123"
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null appuser@localhost -p 2222
        ;;
    3)
        echo "📋 Container logs:"
        docker logs -f ma-data-app
        ;;
    4)
        exit 0
        ;;
    *)
        echo "Invalid choice. Connecting as root..."
        echo "Password: debug123"
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@localhost -p 2222
        ;;
esac
