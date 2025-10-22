#!/bin/bash
# Deployment script for Webhook Archive Bot

set -e

echo "🚀 Deploying Telegram Archive Bot with Webhooks"
echo "=============================================="

# Check if bot token and webhook URL are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <bot_token> <webhook_url> [port]"
    echo "Example: $0 123456:ABC-DEF https://yourdomain.com/webhook 8443"
    exit 1
fi

BOT_TOKEN="$1"
WEBHOOK_URL="$2"
PORT="${3:-8443}"

echo "📋 Configuration:"
echo "  Bot Token: ${BOT_TOKEN:0:10}..."
echo "  Webhook URL: $WEBHOOK_URL"
echo "  Port: $PORT"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Test webhook URL accessibility
echo "🔍 Testing webhook URL accessibility..."
if curl -s --head "$WEBHOOK_URL" | head -n 1 | grep -q "200 OK\|404"; then
    echo "✅ Webhook URL is accessible"
else
    echo "⚠️  Warning: Webhook URL may not be accessible"
fi

# Create systemd service file
echo "⚙️  Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/archive-bot.service"

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Telegram Archive Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=BOT_TOKEN=$BOT_TOKEN
Environment=WEBHOOK_URL=$WEBHOOK_URL
Environment=PORT=$PORT
ExecStart=$(which python3) webhook_archive_bot.py $BOT_TOKEN $WEBHOOK_URL $PORT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "🔄 Configuring systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable archive-bot

# Start the service
echo "🚀 Starting archive bot service..."
sudo systemctl start archive-bot

# Check status
echo "📊 Service status:"
sudo systemctl status archive-bot --no-pager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Check logs: sudo journalctl -u archive-bot -f"
echo "  2. Test the bot by mentioning @Angel_Dimi_Bot with a URL"
echo "  3. Monitor health: curl $WEBHOOK_URL/../health"
echo ""
echo "🛠️  Management commands:"
echo "  Start:   sudo systemctl start archive-bot"
echo "  Stop:    sudo systemctl stop archive-bot"
echo "  Restart: sudo systemctl restart archive-bot"
echo "  Logs:    sudo journalctl -u archive-bot -f"