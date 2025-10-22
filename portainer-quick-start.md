# Portainer Quick Start - 5 Minutes to Deploy

Ultra-quick deployment guide for the impatient! 🚀

## ⚡ Prerequisites (2 minutes)

1. **Portainer running** on your server
2. **Domain ready**: `dimibot.coolphill.com` → your server IP
3. **Bot token**: `your_bot_token_here`

## 🎯 Deploy in 3 Steps (3 minutes)

### Step 1: Create Stack (1 minute)
1. **Open Portainer** → Stacks → Add stack
2. **Name**: `dimibot`
3. **Web editor**: Copy this YAML:

```yaml
version: '3.8'
services:
  dimibot:
    image: python:3.11-slim
    container_name: dimibot
    restart: unless-stopped
    ports:
      - "8443:8443"
    environment:
      - BOT_TOKEN=your_bot_token_here
      - WEBHOOK_URL=https://dimibot.coolphill.com/webhook
    volumes:
      - dimibot_data:/app/data
    working_dir: /app
    command: >
      bash -c "
      apt-get update && apt-get install -y curl &&
      pip install flask requests &&
      cat > bot.py << 'EOF'
      import os, re, requests, json, threading
      from datetime import datetime
      from flask import Flask, request, jsonify
      
      app = Flask(__name__)
      BOT_TOKEN = os.environ['BOT_TOKEN']
      WEBHOOK_URL = os.environ['WEBHOOK_URL']
      API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
      
      def extract_urls(text):
          if not text: return []
          urls = re.findall(r'http[s]?://[^\s]+', text)
          www_urls = re.findall(r'(?:^|\s)(www\.[^\s]+)', text)
          return urls + [f'https://{url.strip()}' for url in www_urls]
      
      def archive_url(url):
          if not url.startswith(('http://', 'https://')): url = f'https://{url}'
          year = datetime.now().year
          return f'https://archive.ph/{year}/{url}'
      
      def send_message(chat_id, text, reply_to=None):
          data = {'chat_id': chat_id, 'text': text}
          if reply_to: data['reply_to_message_id'] = reply_to
          requests.post(f'{API_URL}/sendMessage', json=data)
      
      def process_message(update):
          msg = update.get('message', {})
          text = msg.get('text', '')
          if '@angel_dimi_bot' not in text.lower(): return
          
          chat_id = msg.get('chat', {}).get('id')
          msg_id = msg.get('message_id')
          sender = msg.get('from', {}).get('first_name', 'User')
          
          urls = extract_urls(text)
          if not urls:
              send_message(chat_id, f'@{sender} No URLs found!', msg_id)
              return
          
          results = []
          for url in urls:
              archive = archive_url(url)
              results.append(f'📁 {url}\n   → {archive}')
          
          reply = f'@{sender} Here are your archived links:\n\n' + '\n\n'.join(results)
          send_message(chat_id, reply, msg_id)
      
      @app.route('/webhook', methods=['POST'])
      def webhook():
          update = request.get_json()
          if update: threading.Thread(target=process_message, args=(update,)).start()
          return jsonify({'status': 'ok'})
      
      @app.route('/health')
      def health():
          return jsonify({'status': 'healthy', 'bot': 'Angel_Dimi_Bot'})
      
      @app.route('/')
      def root():
          return jsonify({'service': 'Archive Bot', 'status': 'running'})
      
      if __name__ == '__main__':
          # Set webhook
          requests.post(f'{API_URL}/setWebhook', json={'url': WEBHOOK_URL})
          print(f'🤖 Bot starting on port 8443')
          print(f'📡 Webhook: {WEBHOOK_URL}')
          app.run(host='0.0.0.0', port=8443)
      EOF
      python bot.py
      "
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8443/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  dimibot_data:
```

### Step 2: Deploy (30 seconds)
1. **Click "Deploy the stack"**
2. **Wait for green status**

### Step 3: Setup SSL (1.5 minutes)
```bash
# On your server
sudo apt install nginx certbot python3-certbot-nginx -y

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
    location / {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/dimibot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d dimibot.coolphill.com --non-interactive --agree-tos --email your@email.com
```

## ✅ Test (30 seconds)

1. **Health check**: `curl https://dimibot.coolphill.com/health`
2. **Add bot to chat**: Search `@Angel_Dimi_Bot`
3. **Test**: Send `@Angel_Dimi_Bot archive https://reddit.com`
4. **Get instant reply** with archive link!

## 🎉 Done!

Your bot is now running and will respond to mentions in any chat with archive links!

## 📊 Monitor in Portainer

- **Containers** → `dimibot` → View logs
- **Health status** should be green
- **Resource usage** visible in stats

## 🔧 Quick Fixes

### Bot not responding?
```bash
# Check logs in Portainer
# Or restart container: Containers → dimibot → Restart
```

### SSL issues?
```bash
sudo certbot renew --dry-run
sudo nginx -t
```

### Update bot?
1. **Stacks** → `dimibot` → **Editor**
2. **Modify code** in the YAML
3. **Update the stack**

That's it! Your archive bot is live at `dimibot.coolphill.com` 🚀