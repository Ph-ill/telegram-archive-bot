FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-docker.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY docker_webhook_bot.py .
COPY processed_messages.json* ./

# Create non-root user for security
RUN useradd -m -u 1000 botuser

# Create directories for persistent data and set ownership
RUN mkdir -p /app/data /app/logs && \
    chown -R botuser:botuser /app

USER botuser

# Expose port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8443/health || exit 1

# Default command
CMD ["python", "docker_webhook_bot.py"]