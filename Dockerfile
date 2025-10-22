FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    unzip \
    ca-certificates \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Let Selenium manage ChromeDriver automatically - remove old version
RUN rm -f /usr/local/bin/chromedriver

# Copy requirements first for better caching
COPY requirements-selenium.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY docker_webhook_bot.py .

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