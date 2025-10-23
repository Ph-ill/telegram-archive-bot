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
import random
import glob
from datetime import datetime, date
from flask import Flask, request, jsonify
import threading
import pytz
from dateutil.relativedelta import relativedelta
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
    
    # Birthday functionality
    def load_birthdays(self):
        """Load birthday data from JSON file"""
        birthday_file = os.path.join(self.data_dir, "birthdays.json")
        try:
            with open(birthday_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading birthdays: {e}")
            return {}
    
    def save_birthdays(self, birthdays):
        """Save birthday data to JSON file"""
        birthday_file = os.path.join(self.data_dir, "birthdays.json")
        try:
            os.makedirs(os.path.dirname(birthday_file), exist_ok=True)
            with open(birthday_file, 'w') as f:
                json.dump(birthdays, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving birthdays: {e}")
    
    def is_user_authorized(self, sender_username, target_username):
        """Check if user is authorized to set birthday for target username"""
        # Special users can modify any birthday (case insensitive)
        special_users = ["racistwaluigi", "kokorozasu"]
        if sender_username.lower() in special_users:
            return True, "admin"
        
        # Any user can set their own birthday (case insensitive)
        if sender_username.lower() == target_username.lower():
            return True, "self"
        
        return False, "unauthorized"
    
    def parse_birthday_command(self, text, sender_username=None, sender_id=None):
        """Parse birthday set command"""
        # Try format with username: @Angel_Dimi_Bot birthday set 1990-03-15 America/New_York myusername
        pattern_with_username = r'birthday\s+set\s+(\d{4}-\d{2}-\d{2})\s+([^\s]+)\s+@?(\w+)'
        match_with_username = re.search(pattern_with_username, text, re.IGNORECASE)
        
        # Try format without username: @Angel_Dimi_Bot birthday set 1990-03-15 America/New_York
        pattern_without_username = r'birthday\s+set\s+(\d{4}-\d{2}-\d{2})\s+([^\s]+)(?:\s|$)'
        match_without_username = re.search(pattern_without_username, text, re.IGNORECASE)
        
        if match_with_username:
            date_str, timezone_str, username = match_with_username.groups()
        elif match_without_username:
            date_str, timezone_str = match_without_username.groups()
            # Use sender's username or ID as fallback
            username = sender_username or f"user_{sender_id}"
        else:
            return None, "Invalid format. Use:\n`@Angel_Dimi_Bot birthday set YYYY-MM-DD Timezone [username]`\n\nExamples:\n• `@Angel_Dimi_Bot birthday set 1990-03-15 America/New_York` (uses your username/ID)\n• `@Angel_Dimi_Bot birthday set 1990-03-15 America/New_York john` (sets for specific user)"
        
        # Validate date format
        try:
            birth_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, "Invalid date format. Use YYYY-MM-DD format.\nExample: 1990-03-15"
        
        # Validate timezone
        try:
            pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            return None, f"Invalid timezone '{timezone_str}'. See valid timezones at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        
        return {
            'date': date_str,
            'timezone': timezone_str,
            'username': username
        }, None
    
    def parse_delete_birthday_command(self, text):
        """Parse delete birthday command"""
        # Expected format: @Angel_Dimi_Bot delete_birthday @username
        pattern = r'delete_birthday\s+@?(\w+)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if not match:
            return None
        
        username = match.group(1)
        return username
    
    def calculate_age(self, birth_date_str):
        """Calculate current age from birth date"""
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - birth_date.year
        if today < birth_date.replace(year=today.year):
            age -= 1
        return age
    
    def get_random_birthday_image(self):
        """Get a random birthday image from the birthday_images folder"""
        try:
            image_folder = os.path.join(os.path.dirname(__file__), 'birthday_images')
            if not os.path.exists(image_folder):
                logger.warning("birthday_images folder not found")
                return None
            
            # Get all gif files
            gif_files = glob.glob(os.path.join(image_folder, '*.gif'))
            if not gif_files:
                logger.warning("No gif files found in birthday_images folder")
                return None
            
            return random.choice(gif_files)
        except Exception as e:
            logger.error(f"Error getting birthday image: {e}")
            return None
    
    def send_birthday_message(self, username, age, chat_id=-1002220894500):
        """Send birthday message to group chat"""
        try:
            message = f"🎈 It's @{username}'s birthday today! They're turning {age}! 🎉 Celebrate! 🎂"
            
            # Get random birthday image
            image_path = self.get_random_birthday_image()
            
            if image_path:
                # Send with image
                import requests
                url = f"{self.telegram_api_url}/sendAnimation"
                
                with open(image_path, 'rb') as gif_file:
                    files = {'animation': gif_file}
                    data = {
                        'chat_id': chat_id,
                        'caption': message
                    }
                    response = requests.post(url, files=files, data=data, timeout=30)
            else:
                # Send text only
                self.send_message(chat_id, message)
            
            logger.info(f"Birthday message sent for {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending birthday message: {e}")
            return False
    
    def process_birthday_command(self, text, sender_name, sender_username, sender_id, chat_id):
        """Process birthday-related commands"""
        if "birthday set" in text.lower():
            # Parse command first
            birthday_data, error = self.parse_birthday_command(text, sender_username, sender_id)
            if error:
                return f"@{sender_name} {error}"
            
            target_username = birthday_data['username']
            
            # Check authorization
            is_authorized, auth_type = self.is_user_authorized(sender_username, target_username)
            if not is_authorized:
                return f"@{sender_name} You can only set your own birthday. To set birthday for @{target_username}, ask @RacistWaluigi or @kokorozasu to do it."
            
            # Load existing birthdays
            birthdays = self.load_birthdays()
            
            # Check if user already exists
            if target_username in birthdays:
                existing = birthdays[target_username]
                existing_age = self.calculate_age(existing['date'])
                return f"@{sender_name} User @{target_username} already exists:\nBirthday: {existing['date']}\nTimezone: {existing['timezone']}\nCurrent age: {existing_age}\n\nReply with 'y' to replace this information."
            
            # Save new birthday
            birthdays[target_username] = birthday_data
            self.save_birthdays(birthdays)
            
            age = self.calculate_age(birthday_data['date'])
            
            if auth_type == "self":
                return f"@{sender_name} ✅ Your birthday has been saved!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}"
            else:
                return f"@{sender_name} ✅ Birthday saved for @{target_username}!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}"
        
        elif "delete_birthday" in text.lower():
            # Only special users can delete birthdays
            special_users = ["racistwaluigi", "kokorozasu"]
            if sender_username.lower() not in special_users:
                return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can delete birthdays."
            
            # Parse delete command
            delete_result = self.parse_delete_birthday_command(text)
            if delete_result is None:
                return f"@{sender_name} Invalid format. Use: `@Angel_Dimi_Bot delete_birthday @username`\nExample: `@Angel_Dimi_Bot delete_birthday @john`"
            
            username_to_delete = delete_result
            
            # Load existing birthdays
            birthdays = self.load_birthdays()
            
            # Check if user exists
            if username_to_delete not in birthdays:
                return f"@{sender_name} User @{username_to_delete} not found in birthday database."
            
            # Show existing data before deletion
            existing = birthdays[username_to_delete]
            existing_age = self.calculate_age(existing['date'])
            
            # Delete the birthday
            del birthdays[username_to_delete]
            self.save_birthdays(birthdays)
            
            return f"@{sender_name} ✅ Birthday deleted for @{username_to_delete}!\nDeleted data:\nBirthday: {existing['date']}\nTimezone: {existing['timezone']}\nAge: {existing_age}"
        
        elif "list_birthdays" in text.lower():
            # Only special users can list all birthdays
            special_users = ["racistwaluigi", "kokorozasu"]
            if sender_username.lower() not in special_users:
                return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can list all birthdays."
            
            # Load existing birthdays
            birthdays = self.load_birthdays()
            
            if not birthdays:
                return f"@{sender_name} No birthdays stored in the database."
            
            # Sort birthdays chronologically (by month and day)
            def get_birthday_sort_key(item):
                username, data = item
                birth_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                # Use month and day for chronological sorting (ignore year)
                return (birth_date.month, birth_date.day)
            
            sorted_birthdays = sorted(birthdays.items(), key=get_birthday_sort_key)
            
            # Format birthday list (without @ to avoid pinging users)
            birthday_list = []
            for username, data in sorted_birthdays:
                age = self.calculate_age(data['date'])
                birth_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                formatted_date = birth_date.strftime('%B %d, %Y')  # e.g., "March 15, 1990"
                birthday_list.append(f"{username}: {formatted_date} ({data['timezone']}) - Age: {age}")
            
            total_count = len(birthdays)
            header = f"@{sender_name} 📋 Birthday Database ({total_count} users):\n\n"
            
            return header + "\n".join(birthday_list)
        
        elif "test_birthday" in text.lower():
            # Send test birthday message to current chat
            return self.send_test_birthday_message(chat_id)
        
        return None
    
    def get_help_message(self, sender_name, sender_username):
        """Generate help message with available commands"""
        special_users = ["racistwaluigi", "kokorozasu"]
        is_special_user = sender_username.lower() in special_users
        
        help_text = f"@{sender_name} 🤖 **Angel Dimi Bot Commands:**\n\n"
        
        # Archive commands (available to everyone)
        help_text += "📁 **Archive Commands:**\n"
        help_text += "• `@Angel_Dimi_Bot archive <URL>` - Archive a link\n"
        help_text += "  Example: `@Angel_Dimi_Bot archive https://example.com`\n\n"
        
        # Birthday commands (available to everyone for self)
        help_text += "🎂 **Birthday Commands:**\n"
        help_text += "• `@Angel_Dimi_Bot birthday set YYYY-MM-DD Timezone [username]`\n"
        help_text += "  Set birthday (omit username to set your own)\n"
        help_text += "  Example: `@Angel_Dimi_Bot birthday set 1990-03-15 America/New_York`\n"
        help_text += "• `@Angel_Dimi_Bot test_birthday` - Send test birthday message\n\n"
        
        # Special user commands
        if is_special_user:
            help_text += "👑 **Admin Commands** (Special Users Only):\n"
            help_text += "• `@Angel_Dimi_Bot delete_birthday @username` - Delete a birthday\n"
            help_text += "• `@Angel_Dimi_Bot list_birthdays` - List all stored birthdays\n"
            help_text += "• Can set birthdays for any user\n\n"
        
        # Help commands
        help_text += "ℹ️ **Help Commands:**\n"
        help_text += "• `@Angel_Dimi_Bot help` - Show this help message\n"
        help_text += "• `@Angel_Dimi_Bot list` - Show available commands\n"
        help_text += "• `@Angel_Dimi_Bot /` - Show command summary\n\n"
        
        # Additional info
        help_text += "📝 **Notes:**\n"
        help_text += "• Works in groups and private messages\n"
        help_text += "• Birthday alerts sent to group at midnight in your timezone\n"
        help_text += "• Timezone list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        
        return help_text
    
    def send_test_birthday_message(self, chat_id):
        """Send test birthday message for @RacistWaluigi"""
        try:
            age = 25  # Test age
            message = f"🎈 It's @RacistWaluigi's birthday today! They're turning {age}! 🎉 Celebrate! 🎂"
            
            # Get random birthday image
            image_path = self.get_random_birthday_image()
            
            if image_path:
                # Send with image
                import requests
                url = f"{self.telegram_api_url}/sendAnimation"
                
                with open(image_path, 'rb') as gif_file:
                    files = {'animation': gif_file}
                    data = {
                        'chat_id': chat_id,
                        'caption': f"🧪 TEST BIRTHDAY MESSAGE:\n\n{message}"
                    }
                    response = requests.post(url, files=files, data=data, timeout=30)
                    
                    if response.status_code == 200:
                        return "✅ Test birthday message sent!"
                    else:
                        return f"❌ Failed to send test message: {response.text}"
            else:
                # Send text only
                test_message = f"🧪 TEST BIRTHDAY MESSAGE:\n\n{message}"
                success = self.send_message(chat_id, test_message)
                return "✅ Test birthday message sent!" if success else "❌ Failed to send test message"
                
        except Exception as e:
            logger.error(f"Error sending test birthday message: {e}")
            return f"❌ Error sending test message: {str(e)}"
    
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
    
    def process_message_for_archives(self, text, sender_name="User", sender_id=None, chat_id=None):
        """Process message for archive requests and other commands"""
        if not self.is_bot_mentioned(text):
            return None
        
        # Check for help commands first
        if any(cmd in text.lower() for cmd in ["help", "list", "/"]) and len(text.strip()) < 50:
            return self.get_help_message(sender_name, sender_username)
        
        # Check for birthday commands
        if "birthday" in text.lower() or "test_birthday" in text.lower() or "delete_birthday" in text.lower() or "list_birthdays" in text.lower():
            return self.process_birthday_command(text, sender_name, sender_username, sender_id, chat_id)
        
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
            sender_id = sender.get('id')
            sender_username = sender.get('username')
            # If no username, use user_ID format for identification
            if not sender_username:
                sender_username = f"user_{sender_id}"
            
            # Create unique message identifier
            msg_key = f"{chat_id}_{message_id}"
            
            # Skip if already processed
            if msg_key in self.processed_messages:
                logger.debug(f"Message {msg_key} already processed, skipping")
                return
            
            # Process if bot is mentioned
            reply_text = self.process_message_for_archives(text, sender_name, sender_username, chat_id)
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