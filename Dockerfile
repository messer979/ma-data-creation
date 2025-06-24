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

# Install system dependencies including Redis and SSH
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    redis-server \
    supervisor \
    openssh-server \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip config set global.timeout 600 && pip config set global.retries 5 && pip install --progress-bar=on -r requirements.txt

# Copy application code
COPY . .

# Create users first
RUN useradd --create-home --shell /bin/bash appuser && \
    (id -u redis >/dev/null 2>&1 || useradd --system --home /var/lib/redis --shell /bin/false redis)

# Create necessary directories
RUN mkdir -p .streamlit logs __pycache__ data /var/lib/redis /var/log/supervisor /var/run/sshd /var/log/redis /etc/redis && \
    chmod 755 /var/lib/redis /var/log/redis /etc/redis

# Create Redis configuration
RUN mkdir -p /etc/redis && \
    echo "bind 127.0.0.1" > /etc/redis/redis.conf && \
    echo "port 6379" >> /etc/redis/redis.conf && \
    echo "dir /var/lib/redis" >> /etc/redis/redis.conf && \
    echo "logfile /var/log/redis/redis-server.log" >> /etc/redis/redis.conf && \
    echo "daemonize no" >> /etc/redis/redis.conf && \
    echo "save 900 1" >> /etc/redis/redis.conf && \
    echo "save 300 10" >> /etc/redis/redis.conf && \
    echo "save 60 10000" >> /etc/redis/redis.conf && \
    chmod 644 /etc/redis/redis.conf

# Configure SSH
RUN echo 'root:debug123' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create supervisor configuration
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
childlogdir=/var/log/supervisor

[program:sshd]
command=/usr/sbin/sshd -D
autostart=true
autorestart=true
user=root
stdout_logfile=/var/log/supervisor/sshd.log
stderr_logfile=/var/log/supervisor/sshd_error.log

[program:redis]
command=redis-server /etc/redis/redis.conf
autostart=true
autorestart=true
user=root
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
environment=PYTHONUNBUFFERED=1,HOME=/home/appuser,REDIS_URL=redis://localhost:6379/0,CELERY_BROKER_URL=redis://localhost:6379/0,CELERY_RESULT_BACKEND=redis://localhost:6379/0

[program:celery]
command=celery -A celery_app worker --loglevel=info --concurrency=4
directory=/app
autostart=true
autorestart=true
user=appuser
stdout_logfile=/var/log/supervisor/celery.log
stderr_logfile=/var/log/supervisor/celery_error.log
environment=PYTHONUNBUFFERED=1,HOME=/home/appuser,REDIS_URL=redis://localhost:6379/0,CELERY_BROKER_URL=redis://localhost:6379/0,CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF

# Ensure proper permissions
RUN chmod +x app.py

# Set proper permissions
RUN chown -R appuser:appuser /app && \
    chown -R redis:redis /var/lib/redis && \
    chown -R redis:redis /var/log/redis && \
    chmod 755 /var/lib/redis && \
    chmod 755 /var/log/redis && \
    echo 'appuser:debug123' | chpasswd && \
    mkdir -p /home/appuser/.streamlit && \
    chown -R appuser:appuser /home/appuser/.streamlit

# Health check for both Redis and Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD redis-cli ping && curl -f http://localhost:8080/_stcore/health || exit 1

# Expose ports
EXPOSE 8080 22

# Run supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
