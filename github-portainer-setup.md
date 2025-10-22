# GitHub + Portainer Deployment Guide

The cleanest way to deploy your archive bot using GitHub repository and Portainer's Git integration.

## 🎯 Step 1: Create GitHub Repository

### 1.1 Create Repository
1. Go to GitHub and create a new repository: `telegram-archive-bot`
2. Make it **public** (or private if you have Portainer Business)
3. Don't initialize with README (we'll push existing files)

### 1.2 Push Your Files
```bash
# In your local project directory
git init
git add .
git commit -m "Initial commit - Telegram Archive Bot"
git branch -M main
git remote add origin https://github.com/yourusername/telegram-archive-bot.git
git push -u origin main
```

## 📁 Required Files in Repository

Make sure these files are in your GitHub repo:

```
telegram-archive-bot/
├── Dockerfile
├── docker_webhook_bot.py
├── requirements-docker.txt
├── docker-compose.yml (your modified version)
├── .env.example
├── README.md
└── .gitignore
```

## 🐳 Step 2: Deploy with Portainer

### 2.1 Create Stack from Git Repository

1. **Open Portainer** → **Stacks** → **Add stack**

2. **Stack Configuration**:
   - **Name**: `dimibot`
   - **Build method**: **Repository**

3. **Repository Settings**:
   - **Repository URL**: `https://github.com/yourusername/telegram-archive-bot`
   - **Repository reference**: `refs/heads/main`
   - **Compose path**: `docker-compose.yml`

4. **Environment Variables**:
   ```
   BOT_TOKEN=your_bot_token_here
   WEBHOOK_URL=https://dimibot.coolphill.com/webhook
   ```

5. **Deploy the stack**

## 🔧 Your Modified docker-compose.yml

Your compose file looks good! Here's the formatted version:

```yaml
version: '3.8'

services:
  dimibot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: dimibot
    restart: unless-stopped
    ports:
      - "8443:8443"
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - WEBHOOK_URL=${WEBHOOK_URL:-https://dimibot.coolphill.com/webhook}
      - PORT=8443
    volumes:
      - dimibot_data:/app/data
      - dimibot_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8443/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    networks:
      - Shared

volumes:
  dimibot_data:
    driver: local
  dimibot_logs:
    driver: local

networks:
  Shared:
    external: true
```

## 📋 Step 3: Verify Files

### 3.1 Check Dockerfile
Make sure your `Dockerfile` contains:

```dockerfile
FROM python:3.11-slim

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

# Create directories for persistent data
RUN mkdir -p /app/data /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Expose port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8443/health || exit 1

# Default command
CMD ["python", "docker_webhook_bot.py"]
```

### 3.2 Check requirements-docker.txt
```
flask==2.3.3
requests==2.31.0
gunicorn==21.2.0
```

### 3.3 Add .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt

# Environment variables
.env

# Logs
*.log
logs/

# Data
data/
processed_messages.json

# Docker
.dockerignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

## 🚀 Step 4: Deploy and Test

### 4.1 Deploy
1. **Click "Deploy the stack"** in Portainer
2. **Wait for build to complete** (may take 2-3 minutes first time)
3. **Check container status** - should be "healthy"

### 4.2 Test Deployment
```bash
# Test health endpoint
curl http://your-server:8443/health

# Should return:
# {"status": "healthy", "bot": "Angel_Dimi_Bot", ...}
```

### 4.3 Set up SSL (if not done already)
```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/dimibot << 'EOF'
server {
    listen 80;
    server_name dimibot.coolphill.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dimibot.coolphill.com;
    
    # SSL will be configured by certbot
    
    location / {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/dimibot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d dimibot.coolphill.com
```

## ✅ Step 5: Final Test

1. **Health check**: `curl https://dimibot.coolphill.com/health`
2. **Add @Angel_Dimi_Bot to a chat**
3. **Send**: `@Angel_Dimi_Bot archive https://reddit.com`
4. **Get instant reply** with archive link!

## 🔄 Benefits of GitHub + Portainer

### Easy Updates
1. **Push changes** to GitHub
2. **In Portainer**: Stacks → dimibot → **Pull and redeploy**
3. **Automatic rebuild** with new code

### Version Control
- **Track changes** to your bot
- **Rollback** if needed
- **Collaborate** with others

### Backup
- **Code is safe** in GitHub
- **Easy to redeploy** anywhere

## 🐛 Troubleshooting

### Build Fails
1. **Check all files** are in GitHub repo
2. **Verify Dockerfile** syntax
3. **Check build logs** in Portainer

### Container Won't Start
1. **Check environment variables** are set
2. **View container logs** in Portainer
3. **Verify port 8443** is available

### Bot Not Responding
1. **Test health endpoint**
2. **Check webhook URL** is accessible
3. **Verify bot token** is correct

## 📱 Quick Commands

```bash
# Check container
docker ps | grep dimibot

# View logs
docker logs dimibot -f

# Test locally
curl http://localhost:8443/health

# Test with SSL
curl https://dimibot.coolphill.com/health

# Restart container (in Portainer or CLI)
docker restart dimibot
```

This approach is much cleaner and more maintainable than uploading files directly to Portainer!