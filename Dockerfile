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

# Create necessary directories with proper permissions
RUN mkdir -p /app/backend/uploads /app/backend/indexes /var/run \
    && chmod -R 755 /app/backend

# Copy frontend files
COPY frontend/index.html /usr/share/nginx/html/
COPY frontend/app.js /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config
RUN rm -f /etc/nginx/sites-enabled/default

# Create startup script that ensures log directory exists
RUN echo '#!/bin/bash\n\
mkdir -p /var/log/nginx\n\
touch /var/log/nginx/access.log /var/log/nginx/error.log\n\
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf' > /start.sh \
    && chmod +x /start.sh

# Test nginx configuration (this will create the log dir during build)
RUN mkdir -p /var/log/nginx && nginx -t

# Create supervisor config with redirect to stderr/stdout for Docker logs
RUN echo '[supervisord]\n\
nodaemon=true\n\
logfile=/dev/null\n\
logfile_maxbytes=0\n\
pidfile=/var/run/supervisord.pid\n\
user=root\n\
\n\
[program:backend]\n\
command=python -u /app/backend/app.py\n\
directory=/app/backend\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
environment=PYTHONUNBUFFERED="1"\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0' > /etc/supervisor/conf.d/supervisord.conf

# Expose ports (80 for frontend/nginx, 5001 for backend)
EXPOSE 80 5001

# Use startup script instead of direct supervisord
CMD ["/start.sh"]