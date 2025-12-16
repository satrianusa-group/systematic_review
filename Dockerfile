# Multi-stage Dockerfile for Systematic Review Chatbot
# This builds both backend and frontend in a single image

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

# Copy backend application files
COPY backend/app.py .
COPY backend/utils.py .

# Create necessary directories
RUN mkdir -p uploads indexes

# Stage 2: Final Image with both Backend and Frontend
FROM python:3.10-slim

WORKDIR /app

# Install nginx and supervisor to run both services
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend files from builder
COPY --from=backend-builder /app/backend /app/backend

# Copy frontend files
COPY frontend/index.html /usr/share/nginx/html/
COPY frontend/app.js /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm /etc/nginx/sites-enabled/default

# Create supervisor config to run both services
RUN echo '[supervisord]\n\
nodaemon=true\n\
logfile=/var/log/supervisor/supervisord.log\n\
pidfile=/var/run/supervisord.pid\n\
\n\
[program:backend]\n\
command=python /app/backend/app.py\n\
directory=/app/backend\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/var/log/backend.err.log\n\
stdout_logfile=/var/log/backend.out.log\n\
environment=PYTHONUNBUFFERED="1"\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stderr_logfile=/var/log/nginx.err.log\n\
stdout_logfile=/var/log/nginx.out.log' > /etc/supervisor/conf.d/supervisord.conf

# Create log directory
RUN mkdir -p /var/log/supervisor

# Expose ports (80 for frontend, 5001 for backend)
EXPOSE 80 5001

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/ && curl -f http://localhost:5001/ || exit 1

# Start supervisor to manage both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]