FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_THEME_BASE=dark

# Set work directory
WORKDIR /app

# Install system dependencies including Redis
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p .streamlit logs __pycache__ data /var/lib/redis /var/log/supervisor

# Create Redis configuration
RUN echo "bind 127.0.0.1" > /etc/redis/redis.conf && \
    echo "port 6379" >> /etc/redis/redis.conf && \
    echo "dir /var/lib/redis" >> /etc/redis/redis.conf && \
    echo "logfile /var/log/redis/redis-server.log" >> /etc/redis/redis.conf && \
    echo "daemonize no" >> /etc/redis/redis.conf

# Create supervisor configuration
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
childlogdir=/var/log/supervisor

[program:redis]
command=redis-server /etc/redis/redis.conf
autostart=true
autorestart=true
user=redis
stdout_logfile=/var/log/supervisor/redis.log
stderr_logfile=/var/log/supervisor/redis_error.log

[program:streamlit]
command=streamlit run app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
directory=/app
autostart=true
autorestart=true
user=appuser
stdout_logfile=/var/log/supervisor/streamlit.log
stderr_logfile=/var/log/supervisor/streamlit_error.log
environment=PYTHONUNBUFFERED=1,REDIS_URL=redis://localhost:6379/0,CELERY_BROKER_URL=redis://localhost:6379/0,CELERY_RESULT_BACKEND=redis://localhost:6379/0

[program:celery]
command=celery -A celery_app worker --loglevel=info --concurrency=4
directory=/app
autostart=true
autorestart=true
user=appuser
stdout_logfile=/var/log/supervisor/celery.log
stderr_logfile=/var/log/supervisor/celery_error.log
environment=PYTHONUNBUFFERED=1,REDIS_URL=redis://localhost:6379/0,CELERY_BROKER_URL=redis://localhost:6379/0,CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF

# Ensure proper permissions
RUN chmod +x app.py

# Create a non-root user for security and create redis user
RUN useradd --create-home --shell /bin/bash appuser && \
    useradd --system --home /var/lib/redis --shell /bin/false redis && \
    chown -R appuser:appuser /app && \
    chown -R redis:redis /var/lib/redis && \
    mkdir -p /var/log/redis && \
    chown -R redis:redis /var/log/redis

# Health check for both Redis and Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD redis-cli ping && curl -f http://localhost:8080/_stcore/health || exit 1

# Expose ports
EXPOSE 8080 6379

# Run supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
