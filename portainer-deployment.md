# Portainer Deployment Guide for Telegram Archive Bot

Complete guide to deploy the archive bot using Portainer's web interface.

## 🎯 Prerequisites

1. **Portainer installed** on your server
2. **Domain configured**: `dimibot.coolphill.com` pointing to your server
3. **Bot token** from @BotFather
4. **SSL certificate** (we'll cover this)

## 📋 Step-by-Step Deployment

### Step 1: Access Portainer

1. Open your Portainer web interface: `https://your-server:9443`
2. Login with your admin credentials

### Step 2: Create the Stack

1. **Navigate to Stacks**
   - Click "Stacks" in the left sidebar
   - Click "Add stack" button

2. **Configure Stack**
   - **Name**: `dimibot`
   - **Build method**: Select "Web editor"

### Step 3: Docker Compose Configuration

Copy this into the web editor:

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
      - dimibot_network

  # Optional: Nginx reverse proxy (if not using external nginx)
  nginx:
    image: nginx:alpine
    container_name: dimibot-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - dimibot
    networks:
      - dimibot_network

volumes:
  dimibot_data:
    driver: local
  dimibot_logs:
    driver: local

networks:
  dimibot_network:
    driver: bridge
```

### Step 4: Environment Variables

In the "Environment variables" section, add:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | `your_bot_token_here` |
| `WEBHOOK_URL` | `https://dimibot.coolphill.com/webhook` |

### Step 5: Upload Files

Since Portainer needs the source files, you have two options:

#### Option A: Git Repository (Recommended)
1. **Create Git Repository**
   - Push all bot files to a Git repository
   - In Portainer, select "Repository" as build method
   - Enter your repository URL

#### Option B: Upload Files
1. **Prepare files on server**
   ```bash
   # Create directory
   sudo mkdir -p /opt/dimibot
   cd /opt/dimibot
   
   # Copy all files here
   # - Dockerfile
   # - docker_webhook_bot.py
   # - requirements-docker.txt
   # - nginx.conf (if using internal nginx)
   ```

2. **In Portainer**
   - Select "Upload" as build method
   - Upload a zip file containing all source files

### Step 6: Deploy Stack

1. Click "Deploy the stack"
2. Wait for deployment to complete
3. Check container status in "Containers" section

## 🔧 Alternative: Using Pre-built Image

If you prefer not to build from source, create a pre-built image:

### Step 1: Build Image Locally
```bash
# On your development machine
docker build -t your-registry/dimibot:latest .
docker push your-registry/dimibot:latest
```

### Step 2: Simplified Stack Configuration
```yaml
version: '3.8'

services:
  dimibot:
    image: your-registry/dimibot:latest
    container_name: dimibot
    restart: unless-stopped
    ports:
      - "8443:8443"
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - WEBHOOK_URL=https://dimibot.coolphill.com/webhook
    volumes:
      - dimibot_data:/app/data
      - dimibot_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8443/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  dimibot_data:
  dimibot_logs:
```

## 🌐 SSL/Reverse Proxy Setup

### Option 1: External Nginx (Recommended)

1. **Install nginx on host**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```

2. **Create nginx config**
   ```bash
   sudo nano /etc/nginx/sites-available/dimibot.coolphill.com
   ```
   
   Copy the content from `nginx.conf` file

3. **Enable site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/dimibot.coolphill.com /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Get SSL certificate**
   ```bash
   sudo certbot --nginx -d dimibot.coolphill.com
   ```

### Option 2: Traefik (If you use Traefik)

Add these labels to your service in the stack:

```yaml
services:
  dimibot:
    # ... existing config
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dimibot.rule=Host(`dimibot.coolphill.com`)"
      - "traefik.http.routers.dimibot.tls=true"
      - "traefik.http.routers.dimibot.tls.certresolver=letsencrypt"
      - "traefik.http.services.dimibot.loadbalancer.server.port=8443"
    networks:
      - traefik
      - default

networks:
  traefik:
    external: true
```

## 📊 Monitoring in Portainer

### Container Health
1. **Go to Containers**
2. **Click on `dimibot` container**
3. **Check "Health" status**
4. **View logs in "Logs" tab**

### Resource Usage
1. **Container Stats**
   - CPU usage
   - Memory usage
   - Network I/O

### Volume Management
1. **Go to Volumes**
2. **Find `dimibot_data` and `dimibot_logs`**
3. **Browse files or backup volumes**

## 🔄 Management Tasks

### Update Bot
1. **Go to Stacks → dimibot**
2. **Click "Editor"**
3. **Modify configuration if needed**
4. **Click "Update the stack"**
5. **Select "Re-pull image and redeploy"**

### View Logs
1. **Go to Containers**
2. **Click on `dimibot`**
3. **Click "Logs" tab**
4. **Use filters for specific log levels**

### Restart Container
1. **Go to Containers**
2. **Select `dimibot` container**
3. **Click "Restart"**

### Scale Service (if needed)
1. **Go to Stacks → dimibot**
2. **Click "Editor"**
3. **Add replica configuration**:
   ```yaml
   deploy:
     replicas: 3
   ```

## 🐛 Troubleshooting

### Container Won't Start
1. **Check logs** in Portainer
2. **Verify environment variables** are set correctly
3. **Check if port 8443 is available**

### Bot Not Responding
1. **Test health endpoint**:
   ```bash
   curl http://your-server:8443/health
   ```
2. **Check webhook is accessible**:
   ```bash
   curl https://dimibot.coolphill.com/webhook
   ```
3. **Verify bot token** in environment variables

### SSL Issues
1. **Check nginx configuration**
2. **Verify certificate** is valid
3. **Test HTTPS access** to webhook URL

## 📱 Testing the Deployment

### 1. Health Check
```bash
curl https://dimibot.coolphill.com/health
```
Should return:
```json
{
  "status": "healthy",
  "bot": "Angel_Dimi_Bot",
  "timestamp": "2025-01-XX...",
  "processed_messages": 0
}
```

### 2. Bot Functionality
1. **Add @Angel_Dimi_Bot to a chat**
2. **Send**: `@Angel_Dimi_Bot archive https://reddit.com`
3. **Should get instant reply** with archive link

### 3. Monitor Logs
In Portainer:
1. Go to Containers → dimibot → Logs
2. Should see webhook registration and message processing

## 🔒 Security Considerations

### Environment Variables
- **Never expose bot token** in stack configuration
- **Use Portainer secrets** for sensitive data:
  1. Go to Secrets
  2. Create new secret with bot token
  3. Reference in stack: `${DOCKER-SECRET:bot_token}`

### Network Security
- **Use custom networks** to isolate containers
- **Limit port exposure** to only necessary ports
- **Enable firewall** on host system

### Regular Updates
- **Monitor container health** regularly
- **Update base images** periodically
- **Backup persistent data** regularly

## 📈 Advanced Configuration

### Custom Build Args
```yaml
services:
  dimibot:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - PYTHON_VERSION=3.11
        - BUILD_DATE=${BUILD_DATE}
```

### Resource Limits
```yaml
services:
  dimibot:
    # ... existing config
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Multiple Environments
Create separate stacks for different environments:
- `dimibot-dev` (development)
- `dimibot-staging` (staging)
- `dimibot-prod` (production)

## 🎯 Quick Deployment Checklist

- [ ] Portainer accessible
- [ ] Domain DNS configured
- [ ] Bot token obtained
- [ ] Source files ready
- [ ] Stack created in Portainer
- [ ] Environment variables set
- [ ] Stack deployed successfully
- [ ] Container health check passing
- [ ] SSL certificate configured
- [ ] Webhook URL accessible
- [ ] Bot responding to mentions
- [ ] Logs showing normal operation

## 📞 Support Commands

```bash
# Check container status
docker ps | grep dimibot

# View logs
docker logs dimibot -f

# Test health
curl https://dimibot.coolphill.com/health

# Check webhook info
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Container stats
docker stats dimibot
```