# Webhook Archive Bot Setup Guide

## Prerequisites

1. **Server with public IP/domain**
2. **Bot token** (from @BotFather)
3. **SSL certificate** (required for webhooks)
4. **Python 3.7+**

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Your Bot Token
- Message @BotFather on Telegram
- Use `/newbot` or get existing token
- Copy the token (format: `123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 3. Set Up Domain/SSL
Your webhook URL must be HTTPS. Options:

**Option A: Use a domain with SSL**
```
https://yourdomain.com/webhook
```

**Option B: Use ngrok for testing**
```bash
# Install ngrok
ngrok http 8443

# Use the HTTPS URL it provides
https://abc123.ngrok.io/webhook
```

**Option C: Use Cloudflare Tunnel**
```bash
cloudflared tunnel --url http://localhost:8443
```

### 4. Run the Bot
```bash
python webhook_archive_bot.py YOUR_BOT_TOKEN https://yourdomain.com/webhook
```

Example:
```bash
python webhook_archive_bot.py 123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 https://myserver.com/webhook
```

### 5. Test the Bot
1. Add your bot to a chat
2. Send: `@Angel_Dimi_Bot archive https://reddit.com`
3. Bot should reply instantly with archive link!

## Production Deployment

### Using Gunicorn (Recommended)
```bash
# Create WSGI app file
cat > wsgi.py << 'EOF'
from webhook_archive_bot import WebhookArchiveBot
import os

bot_token = os.environ.get('BOT_TOKEN')
webhook_url = os.environ.get('WEBHOOK_URL')

bot = WebhookArchiveBot(bot_token, webhook_url)
application = bot.app

if __name__ == "__main__":
    bot.run()
EOF

# Run with Gunicorn
export BOT_TOKEN="your_bot_token_here"
export WEBHOOK_URL="https://yourdomain.com/webhook"
gunicorn -w 4 -b 0.0.0.0:8443 wsgi:application
```

### Using systemd service
```bash
# Create service file
sudo tee /etc/systemd/system/archive-bot.service << 'EOF'
[Unit]
Description=Telegram Archive Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
Environment=BOT_TOKEN=your_bot_token_here
Environment=WEBHOOK_URL=https://yourdomain.com/webhook
ExecStart=/usr/bin/python3 webhook_archive_bot.py $BOT_TOKEN $WEBHOOK_URL
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable archive-bot
sudo systemctl start archive-bot
sudo systemctl status archive-bot
```

### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY webhook_archive_bot.py .
COPY processed_messages.json .

EXPOSE 8443

CMD ["python", "webhook_archive_bot.py"]
```

```bash
# Build and run
docker build -t archive-bot .
docker run -d -p 8443:8443 \
  -e BOT_TOKEN="your_token" \
  -e WEBHOOK_URL="https://yourdomain.com/webhook" \
  archive-bot
```

## Nginx Configuration

If using nginx as reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /webhook {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring

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
# If using systemd
sudo journalctl -u archive-bot -f

# If running directly
tail -f bot.log
```

## Troubleshooting

### Common Issues

1. **Webhook not receiving updates**
   - Check SSL certificate is valid
   - Verify webhook URL is accessible from internet
   - Check Telegram webhook status: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

2. **Bot not responding**
   - Check bot is mentioned correctly: `@Angel_Dimi_Bot`
   - Verify bot has permission to send messages
   - Check server logs for errors

3. **Archive.ph issues**
   - Some URLs may not be archivable
   - Rate limiting may occur
   - Fallback URLs are always provided

### Debug Mode
```bash
# Run with debug logging
python webhook_archive_bot.py YOUR_TOKEN YOUR_WEBHOOK_URL --debug
```

## Security Notes

- Keep bot token secret
- Use HTTPS only
- Consider rate limiting
- Monitor for abuse
- Regularly update dependencies

## Environment Variables

```bash
export BOT_TOKEN="123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
export WEBHOOK_URL="https://yourdomain.com/webhook"
export PORT="8443"  # Optional, defaults to 8443
```