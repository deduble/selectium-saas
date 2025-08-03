# Dockerfile for Selextract Cloud Worker with Playwright Browsers
# =============================================================

# Use Ubuntu 22.04 as base image for better Playwright compatibility
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set working directory
WORKDIR /app

# Security hardening and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential packages
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
    # System libraries
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libc6-dev \
    libcap-dev \
    # Font support
    fonts-liberation \
    fonts-dejavu-core \
    fontconfig \
    # Network tools
    curl \
    wget \
    ca-certificates \
    # Additional utilities
    git \
    unzip \
    xvfb \
    # Process management
    supervisor \
    # Cleanup in same layer
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Create python3 symlink
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python

# Upgrade pip and install wheel
RUN python3 -m pip install --upgrade pip setuptools wheel

# Create selextract user and group with consistent UID/GID
RUN groupadd --system --gid 1001 selextract && \
    useradd --system --uid 1001 --gid selextract --home /app --shell /bin/bash selextract

# Create necessary directories with proper permissions
RUN mkdir -p /app/results /app/logs /app/tmp /ms-playwright && \
    chown -R selextract:selextract /app /ms-playwright && \
    chmod -R 755 /app && \
    chmod -R 777 /app/results /app/logs /app/tmp

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright==1.40.0

# Switch to selextract user for Playwright installation
USER selextract

# Install Playwright browsers with dependencies
RUN python3 -m playwright install chromium && \
    python3 -m playwright install firefox && \
    python3 -m playwright install webkit

# Install system dependencies for browsers (switch back to root temporarily)
USER root
RUN python3 -m playwright install-deps chromium && \
    python3 -m playwright install-deps firefox && \
    python3 -m playwright install-deps webkit

# Copy worker application code directly to /app
COPY --chown=selextract:selextract *.py /app/
COPY --chown=selextract:selextract requirements.txt /app/
COPY --chown=selextract:selextract alembic.ini /app/
COPY --chown=selextract:selextract alembic/ /app/alembic/
COPY --chown=selextract:selextract healthcheck.py /app/
RUN chmod +x /app/healthcheck.py

# Copy supervisor configuration
COPY --chown=root:root supervisord.conf /etc/supervisor/conf.d/selextract-worker.conf

# Copy and setup entrypoint script
COPY --chown=root:root entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Environment variables with defaults
ENV CELERY_CONCURRENCY=2 \
    CELERY_MAX_TASKS_PER_CHILD=100 \
    CELERY_TIME_LIMIT=3600 \
    CELERY_SOFT_TIME_LIMIT=3300 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/app

# Volume mounts for persistent data
VOLUME ["/app/results", "/app/logs"]

# Expose ports (if needed for monitoring)
EXPOSE 5555

# Health check for worker service
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 /app/healthcheck.py || exit 1

# Stay as root for supervisord to manage different users
USER root

# Default command - use entrypoint script
CMD ["/app/entrypoint.sh"]

# Add labels for metadata
LABEL maintainer="Selextract Cloud Team" \
      version="1.0.0" \
      description="Selextract Cloud Worker with Playwright browsers" \
      org.opencontainers.image.title="selextract-worker" \
      org.opencontainers.image.description="Web scraping worker with Playwright and Celery" \
      org.opencontainers.image.vendor="Selextract Cloud" \
      org.opencontainers.image.version="1.0.0"