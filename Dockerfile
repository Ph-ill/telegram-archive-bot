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

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Copy requirements first for better caching
COPY requirements-selenium.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY selenium_archive_bot.py .

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
CMD ["python", "selenium_archive_bot.py"]