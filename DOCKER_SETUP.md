# Docker Setup with Redis and Celery

This document explains how Redis and Celery are integrated into the Docker setup for the MA Data Creation Tool.

## Architecture Overview

The application now uses a multi-container architecture:

1. **App Container**: Runs the Streamlit application
2. **Redis Container**: Provides message brokering and result storage for Celery
3. **Celery Worker Container**: Processes background tasks (data import, generation, etc.)
4. **Celery Beat Container**: Handles scheduled tasks (optional)

## Quick Start

### Option 1: Use the provided scripts

**For Windows:**
```bash
./start_docker_env.bat
```

**For Linux/Mac:**
```bash
chmod +x start_docker_env.sh
./start_docker_env.sh
```

### Option 2: Manual Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Service Details

### Redis Service
- **Port**: 6379 (internal), not exposed externally by default
- **Purpose**: Message broker and result backend for Celery
- **Health Check**: Redis ping command
- **Data Persistence**: Uses a named volume `redis_data`

### Application Service
- **Port**: 8080 (exposed)
- **Purpose**: Main Streamlit web interface
- **Dependencies**: Waits for Redis to be healthy
- **Environment Variables**:
  - `REDIS_URL`: Connection string to Redis
  - `CELERY_BROKER_URL`: Celery broker URL
  - `CELERY_RESULT_BACKEND`: Celery result backend URL

### Celery Worker Service
- **Purpose**: Processes background tasks
- **Concurrency**: 4 workers by default
- **Command**: `celery -A celery_app worker --loglevel=info --concurrency=4`
- **Dependencies**: Waits for Redis to be healthy

### Celery Beat Service (Optional)
- **Purpose**: Schedules periodic tasks
- **Command**: `celery -A celery_app beat --loglevel=info`
- **Note**: Only needed if you have scheduled tasks

## Environment Configuration

The application automatically detects the environment:

- **Development**: Uses `redis://localhost:6379/0`
- **Docker**: Uses `redis://redis:6379/0` (service name as hostname)

Environment variables can be overridden in `docker-compose.yml` or via `.env` file.

## Data Persistence

- **Redis Data**: Persisted in Docker volume `redis_data`
- **Application Logs**: Mounted to `./logs` directory
- **Application Data**: Mounted to `./data` directory

## Monitoring and Debugging

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f celery-worker
docker-compose logs -f redis
```

### Check Service Health
```bash
# Redis
docker-compose exec redis redis-cli ping

# Application health check
curl http://localhost:8080/_stcore/health

# Celery worker status
docker-compose exec celery-worker celery -A celery_app status
```

### Access Redis CLI
```bash
docker-compose exec redis redis-cli
```

## Development vs Production

### Development Setup
- Uses the provided scripts
- Includes development volumes for hot reloading
- Exposes Redis port for debugging

### Production Considerations
- Remove Redis port exposure
- Use proper secrets management
- Consider Redis clustering for high availability
- Add resource limits
- Use production-grade health checks
- Consider using Redis persistence configuration

## Scaling

To scale Celery workers:
```bash
docker-compose up --scale celery-worker=3 -d
```

## Troubleshooting

### Common Issues

1. **Port 8080 already in use**
   - Change the port mapping in `docker-compose.yml`
   - Or stop the conflicting service

2. **Redis connection refused**
   - Check if Redis container is running: `docker-compose ps`
   - Check Redis logs: `docker-compose logs redis`

3. **Celery worker not processing tasks**
   - Check worker logs: `docker-compose logs celery-worker`
   - Verify Redis connectivity from worker
   - Check task routing configuration

4. **Permission issues**
   - Ensure the `appuser` has proper permissions
   - Check volume mount permissions

### Debugging Commands

```bash
# Restart specific service
docker-compose restart celery-worker

# Rebuild and restart
docker-compose up --build celery-worker

# Execute commands in running container
docker-compose exec app bash
docker-compose exec celery-worker python -c "import celery_app; print('Celery app loaded')"
```

## File Structure Changes

New files added for Docker integration:
- `docker-compose.yml`: Multi-service orchestration
- `entrypoint.sh`: Flexible container startup script
- `start_docker_env.sh`/`.bat`: Development convenience scripts
- `DOCKER_SETUP.md`: This documentation

Modified files:
- `celery_app.py`: Now uses environment variables for Redis connection
- `Dockerfile`: Updated to support multi-service setup
