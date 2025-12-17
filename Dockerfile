# Multi-stage Dockerfile for Systematic Review Chatbot

# Stage 1: Backend Python Application
FROM python:3.10-slim as backend-builder

WORKDIR /app/backend

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Image with Backend and Frontend
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install nginx, supervisor, and curl for healthcheck
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend files
COPY backend/ /app/backend/

# Create necessary directories
RUN mkdir -p /app/backend/uploads /app/backend/indexes /var/log/supervisor

# Copy frontend files
COPY frontend/index.html /usr/share/nginx/html/
COPY frontend/app.js /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# Create supervisor config
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[program:backend]
command=python /app/backend/app.py
directory=/app/backend
autostart=true
autorestart=true
stderr_logfile=/var/log/backend.err.log
stdout_logfile=/var/log/backend.out.log
environment=PYTHONUNBUFFERED="1"

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stderr_logfile=/var/log/nginx.err.log
stdout_logfile=/var/log/nginx.out.log
EOF

# Expose ports (80 for frontend/nginx, 5001 for backend)
EXPOSE 80 5001

# Start supervisor to manage both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]