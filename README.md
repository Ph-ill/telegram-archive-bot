# Telegram Archive Bot

A Telegram bot that automatically archives links using archive.ph when mentioned in messages.

## 🤖 Bot Information
- **Username**: @Angel_Dimi_Bot
- **ID**: 8144911230

## ✨ Features

- **Creates fresh archives** using Selenium browser automation
- **Real-time responses** via webhooks
- **Works in any chat** - personal, groups, channels
- **Docker containerized** with Chrome and ChromeDriver
- **Health monitoring** and logging
- **Persistent data storage**
- **Clean message format** - just shows archived links

## 🚀 Quick Start

### Using Portainer + GitHub (Recommended)

1. **Fork/Clone this repository**
2. **In Portainer**: Stacks → Add stack → Repository
3. **Repository URL**: `https://github.com/yourusername/telegram-archive-bot`
4. **Set environment variables**:
   - `BOT_TOKEN`: Your bot token from @BotFather
   - `WEBHOOK_URL`: `https://yourdomain.com/webhook`
5. **Deploy the stack**

### Manual Docker Deployment

```bash
# Clone repository
git clone https://github.com/yourusername/telegram-archive-bot
cd telegram-archive-bot

# Set environment variables
cp .env.example .env
# Edit .env with your bot token and webhook URL

# Deploy with Docker Compose
docker-compose up -d
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | `123456:ABC-DEF...` |
| `WEBHOOK_URL` | Public HTTPS URL for webhook | `https://bot.example.com/webhook` |
| `PORT` | Internal port (optional) | `8443` |

### Docker Compose

```yaml
version: '3.8'
services:
  dimibot:
    build: .
    ports:
      - "8443:8443"
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - WEBHOOK_URL=${WEBHOOK_URL}
    volumes:
      - dimibot_data:/app/data
      - dimibot_logs:/app/logs
    restart: unless-stopped

volumes:
  dimibot_data:
  dimibot_logs:
```

## 🌐 Usage

1. **Add the bot** to any chat (personal, group, or channel)
2. **Mention the bot** with URLs:
   ```
   @Angel_Dimi_Bot please archive https://example.com
   ```
3. **Get instant reply** with archive links:
   ```
   @YourName Here are your archived links:

   📁 https://example.com
      → https://archive.ph/2025/https://example.com
   ```

## 📊 Monitoring

### Health Check
```bash
curl https://yourdomain.com/health
```

### Statistics
```bash
curl https://yourdomain.com/stats
```

### Logs
```bash
# Docker logs
docker logs dimibot -f

# Or in Portainer: Containers → dimibot → Logs
```

## 🔒 Security

- **Non-root user** in container
- **HTTPS required** for webhooks
- **Environment variables** for sensitive data
- **Security headers** via reverse proxy
- **Health checks** for monitoring

## 🛠️ Development

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements-docker.txt

# Set environment variables
export BOT_TOKEN="your_bot_token"
export WEBHOOK_URL="https://your-ngrok-url.ngrok.io/webhook"

# Run bot
python docker_webhook_bot.py
```

### Testing with ngrok
```bash
# Install ngrok, then:
ngrok http 8443

# Use the HTTPS URL for WEBHOOK_URL
# Example: https://abc123.ngrok.io/webhook
```

## 📁 Project Structure

```
telegram-archive-bot/
├── Dockerfile                 # Container definition
├── docker-compose.yml        # Container orchestration
├── docker_webhook_bot.py     # Main bot application (Selenium-powered)
├── requirements-docker.txt   # Python dependencies
├── nginx.conf                # Nginx reverse proxy configuration
├── .env.example              # Environment template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## 🔄 Updates

### Via Portainer
1. **Push changes** to GitHub
2. **In Portainer**: Stacks → dimibot → Pull and redeploy

### Via Docker Compose
```bash
git pull
docker-compose up --build -d
```

## 🐛 Troubleshooting

### Bot Not Responding
1. Check container health: `docker ps | grep dimibot`
2. View logs: `docker logs dimibot -f`
3. Test webhook: `curl https://yourdomain.com/webhook`
4. Verify bot token and webhook URL

### SSL/HTTPS Issues
1. Ensure domain points to your server
2. Check SSL certificate: `sudo certbot certificates`
3. Test HTTPS access: `curl https://yourdomain.com/health`

### Archive.ph Issues
- Some URLs may not be archivable
- Rate limiting may occur with many requests
- Bot always provides fallback URLs

## 📞 Support

- **Health endpoint**: `/health`
- **Stats endpoint**: `/stats`
- **Container logs**: `docker logs dimibot -f`
- **GitHub Issues**: For bug reports and feature requests

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Archive.ph for providing the archiving service
- Telegram Bot API for webhook support
- Docker and Portainer for containerization