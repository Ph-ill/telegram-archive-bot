#!/usr/bin/env python3
"""
Selenium-based Archive Bot - Actually creates new archives by automating browser
"""

import re
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from flask import Flask, request, jsonify
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

def setup_logging():
    """Setup logging with proper error handling"""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    try:
        log_dir = '/app/logs'
        if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
            handlers.append(logging.FileHandler(os.path.join(log_dir, 'bot.log')))
        elif os.path.exists('/app/data') and os.access('/app/data', os.W_OK):
            handlers.append(logging.FileHandler('/app/data/bot.log'))
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

setup_logging()
logger = logging.getLogger(__name__)

class SeleniumArchiveBot:
    def __init__(self):
        # Get configuration from environment variables
        self.bot_token = os.environ.get('BOT_TOKEN')
        self.webhook_url = os.environ.get('WEBHOOK_URL')
        self.port = int(os.environ.get('PORT', 8443))
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        if not self.webhook_url:
            raise ValueError("WEBHOOK_URL environment variable is required")
        
        self.bot_username = "Angel_Dimi_Bot"
        self.telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Use persistent storage if available
        self.data_dir = '/app/data' if os.path.exists('/app/data') else '/app'
        self.processed_file = os.path.join(self.data_dir, "processed_messages.json")
        self.processed_messages = self.load_processed_messages()
        
        # Flask app for webhook
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Graceful shutdown handling
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logger.info(f"Bot initialized - Token: {self.bot_token[:10]}..., Webhook: {self.webhook_url}")
    
    def signal_handler(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.delete_webhook()
        self.save_processed_messages()
        sys.exit(0)
    
    def load_processed_messages(self):
        """Load previously processed message IDs"""
        try:
            with open(self.processed_file, 'r') as f:
                messages = set(json.load(f))
                logger.info(f"Loaded {len(messages)} processed messages")
                return messages
        except FileNotFoundError:
            logger.info("No previous processed messages found, starting fresh")
            return set()
        except Exception as e:
            logger.error(f"Error loading processed messages: {e}")
            return set()
    
    def save_processed_messages(self):
        """Save processed message IDs"""
        try:
            os.makedirs(os.path.dirname(self.processed_file), exist_ok=True)
            with open(self.processed_file, 'w') as f:
                json.dump(list(self.processed_messages), f)
            logger.debug(f"Saved {len(self.processed_messages)} processed messages")
        except Exception as e:
            logger.error(f"Error saving processed messages: {e}")
    
    def extract_urls(self, text):
        """Extract URLs from text"""
        if not text:
            return []
        
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        
        www_pattern = r'(?:^|\s)(www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),])+)'
        www_matches = re.findall(www_pattern, text)
        
        for www_url in www_matches:
            urls.append(f"https://{www_url.strip()}")
        
        return list(set(urls))
    
    def is_bot_mentioned(self, text):
        """Check if bot is mentioned"""
        if not text:
            return False
        return f"@{self.bot_username.lower()}" in text.lower()
    
    def create_driver(self):
        """Create a headless Chrome driver"""
        try:
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            chrome_options.add_argument("--remote-debugging-port=9222")
            
            # Let Selenium automatically manage ChromeDriver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            return None
    
    def archive_url_with_selenium(self, url):
        """Archive a URL by automating the archive.ph interface"""
        driver = None
        try:
            logger.info(f"Creating new archive for: {url}")
            
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Create driver
            driver = self.create_driver()
            if not driver:
                logger.error("Could not create browser driver")
                return None
            
            # Navigate to archive.ph with pre-filled URL
            archive_url = f"https://archive.ph/?url={url}"
            logger.info(f"Navigating to: {archive_url}")
            driver.get(archive_url)
            
            # Wait for page to load and find the save button
            wait = WebDriverWait(driver, 10)
            
            # Look for the save/submit button - try different selectors
            save_button = None
            button_selectors = [
                "input[type='submit']",
                "button[type='submit']", 
                "input[value*='Save']",
                "button:contains('Save')",
                "#submiturl",
                ".btn-primary",
                "[onclick*='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    logger.info(f"Found save button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not save_button:
                logger.error("Could not find save button on archive.ph")
                return None
            
            # Click the save button
            logger.info("Clicking save button...")
            save_button.click()
            
            # Wait for redirect to archived page
            wait = WebDriverWait(driver, 30)  # Archive creation can take time
            
            # Wait for URL to change to archived page format
            def url_changed_to_archive(driver):
                current_url = driver.current_url
                return (current_url != archive_url and 
                       'archive.ph/' in current_url and 
                       current_url != 'https://archive.ph/')
            
            wait.until(url_changed_to_archive)
            
            # Get the final archived URL
            archived_url = driver.current_url
            logger.info(f"✅ Successfully created archive: {archived_url}")
            
            return archived_url
            
        except TimeoutException:
            logger.error(f"Timeout while archiving {url}")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriver error while archiving {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while archiving {url}: {e}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def process_message_for_archives(self, text, sender_name="User"):
        """Process message and return archive reply"""
        if not self.is_bot_mentioned(text):
            return None
        
        # Check if message contains the word "archive" (case insensitive)
        if "archive" not in text.lower():
            return None
        
        logger.info(f"Processing archive request from {sender_name}")
        
        urls = self.extract_urls(text)
        if not urls:
            return f"@{sender_name} I found the word 'archive' but no URLs to archive in your message."
        
        archived_results = []
        for url in urls:
            logger.info(f"Starting archive process for: {url}")
            archived_url = self.archive_url_with_selenium(url)
            if archived_url:
                archived_results.append(f"📁 {archived_url}")
            else:
                # Fallback to year-based URL if Selenium fails
                current_year = datetime.now().year
                fallback_url = f"https://archive.ph/{current_year}/{url}"
                archived_results.append(f"⚠️ {fallback_url} (fallback - may not exist)")
        
        # Use singular/plural based on number of URLs
        if len(urls) == 1:
            return f"@{sender_name} Here is your archived link:\n\n" + "\n\n".join(archived_results)
        else:
            return f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
    
    def send_message(self, chat_id, text, reply_to_message_id=None):
        """Send message via Telegram Bot API"""
        try:
            import requests
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            if reply_to_message_id:
                data['reply_to_message_id'] = reply_to_message_id
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def process_webhook_update(self, update):
        """Process incoming webhook update"""
        try:
            # Extract message info
            message = update.get('message')
            if not message:
                return
            
            message_id = message.get('message_id')
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            sender = message.get('from', {})
            sender_name = sender.get('first_name', 'User')
            
            # Create unique message identifier
            msg_key = f"{chat_id}_{message_id}"
            
            # Skip if already processed
            if msg_key in self.processed_messages:
                logger.debug(f"Message {msg_key} already processed, skipping")
                return
            
            # Process if bot is mentioned
            reply_text = self.process_message_for_archives(text, sender_name)
            if reply_text:
                # Mark as processed
                self.processed_messages.add(msg_key)
                
                # Send reply
                success = self.send_message(chat_id, reply_text, message_id)
                if success:
                    logger.info(f"Successfully processed and replied to message {msg_key}")
                    # Save processed messages periodically
                    if len(self.processed_messages) % 10 == 0:
                        self.save_processed_messages()
                else:
                    logger.error(f"Failed to send reply for message {msg_key}")
            
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
    
    def setup_routes(self):
        """Set up Flask routes for webhook"""
        
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle incoming webhook updates"""
            try:
                update = request.get_json()
                if update:
                    # Process update in background thread to avoid blocking
                    threading.Thread(target=self.process_webhook_update, args=(update,)).start()
                
                return jsonify({'status': 'ok'})
                
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'bot': self.bot_username,
                'timestamp': datetime.now().isoformat(),
                'processed_messages': len(self.processed_messages),
                'selenium_enabled': True
            })
        
        @self.app.route('/stats', methods=['GET'])
        def stats():
            """Bot statistics"""
            return jsonify({
                'processed_messages': len(self.processed_messages),
                'bot_username': self.bot_username,
                'webhook_url': self.webhook_url,
                'uptime': datetime.now().isoformat(),
                'selenium_enabled': True
            })
        
        @self.app.route('/', methods=['GET'])
        def root():
            """Root endpoint"""
            return jsonify({
                'service': 'Telegram Archive Bot with Selenium',
                'status': 'running',
                'bot': self.bot_username
            })
    
    def set_webhook(self):
        """Set the webhook URL with Telegram"""
        try:
            import requests
            url = f"{self.telegram_api_url}/setWebhook"
            data = {'url': self.webhook_url}
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"Webhook set successfully: {self.webhook_url}")
                    return True
                else:
                    logger.error(f"Failed to set webhook: {result}")
                    return False
            else:
                logger.error(f"HTTP error setting webhook: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False
    
    def delete_webhook(self):
        """Delete the webhook"""
        try:
            import requests
            url = f"{self.telegram_api_url}/deleteWebhook"
            response = requests.post(url, timeout=30)
            
            if response.status_code == 200:
                logger.info("Webhook deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete webhook: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
    
    def run(self):
        """Run the webhook server"""
        logger.info(f"Starting Selenium-powered webhook server on 0.0.0.0:{self.port}")
        logger.info(f"Webhook URL: {self.webhook_url}")
        
        # Set webhook with Telegram
        if self.set_webhook():
            logger.info("Webhook configured successfully")
        else:
            logger.error("Failed to configure webhook")
            return
        
        try:
            # Run Flask app
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.delete_webhook()
            self.save_processed_messages()

def main():
    """Main function"""
    try:
        bot = SeleniumArchiveBot()
        logger.info("🤖 Starting Selenium Archive Bot")
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()