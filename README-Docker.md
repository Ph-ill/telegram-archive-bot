# Docker Deployment for Telegram Archive Bot

Complete Docker setup for deploying the archive bot at `dimibot.coolphill.com`.

## 🚀 Quick Start

### 1. Clone/Copy Files
```bash
# Copy all files to your server
scp -r * user@yourserver:/opt/dimibot/
ssh user@yourserver
cd /opt/dimibot
```

### 2. Configure Environment
```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Set your bot token:
BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://dimibot.coolphill.com/webhook
```

### 3. Deploy
```bash
# Run deployment script
./deploy-docker.sh
```

### 4. Set Up Reverse Proxy
```bash
# Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/dimibot.coolphill.com
sudo ln -s /etc/nginx/sites-available/dimibot.coolphill.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Get SSL Certificate
```bash
# Using certbot
sudo certbot --nginx -d dimibot.coolphill.com
```

## 📁 File Structure

```
/opt/dimibot/
├── Dockerfile                 # Container definition
├── docker-compose.yml        # Container orchestration
├── docker_webhook_bot.py     # Main bot application
├── requirements-docker.txt   # Python dependencies
├── .env                      # Environment variables
├── deploy-docker.sh          # Deployment script
├── nginx.conf               # Nginx configuration
├── data/                    # Persistent data (auto-created)
├── logs/                    # Application logs (auto-created)
└── README-Docker.md         # This file
```

## 🔧 Management Commands

### Container Management
```bash
# View logs
docker logs dimibot -f

# Restart container
docker-compose restart

# Stop container
docker-compose down

# Rebuild and restart
docker-compose up --build -d

# Shell into container
docker exec -it dimibot bash
```

### Monitoring
```bash
# Check health
curl https://dimibot.coolphill.com/health

# View stats
curl https://dimibot.coolphill.com/stats

# Container stats
docker stats dimibot
```

## 🌐 Endpoints

- **`/webhook`** - Telegram webhook endpoint
- **`/health`** - Health check (returns JSON status)
- **`/stats`** - Bot statistics
- **`/`** - Root endpoint (service info)

## 🔒 Security Features

- **Non-root user** in container
- **SSL/TLS termination** via nginx
- **Security headers** configured
- **Health checks** for monitoring
- **Persistent data** outside container
- **Log rotation** configured

## 📊 Monitoring & Logs

### Application Logs
```bash
# Real-time logs
docker logs dimibot -f

# Last 100 lines
docker logs dimibot --tail 100

# Logs with timestamps
docker logs dimibot -t
```

### Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### Health Monitoring
```bash
# Simple health check script
#!/bin/bash
if curl -s https://dimibot.coolphill.com/health | grep -q "healthy"; then
    echo "✅ Bot is healthy"
else
    echo "❌ Bot is unhealthy"
    # Restart container
    docker-compose restart
fi
```

## 🔄 Updates & Maintenance

### Update Bot Code
```bash
# Pull new code
git pull  # or copy new files

# Rebuild and restart
docker-compose up --build -d
```

### Backup Data
```bash
# Backup processed messages
cp data/processed_messages.json backup/processed_messages_$(date +%Y%m%d).json

# Backup logs
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/
```

### Clean Up
```bash
# Remove old images
docker image prune -f

# Remove old containers
docker container prune -f

# Clean up logs (keep last 7 days)
find logs/ -name "*.log" -mtime +7 -delete
```

## 🐛 Troubleshooting

### Bot Not Responding
1. Check container is running: `docker ps | grep dimibot`
2. Check logs: `docker logs dimibot -f`
3. Test health endpoint: `curl https://dimibot.coolphill.com/health`
4. Verify webhook is set: Check Telegram webhook info

### SSL Issues
1. Check certificate: `sudo certbot certificates`
2. Test nginx config: `sudo nginx -t`
3. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`

### Container Issues
1. Check container health: `docker inspect dimibot | grep Health`
2. Check resource usage: `docker stats dimibot`
3. Restart container: `docker-compose restart`

### Webhook Issues
1. Test webhook URL accessibility: `curl https://dimibot.coolphill.com/webhook`
2. Check Telegram webhook status: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
3. Verify bot token is correct

## 📈 Scaling

### Multiple Instances
```yaml
# In docker-compose.yml
services:
  dimibot:
    # ... existing config
    deploy:
      replicas: 3
    ports:
      - "8443-8445:8443"
```

### Load Balancing
```nginx
# In nginx.conf
upstream dimibot_backend {
    server localhost:8443;
    server localhost:8444;
    server localhost:8445;
}

server {
    # ... existing config
    location / {
        proxy_pass http://dimibot_backend;
        # ... existing proxy settings
    }
}
```

## 🎯 Testing

### Test Archive Functionality
1. Add @Angel_Dimi_Bot to a chat
2. Send: `@Angel_Dimi_Bot archive https://reddit.com`
3. Should get instant reply with archive link

### Load Testing
```bash
# Simple load test
for i in {1..10}; do
    curl -s https://dimibot.coolphill.com/health &
done
wait
```

## 📞 Support

- **Logs**: Check `docker logs dimibot -f`
- **Health**: `curl https://dimibot.coolphill.com/health`
- **Stats**: `curl https://dimibot.coolphill.com/stats`
- **Container**: `docker inspect dimibot`