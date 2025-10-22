#!/bin/bash
# Docker deployment script for Archive Bot

set -e

echo "🐳 Deploying Telegram Archive Bot with Docker"
echo "============================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your bot token before running!"
    echo "   BOT_TOKEN=your_bot_token_here"
    echo "   WEBHOOK_URL=https://dimibot.coolphill.com/webhook"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t dimibot:latest .

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker stop dimibot 2>/dev/null || true
docker rm dimibot 2>/dev/null || true

# Run the container
echo "🚀 Starting container..."
docker-compose up -d

# Wait a moment for startup
sleep 5

# Check container status
echo "📊 Container status:"
docker ps | grep dimibot

# Check logs
echo "📋 Recent logs:"
docker logs dimibot --tail 20

# Test health endpoint
echo "🏥 Testing health endpoint..."
sleep 2
if curl -s http://localhost:8443/health | grep -q "healthy"; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed"
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Container info:"
echo "  Name: dimibot"
echo "  Port: 8443"
echo "  URL: https://dimibot.coolphill.com"
echo ""
echo "🛠️  Management commands:"
echo "  View logs:    docker logs dimibot -f"
echo "  Restart:      docker-compose restart"
echo "  Stop:         docker-compose down"
echo "  Rebuild:      docker-compose up --build -d"
echo ""
echo "🔧 Make sure to:"
echo "  1. Point dimibot.coolphill.com to this server"
echo "  2. Set up SSL/TLS termination (nginx/traefik)"
echo "  3. Test the bot by mentioning @Angel_Dimi_Bot"