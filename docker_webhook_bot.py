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
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        if not self.webhook_url:
            raise ValueError("WEBHOOK_URL environment variable is required")
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY environment variable not set - quiz functionality will be disabled")
        
        self.telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Get bot username dynamically from Telegram API
        self.bot_username = self.get_bot_username()
        
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
        
        logger.info(f"Bot initialized - Username: @{self.bot_username}, Token: {self.bot_token[:10]}..., Webhook: {self.webhook_url}")
        
        # Start birthday monitoring system
        self.start_birthday_monitor()
        
        # Initialize quiz manager if API key is available
        self.quiz_manager = None
        logger.info(f"Checking GEMINI_API_KEY: {'SET' if self.gemini_api_key else 'NOT SET'}")
        
        if self.gemini_api_key:
            try:
                logger.info("Attempting to import QuizManager...")
                from quiz.quiz_manager import QuizManager
                logger.info("QuizManager imported successfully, initializing...")
                self.quiz_manager = QuizManager(self, self.data_dir, self.gemini_api_key)
                logger.info("Quiz manager initialized successfully")
            except ImportError as e:
                logger.error(f"Failed to import quiz module: {e}")
                self.quiz_manager = None
            except Exception as e:
                logger.error(f"Failed to initialize quiz manager: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.quiz_manager = None
        else:
            logger.info("Quiz functionality disabled - GEMINI_API_KEY not provided")
    
    def get_bot_username(self):
        """Get bot username from Telegram API"""
        try:
            import requests
            url = f"{self.telegram_api_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    username = data['result'].get('username', 'Unknown_Bot')
                    logger.info(f"Bot username retrieved: @{username}")
                    return username
            
            logger.warning("Failed to get bot username from API, using fallback")
            return "Angel_Dimi_Bot"  # Fallback
            
        except Exception as e:
            logger.error(f"Error getting bot username: {e}")
            return "Angel_Dimi_Bot"  # Fallback
    
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
            return None, f"<blockquote expandable>Invalid format. Use:\n@{self.bot_username} birthday set YYYY-MM-DD Timezone [username]\n\nExamples:\n• @{self.bot_username} birthday set 1990-03-15 America/New_York (uses your username/ID)\n• @{self.bot_username} birthday set 1990-03-15 America/New_York john (sets for specific user)</blockquote>"
        
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
            
            # Get all image files (GIFs, PNGs, JPGs, etc.)
            image_extensions = ['*.gif', '*.png', '*.jpg', '*.jpeg', '*.webp']
            image_files = []
            for extension in image_extensions:
                image_files.extend(glob.glob(os.path.join(image_folder, extension)))
                image_files.extend(glob.glob(os.path.join(image_folder, extension.upper())))
            
            if not image_files:
                logger.warning("No image files found in birthday_images folder")
                return None
            
            return random.choice(image_files)
        except Exception as e:
            logger.error(f"Error getting birthday image: {e}")
            return None
    
    def load_birthday_messages(self):
        """Load birthday messages from JSON file"""
        messages_file = os.path.join(self.data_dir, "birthday_messages.json")
        try:
            with open(messages_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default structure if file doesn't exist
            return {
                "random_messages": [
                    "🎈 It's @{username}'s birthday today! They're turning {age}! 🎉 Celebrate! 🎂",
                    "🎂 Happy Birthday @{username}! Welcome to {age}! 🎉🎈",
                    "🎉 @{username} is {age} today! Time to party! 🎂🎈"
                ],
                "user_specific": {}
            }
        except Exception as e:
            logger.error(f"Error loading birthday messages: {e}")
            return {"random_messages": [], "user_specific": {}}
    
    def save_birthday_messages(self, messages):
        """Save birthday messages to JSON file"""
        messages_file = os.path.join(self.data_dir, "birthday_messages.json")
        try:
            os.makedirs(os.path.dirname(messages_file), exist_ok=True)
            with open(messages_file, 'w') as f:
                json.dump(messages, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving birthday messages: {e}")
    
    def get_birthday_message(self, username, age):
        """Get appropriate birthday message for user"""
        try:
            messages = self.load_birthday_messages()
            
            # Check for user-specific message first
            if username.lower() in messages.get("user_specific", {}):
                message_template = messages["user_specific"][username.lower()]
                return message_template.format(username=username, age=age)
            
            # Use random message if no user-specific message
            random_messages = messages.get("random_messages", [])
            if random_messages:
                message_template = random.choice(random_messages)
                return message_template.format(username=username, age=age)
            
            # Fallback message if no messages configured
            return f"🎈 It's @{username}'s birthday today! They're turning {age}! 🎉 Celebrate! 🎂"
            
        except Exception as e:
            logger.error(f"Error getting birthday message: {e}")
            return f"🎈 It's @{username}'s birthday today! They're turning {age}! 🎉 Celebrate! 🎂"
    
    def send_birthday_message(self, username, age, chat_id=-1002220894500):
        """Send birthday message to group chat"""
        try:
            message = self.get_birthday_message(username, age)
            
            # Get random birthday image
            image_path = self.get_random_birthday_image()
            
            if image_path:
                # Send with image
                import requests
                
                # Determine if it's an animated image (GIF) or static image
                file_extension = os.path.splitext(image_path)[1].lower()
                
                if file_extension == '.gif':
                    # Use sendAnimation for GIFs
                    url = f"{self.telegram_api_url}/sendAnimation"
                    with open(image_path, 'rb') as image_file:
                        files = {'animation': image_file}
                        data = {
                            'chat_id': chat_id,
                            'caption': message
                        }
                        response = requests.post(url, files=files, data=data, timeout=30)
                else:
                    # Use sendPhoto for static images (PNG, JPG, etc.)
                    url = f"{self.telegram_api_url}/sendPhoto"
                    with open(image_path, 'rb') as image_file:
                        files = {'photo': image_file}
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
    
    def start_birthday_monitor(self):
        """Start the birthday monitoring background task - checks only at the start of each hour"""
        def birthday_monitor():
            while True:
                try:
                    current_time = datetime.now()
                    
                    # Only check at the start of each hour (when minutes = 0)
                    if current_time.minute == 0:
                        self.check_and_send_birthday_messages()
                        logger.debug(f"Birthday check completed at {current_time.strftime('%H:%M')}")
                    
                    # Calculate seconds until next hour
                    next_hour = current_time.replace(minute=0, second=0, microsecond=0) + relativedelta(hours=1)
                    seconds_until_next_hour = (next_hour - current_time).total_seconds()
                    
                    # Sleep until the next hour (with a small buffer to ensure we don't miss it)
                    time.sleep(max(1, seconds_until_next_hour - 5))
                    
                except Exception as e:
                    logger.error(f"Error in birthday monitor: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying on error
        
        # Start monitor in background thread
        monitor_thread = threading.Thread(target=birthday_monitor, daemon=True)
        monitor_thread.start()
        logger.info("Birthday monitor started - checking at the start of each hour")
    
    def check_and_send_birthday_messages(self):
        """Check if it's midnight in any user's timezone and send birthday messages - only called at hour boundaries"""
        try:
            birthdays = self.load_birthdays()
            if not birthdays:
                return
            
            current_utc = datetime.now(pytz.UTC)
            midnight_found = False
            
            for username, data in birthdays.items():
                try:
                    # Get user's timezone
                    user_tz = pytz.timezone(data['timezone'])
                    user_time = current_utc.astimezone(user_tz)
                    
                    # Only process if it's midnight (00:00) in user's timezone
                    if user_time.hour == 0 and user_time.minute == 0:
                        midnight_found = True
                        # Check if it's their birthday today
                        birth_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                        today = user_time.date()
                        
                        if birth_date.month == today.month and birth_date.day == today.day:
                            # Calculate age
                            age = today.year - birth_date.year
                            if today < birth_date.replace(year=today.year):
                                age -= 1
                            
                            # Send birthday message to the main group chat
                            logger.info(f"Sending automatic birthday message for {username} (age {age})")
                            self.send_birthday_message(username, age, -1002220894500)
                            
                except Exception as e:
                    logger.error(f"Error checking birthday for {username}: {e}")
            
            if not midnight_found:
                logger.debug("No users at midnight currently - birthday check complete")
                    
        except Exception as e:
            logger.error(f"Error in birthday check: {e}")
    
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
            
            # Check if user already exists and show update message
            update_message = ""
            if target_username in birthdays:
                existing = birthdays[target_username]
                existing_age = self.calculate_age(existing['date'])
                update_message = f"\n\n📝 Updated from:\nOld Birthday: {existing['date']}\nOld Timezone: {existing['timezone']}\nOld Age: {existing_age}"
            
            # Save new birthday (always save, whether new or update)
            birthdays[target_username] = birthday_data
            self.save_birthdays(birthdays)
            
            age = self.calculate_age(birthday_data['date'])
            
            if auth_type == "self":
                return f"@{sender_name} <blockquote expandable>✅ Your birthday has been saved!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}</blockquote>"
            else:
                return f"@{sender_name} <blockquote expandable>✅ Birthday saved for @{target_username}!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}</blockquote>"
        
        elif "delete_birthday" in text.lower():
            # Only special users can delete birthdays
            special_users = ["racistwaluigi", "kokorozasu"]
            if sender_username.lower() not in special_users:
                return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can delete birthdays."
            
            # Parse delete command
            delete_result = self.parse_delete_birthday_command(text)
            if delete_result is None:
                return f"@{sender_name} Invalid format. Use: @{self.bot_username} delete_birthday @username\nExample: @{self.bot_username} delete_birthday @john"
            
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
            
            return f"@{sender_name} <blockquote expandable>✅ Birthday deleted for @{username_to_delete}!\nDeleted data:\nBirthday: {existing['date']}\nTimezone: {existing['timezone']}\nAge: {existing_age}</blockquote>"
        
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
        
        elif "add_birthday_message" in text.lower():
            return self.process_add_birthday_message(text, sender_name, sender_username)
        
        elif "list_birthday_messages" in text.lower():
            return self.process_list_birthday_messages(sender_name, sender_username)
        
        elif "delete_birthday_message" in text.lower():
            return self.process_delete_birthday_message(text, sender_name, sender_username)
        
        elif "test_birthday" in text.lower():
            # Send test birthday message to current chat
            return self.send_test_birthday_message(chat_id)
        
        return None
    
    def process_add_birthday_message(self, text, sender_name, sender_username):
        """Process add birthday message command"""
        # Only special users can manage birthday messages
        special_users = ["racistwaluigi", "kokorozasu"]
        if sender_username.lower() not in special_users:
            return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can manage birthday messages."
        
        # Parse command formats:
        # @Angel_Dimi_Bot add_birthday_message random "Happy birthday @{{username}}! You're {{age}} today! 🎉"
        # @Angel_Dimi_Bot add_birthday_message user racistwaluigi "Special birthday message for you @{{username}}! {{age}} years of awesome! 🎂"
        
        import re
        
        # Try random message format
        random_pattern = r'add_birthday_message\s+random\s+"([^"]+)"'
        random_match = re.search(random_pattern, text, re.IGNORECASE)
        
        # Try user-specific message format (handle both @username and username)
        user_pattern = r'add_birthday_message\s+user\s+@?(\w+)\s+"([^"]+)"'
        user_match = re.search(user_pattern, text, re.IGNORECASE)
        
        if random_match:
            message_template = random_match.group(1)
            messages = self.load_birthday_messages()
            messages["random_messages"].append(message_template)
            self.save_birthday_messages(messages)
            return f"@{sender_name} ✅ Random birthday message added!\nMessage: {message_template}"
        
        elif user_match:
            # Remove @ if present and convert to lowercase for consistent storage
            target_user = user_match.group(1).lower()
            message_template = user_match.group(2)
            messages = self.load_birthday_messages()
            messages["user_specific"][target_user] = message_template
            self.save_birthday_messages(messages)
            return f"@{sender_name} ✅ User-specific birthday message added for @{target_user}!\nMessage: {message_template}"
        
        else:
            return f"@{sender_name} <blockquote expandable>Invalid format. Use:\n• @{self.bot_username} add_birthday_message random \"Your message with {{username}} and {{age}}\"\n• @{self.bot_username} add_birthday_message user username \"User-specific message with {{username}} and {{age}}\"\n\nNote: Use {{username}} and {{age}} as placeholders in your message.</blockquote>"
    
    def process_list_birthday_messages(self, sender_name, sender_username):
        """Process list birthday messages command"""
        # Only special users can view birthday messages
        special_users = ["racistwaluigi", "kokorozasu"]
        if sender_username.lower() not in special_users:
            return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can view birthday messages."
        
        messages = self.load_birthday_messages()
        
        result = f"📝 Birthday Messages:\n\n<blockquote expandable>"
        
        # Random messages
        random_messages = messages.get("random_messages", [])
        if random_messages:
            result += f"🎲 Random Messages ({len(random_messages)}):\n"
            for i, msg in enumerate(random_messages, 1):
                result += f"{i}. {msg}\n"
            result += "\n"
        else:
            result += "🎲 Random Messages: None\n\n"
        
        # User-specific messages
        user_specific = messages.get("user_specific", {})
        if user_specific:
            result += f"👤 User-Specific Messages ({len(user_specific)}):\n"
            for username, msg in user_specific.items():
                result += f"@{username}: {msg}\n"
        else:
            result += "👤 User-Specific Messages: None"
        
        result += "</blockquote>"
        
        return result
    
    def process_delete_birthday_message(self, text, sender_name, sender_username):
        """Process delete birthday message command"""
        # Only special users can manage birthday messages
        special_users = ["racistwaluigi", "kokorozasu"]
        if sender_username.lower() not in special_users:
            return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can manage birthday messages."
        
        import re
        
        # Parse command formats:
        # @Angel_Dimi_Bot delete_birthday_message random 1
        # @Angel_Dimi_Bot delete_birthday_message user racistwaluigi
        
        # Try random message deletion
        random_pattern = r'delete_birthday_message\s+random\s+(\d+)'
        random_match = re.search(random_pattern, text, re.IGNORECASE)
        
        # Try user-specific message deletion (handle both @username and username)
        user_pattern = r'delete_birthday_message\s+user\s+@?(\w+)'
        user_match = re.search(user_pattern, text, re.IGNORECASE)
        
        if random_match:
            index = int(random_match.group(1)) - 1  # Convert to 0-based index
            messages = self.load_birthday_messages()
            random_messages = messages.get("random_messages", [])
            
            if 0 <= index < len(random_messages):
                deleted_message = random_messages.pop(index)
                self.save_birthday_messages(messages)
                return f"@{sender_name} ✅ Random birthday message #{index + 1} deleted!\nDeleted: {deleted_message}"
            else:
                return f"@{sender_name} ❌ Invalid message number. Use list_birthday_messages to see available messages."
        
        elif user_match:
            # Remove @ if present and convert to lowercase for consistent lookup
            target_user = user_match.group(1).lower()
            messages = self.load_birthday_messages()
            user_specific = messages.get("user_specific", {})
            
            if target_user in user_specific:
                deleted_message = user_specific.pop(target_user)
                self.save_birthday_messages(messages)
                return f"@{sender_name} ✅ User-specific birthday message for @{target_user} deleted!\nDeleted: {deleted_message}"
            else:
                return f"@{sender_name} ❌ No user-specific message found for @{target_user}."
        
        else:
            return f"@{sender_name} <blockquote expandable>Invalid format. Use:\n• @{self.bot_username} delete_birthday_message random [number]\n• @{self.bot_username} delete_birthday_message user [username]\n\nUse list_birthday_messages to see available messages.</blockquote>"
    
    def get_help_message(self, sender_name, sender_username):
        """Generate help message with available commands"""
        special_users = ["racistwaluigi", "kokorozasu"]
        is_special_user = sender_username.lower() in special_users
        bot_mention = f"@{self.bot_username}"
        
        help_text = f"🤖 {self.bot_username} Commands:\n\n<blockquote expandable>"
        
        # Archive commands (available to everyone)
        help_text += "📁 Archive Commands:\n"
        help_text += f"• /archive{bot_mention} &lt;URL&gt; - Archive a link\n"
        help_text += f"  Example: /archive{bot_mention} https://example.com\n\n"
        
        # Birthday commands (available to everyone for self)
        help_text += "🎂 Birthday Commands:\n"
        help_text += f"• /birthday_set{bot_mention} &lt;YYYY-MM-DD&gt; &lt;Timezone&gt; [username] - Set birthday\n"
        help_text += f"  Example: /birthday_set{bot_mention} 1990-03-15 America/New_York\n\n"
        
        # Quiz commands (if available)
        if self.quiz_manager:
            help_text += "🎯 Quiz Commands:\n"
            help_text += f"• /quiz_new{bot_mention} &lt;Subject&gt; [Number] [Difficulty] - Start a new quiz\n"
            help_text += f"  Example: /quiz_new{bot_mention} Python Programming 5 medium\n"
            help_text += f"• /quiz_leaderboard{bot_mention} - Show current quiz scores\n"
            help_text += f"• /quiz_stop{bot_mention} - Stop the current quiz\n"
            help_text += f"• /quiz_help{bot_mention} - Detailed quiz help and rules\n\n"
        
        # Fun commands
        help_text += "🎯 Activity &amp; Fun Commands:\n"
        help_text += f"• /layla{bot_mention} - Send a random Layla image\n"
        help_text += f"• /bored{bot_mention} - Get a random activity suggestion\n"
        help_text += f"• /bored_type{bot_mention} &lt;type&gt; - Get activity by type\n"
        help_text += "  Types: education, social, recreational, diy, charity, cooking, relaxation, music, busywork\n"
        help_text += f"• /bored_participants{bot_mention} &lt;number&gt; - Get activity for specific number of people\n"
        help_text += f"• /bored_price{bot_mention} &lt;range&gt; - Get activity by cost (free, low, medium, high)\n"
        help_text += f"• /age_guess{bot_mention} &lt;name&gt; - Predict someone's age based on their name\n"
        help_text += f"  Example: /age_guess{bot_mention} John\n"
        help_text += f"• /xkcd_latest{bot_mention} - Get the latest XKCD comic\n"
        help_text += f"• /xkcd_random{bot_mention} - Get a random XKCD comic\n"
        help_text += f"• /xkcd_number{bot_mention} &lt;number&gt; - Get a specific XKCD comic\n"
        help_text += f"  Example: /xkcd_number{bot_mention} 353\n"
        help_text += f"• /iss{bot_mention} - Get current location and crew of the International Space Station\n"
        help_text += f"• /mensfashion{bot_mention} - Get a random men's fashion image from Reddit\n"
        help_text += f"• /startup{bot_mention} - Get a random startup idea with relevant image\n\n"
        
        # Special user commands
        if is_special_user:
            help_text += "👑 Admin Commands (Special Users Only):\n"
            help_text += f"• /test_birthday{bot_mention} - Send test birthday message\n"
            help_text += f"• /delete_birthday{bot_mention} &lt;username&gt; - Delete a birthday\n"
            help_text += f"• /list_birthdays{bot_mention} - List all stored birthdays\n"
            help_text += f"• /add_birthday_message{bot_mention} random \"message\" - Add random birthday message\n"
            help_text += f"• /add_birthday_message{bot_mention} user &lt;username&gt; \"message\" - Add user-specific message\n"
            help_text += f"• /list_birthday_messages{bot_mention} - View all birthday messages\n"
            help_text += f"• /delete_birthday_message{bot_mention} random &lt;number&gt; - Delete random message\n"
            help_text += f"• /delete_birthday_message{bot_mention} user &lt;username&gt; - Delete user message\n"
            help_text += "• Can set birthdays for any user\n\n"
        
        # Additional info
        help_text += "📝 Notes:\n"
        help_text += f"• In group chats: Use {bot_mention} (e.g., /help{bot_mention})\n"
        help_text += f"• In private chats: {bot_mention} is optional (e.g., /help works)\n"
        help_text += "• Use / to see all available commands in your chat\n"
        help_text += "• Birthday alerts sent to group at midnight in your timezone\n"
        help_text += "• Timezone list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        
        help_text += "</blockquote>"
        
        return help_text
    
    def send_test_birthday_message(self, chat_id):
        """Send test birthday message using a random registered user and appropriate birthday message"""
        try:
            # Load registered birthdays
            birthdays = self.load_birthdays()
            
            if not birthdays:
                return "❌ No registered birthdays found. Add some birthdays first to test the birthday message system."
            
            # Pick a random registered user
            random_username = random.choice(list(birthdays.keys()))
            user_data = birthdays[random_username]
            
            # Calculate their current age
            age = self.calculate_age(user_data['date'])
            
            # Get appropriate birthday message using the birthday message system
            message = self.get_birthday_message(random_username, age)
            
            # Send the actual birthday message (same as automatic system would send)
            success = self.send_birthday_message(random_username, age, chat_id)
            
            if success:
                return f"✅ Sent realistic birthday message for @{random_username} (age {age})"
            else:
                return "❌ Failed to send birthday message"
                
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
    
    def process_slash_command(self, text, sender_name="User", sender_username=None, sender_id=None, chat_id=None):
        """Process slash commands"""
        if not text.startswith('/'):
            return None
        
        # Parse command and arguments
        parts = text.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Check if command is directed at this bot or no specific bot
        if '@' in command:
            # Command is directed at a specific bot (e.g., /help@Angel_Dimi_Bot)
            cmd_parts = command.split('@', 1)
            command = cmd_parts[0]  # Extract the actual command
            target_bot = cmd_parts[1]  # Extract the target bot username
            
            # Only respond if the command is directed at this bot
            if target_bot.lower() != self.bot_username.lower():
                return None  # Ignore commands for other bots
        else:
            # Generic command without bot specification (e.g., /help)
            # In group chats, only respond to commands explicitly directed at this bot
            # In private chats (chat_id > 0), we can respond to generic commands
            if chat_id and chat_id < 0:  # Negative chat_id means group/channel
                return None  # Ignore generic commands in groups
        
        logger.info(f"Processing slash command '{command}' from {sender_name}")
        
        # Route commands to appropriate handlers
        if command == "/help" or command == "/start":
            return self.get_help_message(sender_name, sender_username)
        
        elif command == "/archive":
            return self.handle_archive_command(args, sender_name)
        
        elif command == "/birthday_set":
            return self.handle_birthday_set_command(args, sender_name, sender_username, sender_id)
        
        elif command == "/layla":
            return self.handle_layla_command(chat_id)
        
        elif command == "/bored":
            return self.handle_bored_command()
        
        elif command == "/bored_type":
            return self.handle_bored_type_command(args)
        
        elif command == "/bored_participants":
            return self.handle_bored_participants_command(args)
        
        elif command == "/bored_price":
            return self.handle_bored_price_command(args)
        
        elif command == "/age_guess":
            return self.handle_age_guess_command(args)
        
        elif command == "/xkcd_latest":
            return self.handle_xkcd_latest_command(chat_id)
        
        elif command == "/xkcd_random":
            return self.handle_xkcd_random_command(chat_id)
        
        elif command == "/xkcd_number":
            return self.handle_xkcd_number_command(args, chat_id)
        
        elif command == "/iss":
            return self.handle_iss_command()
        
        elif command == "/mensfashion":
            return self.handle_mensfashion_command(chat_id)
        
        elif command == "/startup":
            return self.handle_startup_command(chat_id)
        
        # Quiz commands
        elif command in ["/quiz_new", "/quiz_leaderboard", "/quiz_stop", "/quiz_help"]:
            return self.handle_quiz_command(command, args, sender_name, sender_username, sender_id, chat_id)
        
        # Admin-only commands
        elif command in ["/test_birthday", "/delete_birthday", "/list_birthdays", "/add_birthday_message", 
                        "/list_birthday_messages", "/delete_birthday_message"]:
            return self.handle_admin_command(command, args, sender_name, sender_username, sender_id, chat_id)
        
        else:
            return f"Unknown command: {command}. Use /help to see available commands."
    
    def handle_archive_command(self, args, sender_name):
        """Handle /archive command"""
        if not args.strip():
            return f"Please provide a URL to archive.\nExample: /archive https://example.com"
        
        urls = self.extract_urls(args)
        if not urls:
            return f"No valid URLs found in your message. Please provide a URL to archive."
        
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
            return f"Here is your archived link:\n\n" + "\n\n".join(archived_results)
        else:
            return f"Here are your archived links:\n\n" + "\n\n".join(archived_results)
    
    def handle_birthday_set_command(self, args, sender_name, sender_username, sender_id):
        """Handle /birthday_set command"""
        if not args.strip():
            return "<blockquote expandable>Please provide birthday information.\nFormat: /birthday_set YYYY-MM-DD Timezone [username]\nExample: /birthday_set 1990-03-15 America/New_York</blockquote>"
        
        # Parse the birthday command using existing logic
        fake_text = f"birthday set {args}"  # Convert to old format for parsing
        birthday_data, error = self.parse_birthday_command(fake_text, sender_username, sender_id)
        
        if error:
            return error
        
        target_username = birthday_data['username']
        
        # Check authorization
        is_authorized, auth_type = self.is_user_authorized(sender_username, target_username)
        if not is_authorized:
            return f"You can only set your own birthday. To set birthday for @{target_username}, ask an admin to do it."
        
        # Load existing birthdays
        birthdays = self.load_birthdays()
        
        # Check if user already exists and show update message
        update_message = ""
        if target_username in birthdays:
            existing = birthdays[target_username]
            existing_age = self.calculate_age(existing['date'])
            update_message = f"\n\n📝 Updated from:\nOld Birthday: {existing['date']}\nOld Timezone: {existing['timezone']}\nOld Age: {existing_age}"
        
        # Save new birthday (always save, whether new or update)
        birthdays[target_username] = birthday_data
        self.save_birthdays(birthdays)
        
        age = self.calculate_age(birthday_data['date'])
        
        if auth_type == "self":
            return f"<blockquote expandable>✅ Your birthday has been saved!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}</blockquote>"
        else:
            return f"<blockquote expandable>✅ Birthday saved for @{target_username}!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}</blockquote>"
    
    def handle_layla_command(self, chat_id):
        """Handle /layla command - send random image from layla_images folder"""
        try:
            import requests
            
            # Get layla_images folder path
            image_folder = os.path.join(os.path.dirname(__file__), 'layla_images')
            if not os.path.exists(image_folder):
                return "❌ Layla images folder not found."
            
            # Get all image files (common formats)
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
            image_files = []
            for extension in image_extensions:
                image_files.extend(glob.glob(os.path.join(image_folder, extension)))
                image_files.extend(glob.glob(os.path.join(image_folder, extension.upper())))
            
            if not image_files:
                return "❌ No images found in layla_images folder."
            
            # Pick a random image
            random_image = random.choice(image_files)
            logger.info(f"Sending random Layla image: {os.path.basename(random_image)}")
            
            # Send the image
            url = f"{self.telegram_api_url}/sendPhoto"
            
            with open(random_image, 'rb') as image_file:
                files = {'photo': image_file}
                data = {'chat_id': chat_id}
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    return None  # Don't send text response when image is sent successfully
                else:
                    logger.error(f"Failed to send Layla image: {response.text}")
                    return "❌ Failed to send Layla image."
                    
        except Exception as e:
            logger.error(f"Error sending Layla image: {e}")
            return f"❌ Error sending Layla image: {str(e)}"
    
    def handle_mensfashion_command(self, chat_id):
        """Handle /mensfashion command - send random image from r/malefashionadvice"""
        try:
            import requests
            import json
            import random
            
            # Better headers to avoid Reddit blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Try multiple subreddits for better variety
            subreddits = ['malefashionadvice', 'malefashion', 'streetwear']
            
            image_posts = []
            
            # Try each subreddit until we find images
            for subreddit in subreddits:
                try:
                    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    logger.info(f"Reddit API response for r/{subreddit}: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        # Filter for image posts
                        for post in posts:
                            post_data = post.get('data', {})
                            post_url = post_data.get('url', '')
                            
                            # Check if it's an image URL
                            if (post_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) or 
                                'i.redd.it' in post_url or 'i.imgur.com' in post_url or
                                'imgur.com' in post_url):
                                image_posts.append({
                                    'url': post_url,
                                    'title': post_data.get('title', ''),
                                    'subreddit': post_data.get('subreddit', '')
                                })
                        
                        if image_posts:
                            break  # Found images, no need to try other subreddits
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch from r/{subreddit}: {e}")
                    continue
            
            if not image_posts:
                return "❌ No fashion images found. Reddit might be temporarily unavailable."
            
            # Select random image
            selected_post = random.choice(image_posts)
            image_url = selected_post['url']
            
            logger.info(f"Sending fashion image from r/{selected_post['subreddit']}: {image_url}")
            
            # Send the image
            telegram_url = f"{self.telegram_api_url}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'photo': image_url
            }
            
            response = requests.post(telegram_url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Men's fashion image sent to chat {chat_id}")
                return None  # Don't send text response when image is sent successfully
            else:
                logger.error(f"Failed to send fashion image: {response.text}")
                return "❌ Failed to send fashion image. The image URL might be invalid."
                
        except Exception as e:
            logger.error(f"Error in mensfashion command: {e}")
            return f"❌ Error fetching fashion image. Please try again later."
    
    def handle_startup_command(self, chat_id):
        """Handle /startup command - send random startup idea with relevant image"""
        try:
            import requests
            import json
            import random
            import re
            from urllib.parse import quote
            
            logger.info("Fetching startup idea from API...")
            
            # Get random startup idea
            startup_response = requests.get("https://itsthisforthat.com/api.php", timeout=10)
            
            if startup_response.status_code != 200:
                return "❌ Failed to fetch startup idea. Please try again later."
            
            # Check if response is JSON or plain text
            try:
                startup_data = startup_response.json()
                startup_idea = startup_data.get('this', 'Unknown') + " for " + startup_data.get('that', 'Unknown')
            except json.JSONDecodeError:
                # API might return plain text, let's check the content
                response_text = startup_response.text.strip()
                logger.info(f"API response (non-JSON): {response_text}")
                
                if response_text:
                    startup_idea = response_text
                else:
                    # Fallback to manual startup ideas if API fails
                    fallback_ideas = [
                        "Uber for Dogs",
                        "Netflix for Books", 
                        "Spotify for Podcasts",
                        "Instagram for Food",
                        "Airbnb for Workspaces",
                        "Tinder for Business Networking",
                        "Amazon for Local Services",
                        "YouTube for Education",
                        "WhatsApp for Teams",
                        "Google Maps for Indoor Navigation"
                    ]
                    startup_idea = random.choice(fallback_ideas)
                    logger.info(f"Using fallback startup idea: {startup_idea}")
            
            logger.info(f"Generated startup idea: {startup_idea}")
            
            # Extract keywords for image search
            keywords = self._extract_startup_keywords(startup_idea)
            search_query = " ".join(keywords[:3])  # Use top 3 keywords
            
            logger.info(f"Image search query: {search_query}")
            
            # Search for relevant image using DuckDuckGo
            image_url = self._search_startup_image(search_query)
            
            if image_url:
                # Send image with startup idea as caption
                telegram_url = f"{self.telegram_api_url}/sendPhoto"
                data = {
                    'chat_id': chat_id,
                    'photo': image_url,
                    'caption': f"💡 <b>Random Startup Idea:</b>\n\n<i>{startup_idea}</i>\n\n🚀 Ready to disrupt the market?",
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(telegram_url, json=data, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Startup idea with image sent to chat {chat_id}")
                    return None
                else:
                    logger.warning(f"Failed to send image, sending text only: {response.text}")
                    # Fallback to text only
                    return f"💡 <b>Random Startup Idea:</b>\n\n<i>{startup_idea}</i>\n\n🚀 Ready to disrupt the market?"
            else:
                # No image found, send text only
                return f"💡 <b>Random Startup Idea:</b>\n\n<i>{startup_idea}</i>\n\n🚀 Ready to disrupt the market?"
                
        except Exception as e:
            logger.error(f"Error in startup command: {e}")
            return f"❌ Error fetching startup idea: {str(e)}"
    
    def _extract_startup_keywords(self, startup_idea):
        """Extract relevant keywords from startup idea for image search"""
        # Remove common words and extract meaningful terms
        common_words = {'for', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'of', 'with', 'by'}
        
        # Split and clean words
        words = re.findall(r'\b\w+\b', startup_idea.lower())
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        
        # Prioritize business/tech related terms
        priority_terms = ['app', 'platform', 'service', 'system', 'tool', 'software', 'tech', 'digital', 'online', 'mobile']
        
        # Sort keywords by priority
        prioritized = []
        for term in priority_terms:
            if term in keywords:
                prioritized.append(term)
                keywords.remove(term)
        
        return prioritized + keywords
    
    def _search_startup_image(self, query):
        """Search for relevant image using DuckDuckGo"""
        try:
            import requests
            from urllib.parse import quote
            
            # DuckDuckGo image search
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Add business/startup context to search
            enhanced_query = f"{query} business startup technology"
            encoded_query = quote(enhanced_query)
            
            # DuckDuckGo instant answer API for images
            search_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&image_type=photo&safesearch=moderate"
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Try to get image from related topics or abstract
                if 'RelatedTopics' in data and data['RelatedTopics']:
                    for topic in data['RelatedTopics'][:5]:  # Check first 5 topics
                        if 'Icon' in topic and topic['Icon'].get('URL'):
                            icon_url = topic['Icon']['URL']
                            if icon_url.startswith('http') and any(ext in icon_url for ext in ['.jpg', '.png', '.jpeg', '.gif']):
                                return icon_url
                
                # Fallback: try a simple business/startup image search
                fallback_queries = [
                    "startup business idea",
                    "innovation technology",
                    "business concept",
                    "entrepreneurship"
                ]
                
                for fallback_query in fallback_queries:
                    try:
                        # Use a different approach - search for stock images
                        stock_images = [
                            "https://images.unsplash.com/photo-1556761175-b413da4baf72?w=500",  # Startup team
                            "https://images.unsplash.com/photo-1553484771-371a605b060b?w=500",  # Innovation
                            "https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=500",  # Business idea
                            "https://images.unsplash.com/photo-1552664730-d307ca884978?w=500",  # Startup office
                            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500",  # Technology
                        ]
                        return random.choice(stock_images)
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching for startup image: {e}")
            return None
    
    def handle_bored_command(self):
        """Handle /bored command - get a random activity"""
        try:
            import requests
            
            response = requests.get("https://apis.scrimba.com/bored/api/activity", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                activity = data.get('activity', 'No activity found')
                activity_type = data.get('type', 'Unknown').title()
                participants = data.get('participants', 'Unknown')
                price = data.get('price', 0)
                
                # Format price description
                if price == 0:
                    price_desc = "Free"
                elif price <= 0.3:
                    price_desc = "Low cost"
                elif price <= 0.6:
                    price_desc = "Medium cost"
                else:
                    price_desc = "High cost"
                
                return f"<blockquote expandable>🎯 <b>Random Activity Suggestion:</b>\n\n" \
                       f"<b>Activity:</b> {activity}\n" \
                       f"<b>Type:</b> {activity_type}\n" \
                       f"<b>Participants:</b> {participants}\n" \
                       f"<b>Cost:</b> {price_desc}</blockquote>"
            else:
                return "❌ Failed to get activity suggestion. Please try again later."
                
        except Exception as e:
            logger.error(f"Error getting bored activity: {e}")
            return "❌ Error getting activity suggestion. Please try again later."
    
    def handle_bored_type_command(self, args):
        """Handle /bored_type command - get activity by type"""
        if not args.strip():
            return "<blockquote expandable>Please specify an activity type.\n\n" \
                   "<b>Available types:</b>\n" \
                   "• education - Learn something new\n" \
                   "• recreational - Fun and games\n" \
                   "• social - Activities with others\n" \
                   "• diy - Do-it-yourself projects\n" \
                   "• charity - Help others\n" \
                   "• cooking - Food and recipes\n" \
                   "• relaxation - Chill and unwind\n" \
                   "• music - Musical activities\n" \
                   "• busywork - Productive tasks\n\n" \
                   "<b>Example:</b> /bored_type social</blockquote>"
        
        activity_type = args.strip().lower()
        valid_types = ['education', 'recreational', 'social', 'diy', 'charity', 'cooking', 'relaxation', 'music', 'busywork']
        
        if activity_type not in valid_types:
            return f"<blockquote expandable>❌ Invalid activity type '{activity_type}'.\n\n" \
                   f"Valid types: {', '.join(valid_types)}</blockquote>"
        
        try:
            import requests
            
            response = requests.get(f"https://apis.scrimba.com/bored/api/activity?type={activity_type}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                activity = data.get('activity', 'No activity found')
                participants = data.get('participants', 'Unknown')
                price = data.get('price', 0)
                
                # Format price description
                if price == 0:
                    price_desc = "Free"
                elif price <= 0.3:
                    price_desc = "Low cost"
                elif price <= 0.6:
                    price_desc = "Medium cost"
                else:
                    price_desc = "High cost"
                
                return f"<blockquote expandable>🎯 <b>{activity_type.title()} Activity:</b>\n\n" \
                       f"<b>Activity:</b> {activity}\n" \
                       f"<b>Participants:</b> {participants}\n" \
                       f"<b>Cost:</b> {price_desc}</blockquote>"
            else:
                return f"❌ No {activity_type} activities found. Please try again."
                
        except Exception as e:
            logger.error(f"Error getting bored activity by type: {e}")
            return "❌ Error getting activity suggestion. Please try again later."
    
    def handle_bored_participants_command(self, args):
        """Handle /bored_participants command - get activity by number of participants"""
        if not args.strip():
            return "<blockquote expandable>Please specify the number of participants.\n\n" \
                   "<b>Examples:</b>\n" \
                   "• /bored_participants 1 - Solo activities\n" \
                   "• /bored_participants 2 - Activities for two people\n" \
                   "• /bored_participants 4 - Group activities\n\n" \
                   "<b>Note:</b> You can specify any number from 1 to 8</blockquote>"
        
        try:
            participants = int(args.strip())
            if participants < 1 or participants > 8:
                return "❌ Number of participants must be between 1 and 8."
        except ValueError:
            return "❌ Please provide a valid number of participants.\nExample: /bored_participants 2"
        
        try:
            import requests
            
            response = requests.get(f"https://apis.scrimba.com/bored/api/activity?participants={participants}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                activity = data.get('activity', 'No activity found')
                activity_type = data.get('type', 'Unknown').title()
                price = data.get('price', 0)
                
                # Format price description
                if price == 0:
                    price_desc = "Free"
                elif price <= 0.3:
                    price_desc = "Low cost"
                elif price <= 0.6:
                    price_desc = "Medium cost"
                else:
                    price_desc = "High cost"
                
                participant_text = "person" if participants == 1 else "people"
                
                return f"<blockquote expandable>🎯 <b>Activity for {participants} {participant_text}:</b>\n\n" \
                       f"<b>Activity:</b> {activity}\n" \
                       f"<b>Type:</b> {activity_type}\n" \
                       f"<b>Cost:</b> {price_desc}</blockquote>"
            else:
                return f"❌ No activities found for {participants} participants. Please try a different number."
                
        except Exception as e:
            logger.error(f"Error getting bored activity by participants: {e}")
            return "❌ Error getting activity suggestion. Please try again later."
    
    def handle_bored_price_command(self, args):
        """Handle /bored_price command - get activity by price range"""
        if not args.strip():
            return "<blockquote expandable>Please specify a price range.\n\n" \
                   "<b>Available price ranges:</b>\n" \
                   "• free - Completely free activities\n" \
                   "• low - Low cost activities\n" \
                   "• medium - Medium cost activities\n" \
                   "• high - Higher cost activities\n\n" \
                   "<b>Example:</b> /bored_price free</blockquote>"
        
        price_range = args.strip().lower()
        
        # Map price ranges to API values
        price_mapping = {
            'free': (0, 0),
            'low': (0.1, 0.3),
            'medium': (0.4, 0.6),
            'high': (0.7, 1.0)
        }
        
        if price_range not in price_mapping:
            return f"<blockquote expandable>❌ Invalid price range '{price_range}'.\n\n" \
                   f"Valid ranges: {', '.join(price_mapping.keys())}</blockquote>"
        
        min_price, max_price = price_mapping[price_range]
        
        try:
            import requests
            
            response = requests.get(f"https://apis.scrimba.com/bored/api/activity?minprice={min_price}&maxprice={max_price}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                activity = data.get('activity', 'No activity found')
                activity_type = data.get('type', 'Unknown').title()
                participants = data.get('participants', 'Unknown')
                
                return f"<blockquote expandable>🎯 <b>{price_range.title()} Cost Activity:</b>\n\n" \
                       f"<b>Activity:</b> {activity}\n" \
                       f"<b>Type:</b> {activity_type}\n" \
                       f"<b>Participants:</b> {participants}</blockquote>"
            else:
                return f"❌ No {price_range} cost activities found. Please try again."
                
        except Exception as e:
            logger.error(f"Error getting bored activity by price: {e}")
            return "❌ Error getting activity suggestion. Please try again later."
    
    def handle_age_guess_command(self, args):
        """Handle /age_guess command - predict age based on name using Agify API"""
        if not args.strip():
            return "<blockquote expandable>Please provide a name to guess the age for.\n\n" \
                   "<b>Examples:</b>\n" \
                   "• /age_guess John\n" \
                   "• /age_guess Sarah\n" \
                   "• /age_guess Michael\n\n" \
                   "<b>Note:</b> This uses statistical data and may not be accurate for individuals.</blockquote>"
        
        name = args.strip().title()  # Capitalize first letter for better display
        
        # Basic name validation
        if not name.replace(' ', '').replace('-', '').isalpha():
            return "❌ Please provide a valid name (letters only).\nExample: /age_guess John"
        
        if len(name) > 50:
            return "❌ Name is too long. Please provide a shorter name."
        
        try:
            import requests
            
            # Use the first name only for the API call
            first_name = name.split()[0].lower()
            
            response = requests.get(f"https://api.agify.io?name={first_name}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                predicted_age = data.get('age')
                count = data.get('count', 0)
                
                if predicted_age is None:
                    return f"<blockquote expandable>🤔 <b>Age Prediction for {name}:</b>\n\n" \
                           f"❌ Sorry, I couldn't find enough data to predict the age for the name '{name}'.\n\n" \
                           f"This might happen with very rare or unique names.</blockquote>"
                
                # Add confidence indicator based on count
                if count < 100:
                    confidence = "Low confidence"
                    confidence_emoji = "🤷"
                elif count < 1000:
                    confidence = "Medium confidence"
                    confidence_emoji = "🤔"
                else:
                    confidence = "High confidence"
                    confidence_emoji = "✅"
                
                # Add age range description
                if predicted_age < 18:
                    age_group = "Young person"
                elif predicted_age < 30:
                    age_group = "Young adult"
                elif predicted_age < 50:
                    age_group = "Adult"
                elif predicted_age < 65:
                    age_group = "Middle-aged"
                else:
                    age_group = "Senior"
                
                return f"<blockquote expandable>🎯 <b>Age Prediction for {name}:</b>\n\n" \
                       f"<b>Predicted Age:</b> {predicted_age} years old\n" \
                       f"<b>Age Group:</b> {age_group}\n" \
                       f"<b>Confidence:</b> {confidence_emoji} {confidence}\n" \
                       f"<b>Based on:</b> {count:,} data points\n\n" \
                       f"<i>💡 This is based on statistical data from people with this name and may not reflect individual cases.</i></blockquote>"
            
            elif response.status_code == 429:
                return "❌ Too many requests. Please wait a moment and try again."
            else:
                return "❌ Failed to get age prediction. Please try again later."
                
        except Exception as e:
            logger.error(f"Error getting age prediction: {e}")
            return "❌ Error getting age prediction. Please try again later."
    
    def handle_xkcd_latest_command(self, chat_id):
        """Handle /xkcd_latest command - get the latest XKCD comic"""
        try:
            import requests
            
            response = requests.get("https://xkcd.com/info.0.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self.send_xkcd_comic(data, chat_id)
            else:
                return "❌ Failed to get latest XKCD comic. Please try again later."
                
        except Exception as e:
            logger.error(f"Error getting latest XKCD: {e}")
            return "❌ Error getting latest XKCD comic. Please try again later."
    
    def handle_xkcd_random_command(self, chat_id):
        """Handle /xkcd_random command - get a random XKCD comic"""
        try:
            import requests
            
            # First get the latest comic number
            latest_response = requests.get("https://xkcd.com/info.0.json", timeout=10)
            if latest_response.status_code != 200:
                return "❌ Failed to get random XKCD comic. Please try again later."
            
            latest_num = latest_response.json()['num']
            
            # Generate random comic number (avoiding 404 which doesn't exist)
            random_num = random.randint(1, latest_num)
            if random_num == 404:
                random_num = 405  # Skip the non-existent comic 404
            
            # Get the random comic
            response = requests.get(f"https://xkcd.com/{random_num}/info.0.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self.send_xkcd_comic(data, chat_id)
            else:
                return "❌ Failed to get random XKCD comic. Please try again later."
                
        except Exception as e:
            logger.error(f"Error getting random XKCD: {e}")
            return "❌ Error getting random XKCD comic. Please try again later."
    
    def handle_xkcd_number_command(self, args, chat_id):
        """Handle /xkcd_number command - get a specific XKCD comic by number"""
        if not args.strip():
            return "<blockquote expandable>Please specify a comic number.\n\n" \
                   "<b>Examples:</b>\n" \
                   f"• /xkcd_number@{self.bot_username} 1\n" \
                   f"• /xkcd_number@{self.bot_username} 353\n" \
                   f"• /xkcd_number@{self.bot_username} 2000\n\n" \
                   "<b>Note:</b> Comic #404 doesn't exist (it's a joke about HTTP 404 errors)</blockquote>"
        
        try:
            comic_num = int(args.strip())
            if comic_num < 1:
                return "❌ Comic number must be 1 or higher."
            
            if comic_num == 404:
                return "❌ Comic #404 doesn't exist! This is an intentional joke about HTTP 404 errors. Try a different number."
                
        except ValueError:
            return f"❌ Please provide a valid comic number.\nExample: /xkcd_number@{self.bot_username} 353"
        
        try:
            import requests
            
            response = requests.get(f"https://xkcd.com/{comic_num}/info.0.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self.send_xkcd_comic(data, chat_id)
            elif response.status_code == 404:
                return f"❌ Comic #{comic_num} doesn't exist. Try a lower number or use /xkcd_latest@{self.bot_username} to see the highest available number."
            else:
                return "❌ Failed to get XKCD comic. Please try again later."
                
        except Exception as e:
            logger.error(f"Error getting XKCD comic {comic_num}: {e}")
            return "❌ Error getting XKCD comic. Please try again later."
    
    def send_xkcd_comic(self, data, chat_id):
        """Send XKCD comic image with simple caption"""
        try:
            import requests
            
            num = data.get('num', 'Unknown')
            title = data.get('safe_title', data.get('title', 'Untitled'))
            alt_text = data.get('alt', '')
            img_url = data.get('img', '')
            year = data.get('year', '')
            month = data.get('month', '')
            day = data.get('day', '')
            
            if not img_url:
                return f"#{num}: {title}\n❌ No image available for this comic."
            
            # Format date
            date_str = ""
            try:
                if year and month and day:
                    date_obj = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                    date_str = date_obj.strftime("%B %d, %Y")
            except:
                pass
            
            # Build caption with title, date, and alt text
            caption = f"#{num}: {title}"
            if date_str:
                caption += f"\n{date_str}"
            if alt_text:
                caption += f"\n\n{alt_text}"
            
            # Send the comic image directly
            url = f"{self.telegram_api_url}/sendPhoto"
            
            # Download and send the image
            img_response = requests.get(img_url, timeout=30)
            if img_response.status_code == 200:
                files = {'photo': ('xkcd.png', img_response.content, 'image/png')}
                data_payload = {
                    'chat_id': chat_id,
                    'caption': caption
                }
                response = requests.post(url, files=files, data=data_payload, timeout=30)
                
                if response.status_code == 200:
                    return None  # Don't send text response when image is sent successfully
                else:
                    logger.error(f"Failed to send XKCD image: {response.text}")
                    return f"{caption}\n❌ Failed to send comic image."
            else:
                return f"{caption}\n❌ Failed to download comic image."
                
        except Exception as e:
            logger.error(f"Error sending XKCD comic: {e}")
            return "❌ Error sending XKCD comic."
    
    def handle_iss_command(self):
        """Handle /iss command - get current ISS location and crew information"""
        try:
            import requests
            
            # Get ISS location
            location_response = requests.get("http://api.open-notify.org/iss-now.json", timeout=10)
            
            # Get ISS crew information
            crew_response = requests.get("http://api.open-notify.org/astros.json", timeout=10)
            
            if location_response.status_code != 200:
                return "❌ Failed to get ISS location data. Please try again later."
            
            if crew_response.status_code != 200:
                return "❌ Failed to get ISS crew data. Please try again later."
            
            location_data = location_response.json()
            crew_data = crew_response.json()
            
            # Extract location data
            latitude = float(location_data['iss_position']['latitude'])
            longitude = float(location_data['iss_position']['longitude'])
            timestamp = location_data['timestamp']
            
            # Extract crew data - filter for ISS crew only
            total_people = crew_data.get('number', 0)
            all_people = crew_data.get('people', [])
            iss_crew = [person for person in all_people if person.get('craft', '').lower() == 'iss']
            iss_crew_count = len(iss_crew)
            
            # Get location description
            location_desc = self.get_location_description(latitude, longitude)
            
            # Format response
            response = f"<blockquote expandable>🛰️ <b>International Space Station Status:</b>\n\n"
            response += f"<b>Current Location:</b> {location_desc}\n"
            response += f"<b>Coordinates:</b> {latitude:.2f}°, {longitude:.2f}°\n"
            response += f"<b>Crew on ISS:</b> {iss_crew_count} people\n\n"
            
            if iss_crew:
                response += "<b>Current ISS Crew:</b>\n"
                for person in iss_crew:
                    name = person.get('name', 'Unknown')
                    response += f"• {name}\n"
            
            # Add timestamp
            try:
                from datetime import datetime
                dt = datetime.fromtimestamp(timestamp)
                response += f"\n<i>Data updated: {dt.strftime('%H:%M:%S UTC')}</i>"
            except:
                pass
            
            response += "</blockquote>"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting ISS data: {e}")
            return "❌ Error getting ISS information. Please try again later."
    
    def get_location_description(self, latitude, longitude):
        """Get a human-readable description of the ISS location"""
        try:
            # First try basic ocean/continent detection based on coordinates
            ocean_location = self.get_ocean_by_coordinates(latitude, longitude)
            if ocean_location:
                return ocean_location
            
            # Try reverse geocoding as backup
            import requests
            
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=3"
            headers = {'User-Agent': 'TelegramBot/1.0'}
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                # Check for country
                country = address.get('country')
                if country:
                    return f"Over {country}"
                
                # Check for state/region
                state = address.get('state') or address.get('region')
                if state:
                    return f"Over {state}"
            
        except Exception as e:
            logger.error(f"Error getting location description: {e}")
        
        # Final fallback to coordinate-based description
        return self.get_coordinate_description(latitude, longitude)
    
    def get_ocean_by_coordinates(self, latitude, longitude):
        """Determine ocean/sea based on coordinate ranges"""
        # Pacific Ocean (largest ocean)
        if (longitude >= -180 and longitude <= -70) or (longitude >= 120 and longitude <= 180):
            if latitude >= -60 and latitude <= 60:
                return "Over the Pacific Ocean"
        
        # Atlantic Ocean
        if longitude >= -70 and longitude <= 20:
            if latitude >= -60 and latitude <= 70:
                return "Over the Atlantic Ocean"
        
        # Indian Ocean
        if longitude >= 20 and longitude <= 120:
            if latitude >= -60 and latitude <= 30:
                return "Over the Indian Ocean"
        
        # Arctic Ocean
        if latitude >= 70:
            return "Over the Arctic Ocean"
        
        # Southern Ocean
        if latitude <= -60:
            return "Over the Southern Ocean"
        
        # Mediterranean Sea
        if longitude >= -6 and longitude <= 37 and latitude >= 30 and latitude <= 47:
            return "Over the Mediterranean Sea"
        
        # Caribbean Sea
        if longitude >= -85 and longitude <= -60 and latitude >= 9 and latitude <= 22:
            return "Over the Caribbean Sea"
        
        # Gulf of Mexico
        if longitude >= -98 and longitude <= -80 and latitude >= 18 and latitude <= 31:
            return "Over the Gulf of Mexico"
        
        return None
    
    def get_coordinate_description(self, latitude, longitude):
        """Get basic coordinate description as fallback"""
        if latitude > 0:
            lat_desc = f"{abs(latitude):.1f}°N"
        else:
            lat_desc = f"{abs(latitude):.1f}°S"
            
        if longitude > 0:
            lon_desc = f"{abs(longitude):.1f}°E"
        else:
            lon_desc = f"{abs(longitude):.1f}°W"
        
        return f"At {lat_desc}, {lon_desc}"
    
    def handle_quiz_command(self, command, args, sender_name, sender_username, sender_id, chat_id):
        """Handle quiz-related commands"""
        logger.info(f"Quiz command received: {command}, quiz_manager status: {'initialized' if self.quiz_manager else 'None'}")
        
        if not self.quiz_manager:
            logger.warning("Quiz command called but quiz_manager is None")
            return "❌ Quiz functionality is not available. Please check that GEMINI_API_KEY is configured."
        
        try:
            if command == "/quiz_new":
                return self.handle_quiz_new_command(args, sender_name, chat_id)
            elif command == "/quiz_leaderboard":
                return self.handle_quiz_leaderboard_command(chat_id)
            elif command == "/quiz_stop":
                return self.handle_quiz_stop_command(chat_id)
            elif command == "/quiz_help":
                return self.quiz_manager.get_help_text()
            else:
                return f"Unknown quiz command: {command}"
                
        except Exception as e:
            logger.error(f"Error handling quiz command {command}: {e}")
            return "❌ An error occurred while processing the quiz command. Please try again."
    
    def handle_quiz_new_command(self, args, sender_name, chat_id):
        """Handle /quiz_new command"""
        if not args.strip():
            return "Please provide quiz parameters.\nFormat: /quiz_new [Subject] [Number] [Difficulty]\nExample: /quiz_new Python Programming 5 medium"
        
        # Parse arguments
        parts = args.strip().split()
        if len(parts) < 1:
            return "Please provide at least a subject for the quiz.\nExample: /quiz_new Python Programming"
        
        # Extract subject (everything except last 1-2 parts if they're numbers/difficulty)
        subject_parts = []
        num_questions = 5  # default
        difficulty = "medium"  # default
        
        # Check if last part is a difficulty level
        if len(parts) > 1 and parts[-1].lower() in ['easy', 'medium', 'hard', 'expert']:
            difficulty = parts[-1].lower()
            parts = parts[:-1]
        
        # Check if last part is a number
        if len(parts) > 1:
            try:
                num_questions = int(parts[-1])
                parts = parts[:-1]
            except ValueError:
                pass  # Not a number, include in subject
        
        # Remaining parts form the subject
        subject = " ".join(parts)
        
        # Send progress message first
        from quiz.quiz_ui import QuizUI
        quiz_ui = QuizUI(self)
        progress_msg_id = quiz_ui.send_quiz_progress(chat_id, subject, num_questions, difficulty)
        
        # Create the quiz
        result = self.quiz_manager.create_quiz(chat_id, subject, num_questions, difficulty)
        
        if result['success']:
            # Quiz created successfully, send first question
            first_question = result['quiz_data'].get('first_question')
            if first_question:
                # Add question index to the question data
                first_question['question_index'] = 0
                quiz_ui.send_question(chat_id, first_question, 1, num_questions)
                return None  # Don't send additional text response
            else:
                return "✅ Quiz created successfully, but no questions were generated."
        else:
            # Quiz creation failed
            error_message = quiz_ui.format_error_message(result['error_type'], result['error'])
            return error_message
    
    def handle_quiz_leaderboard_command(self, chat_id):
        """Handle /quiz_leaderboard command"""
        result = self.quiz_manager.get_leaderboard(chat_id)
        
        if result['success']:
            from quiz.quiz_ui import QuizUI
            quiz_ui = QuizUI(self)
            leaderboard_type = result.get('type', 'current_quiz')
            quiz_info = result.get('quiz_info', {})
            quiz_ui.send_leaderboard(
                chat_id, 
                result['leaderboard'], 
                quiz_info, 
                is_final=False,
                leaderboard_type=leaderboard_type
            )
            return None  # Don't send additional text response
        else:
            from quiz.quiz_ui import QuizUI
            quiz_ui = QuizUI(self)
            return quiz_ui.format_error_message(result['error_type'], result['error'])
    
    def handle_quiz_stop_command(self, chat_id):
        """Handle /quiz_stop command"""
        result = self.quiz_manager.stop_quiz(chat_id)
        
        if result['success']:
            from quiz.quiz_ui import QuizUI
            quiz_ui = QuizUI(self)
            if result['final_leaderboard']:
                quiz_ui.send_leaderboard(chat_id, result['final_leaderboard'], result['quiz_info'], is_final=True)
            return "🏁 Quiz stopped successfully!"
        else:
            from quiz.quiz_ui import QuizUI
            quiz_ui = QuizUI(self)
            return quiz_ui.format_error_message(result['error_type'], result['error'])
    
    def handle_admin_command(self, command, args, sender_name, sender_username, sender_id, chat_id):
        """Handle admin-only commands"""
        # Check if user is admin
        special_users = ["racistwaluigi", "kokorozasu"]
        if sender_username.lower() not in special_users:
            return "This command is only available to administrators."
        
        # Route to appropriate admin command handler
        if command == "/test_birthday":
            return self.send_test_birthday_message(chat_id)
        elif command == "/delete_birthday":
            return self.handle_delete_birthday_command(args, sender_name)
        elif command == "/list_birthdays":
            return self.handle_list_birthdays_command(sender_name)
        elif command == "/add_birthday_message":
            return self.handle_add_birthday_message_command(args, sender_name, sender_username)
        elif command == "/list_birthday_messages":
            return self.handle_list_birthday_messages_command(sender_name, sender_username)
        elif command == "/delete_birthday_message":
            return self.handle_delete_birthday_message_command(args, sender_name, sender_username)
        
        return "Unknown admin command."
    
    def handle_delete_birthday_command(self, args, sender_name):
        """Handle /delete_birthday command"""
        if not args.strip():
            return "<blockquote expandable>Please specify a username.\nFormat: /delete_birthday username\nExample: /delete_birthday john</blockquote>"
        
        username_to_delete = args.strip().replace('@', '').lower()
        
        # Load existing birthdays
        birthdays = self.load_birthdays()
        
        # Check if user exists
        if username_to_delete not in birthdays:
            return f"User @{username_to_delete} not found in birthday database."
        
        # Show existing data before deletion
        existing = birthdays[username_to_delete]
        existing_age = self.calculate_age(existing['date'])
        
        # Delete the birthday
        del birthdays[username_to_delete]
        self.save_birthdays(birthdays)
        
        return f"<blockquote expandable>✅ Birthday deleted for @{username_to_delete}!\nDeleted data:\nBirthday: {existing['date']}\nTimezone: {existing['timezone']}\nAge: {existing_age}</blockquote>"
    
    def handle_list_birthdays_command(self, sender_name):
        """Handle /list_birthdays command"""
        # Load existing birthdays
        birthdays = self.load_birthdays()
        
        if not birthdays:
            return "No birthdays stored in the database."
        
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
            formatted_date = birth_date.strftime('%b %d, %Y')  # e.g., "Mar 15, 1990"
            birthday_list.append(f"{username}: {formatted_date} ({data['timezone']}) - Age: {age}")
        
        total_count = len(birthdays)
        header = f"📋 Birthday Database ({total_count} users):\n\n<blockquote expandable>"
        
        return header + "\n".join(birthday_list) + "</blockquote>"
    
    def handle_add_birthday_message_command(self, args, sender_name, sender_username):
        """Handle /add_birthday_message command"""
        if not args.strip():
            return "<blockquote expandable>Please provide message details.\nFormats:\n• /add_birthday_message random \"Your message with {username} and {age}\"\n• /add_birthday_message user username \"User-specific message\"</blockquote>"
        
        # Use existing logic from process_add_birthday_message
        fake_text = f"add_birthday_message {args}"
        return self.process_add_birthday_message(fake_text, sender_name, sender_username)
    
    def handle_list_birthday_messages_command(self, sender_name, sender_username):
        """Handle /list_birthday_messages command"""
        return self.process_list_birthday_messages(sender_name, sender_username)
    
    def handle_delete_birthday_message_command(self, args, sender_name, sender_username):
        """Handle /delete_birthday_message command"""
        if not args.strip():
            return "<blockquote expandable>Please specify what to delete.\nFormats:\n• /delete_birthday_message random [number]\n• /delete_birthday_message user [username]</blockquote>"
        
        # Use existing logic from process_delete_birthday_message
        fake_text = f"delete_birthday_message {args}"
        return self.process_delete_birthday_message(fake_text, sender_name, sender_username)
    
    def send_message(self, chat_id, text, reply_to_message_id=None, disable_web_page_preview=False, 
                    parse_mode=None, reply_markup=None):
        """Send message via Telegram Bot API"""
        try:
            import requests
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode or 'HTML'
            }
            
            if reply_to_message_id:
                data['reply_to_message_id'] = reply_to_message_id
            
            if disable_web_page_preview:
                data['disable_web_page_preview'] = True
            
            if reply_markup:
                data['reply_markup'] = reply_markup
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Message sent successfully to chat {chat_id}")
                return result.get('result', True)  # Return the message object for message_id
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def process_webhook_update(self, update):
        """Process incoming webhook update"""
        try:
            # Handle callback queries (inline keyboard button presses)
            callback_query = update.get('callback_query')
            if callback_query:
                self.process_callback_query(callback_query)
                return
            
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
            
            # Process slash commands
            reply_text = self.process_slash_command(text, sender_name, sender_username, sender_id, chat_id)
            if reply_text:
                # Mark as processed
                self.processed_messages.add(msg_key)
                
                # Send reply (disable web page preview for all help messages)
                is_help_message = ("/help" in text.lower() or "/start" in text.lower() or 
                                 "/quiz_help" in text.lower() or "Commands:" in reply_text)
                success = self.send_message(chat_id, reply_text, message_id, disable_web_page_preview=is_help_message)
                if success:
                    logger.info(f"Successfully processed and replied to message {msg_key}")
                    # Save processed messages periodically
                    if len(self.processed_messages) % 10 == 0:
                        self.save_processed_messages()
                else:
                    logger.error(f"Failed to send reply for message {msg_key}")
            
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
    
    def process_callback_query(self, callback_query):
        """Process callback query from inline keyboard buttons"""
        try:
            if not self.quiz_manager:
                return
            
            callback_data = callback_query.get('data', '')
            user = callback_query.get('from', {})
            message = callback_query.get('message', {})
            
            user_id = user.get('id')
            username = user.get('username') or f"user_{user_id}"
            chat_id = message.get('chat', {}).get('id')
            message_id = message.get('message_id')
            
            # Parse callback data using QuizUI
            from quiz.quiz_ui import QuizUI
            quiz_ui = QuizUI(self)
            parsed_data = quiz_ui.parse_callback_data(callback_data)
            
            if not parsed_data:
                # Not a quiz callback, ignore
                return
            
            # Extract quiz callback data
            question_idx = parsed_data['question_idx']
            option_idx = parsed_data['option_idx']
            
            # Get the current question to find the selected answer
            current_question = self.quiz_manager.get_current_question(chat_id)
            if not current_question or current_question.get('question_index') != question_idx:
                # Question mismatch or no active quiz
                self.answer_callback_query(callback_query['id'], "❌ This question is no longer active.")
                return
            
            options = current_question.get('options', [])
            if option_idx >= len(options):
                self.answer_callback_query(callback_query['id'], "❌ Invalid option selected.")
                return
            
            selected_answer = options[option_idx]
            
            # Process the answer
            result = self.quiz_manager.process_answer(chat_id, user_id, username, question_idx, selected_answer)
            
            if result['success']:
                # Update the question message with result
                quiz_ui.update_question_result(chat_id, message_id, result)
                
                if result['is_correct']:
                    callback_message = f"✅ Correct! +{result['points_awarded']} point"
                else:
                    callback_message = f"❌ Wrong answer. Correct: {result['correct_answer']}"
                
                self.answer_callback_query(callback_query['id'], callback_message)
                
                # Check if quiz is complete or send next question
                if result.get('quiz_complete'):
                    # Send final leaderboard
                    final_leaderboard = result.get('final_leaderboard', {})
                    if final_leaderboard.get('success'):
                        quiz_ui.send_leaderboard(
                            chat_id, 
                            final_leaderboard['leaderboard'], 
                            final_leaderboard['quiz_info'], 
                            is_final=True
                        )
                elif result.get('next_question'):
                    # Send next question
                    next_question = result['next_question']
                    quiz_status = self.quiz_manager.get_quiz_status(chat_id)
                    current_q_num = quiz_status.get('answered_questions', 0) + 1
                    total_questions = quiz_status.get('total_questions', 0)
                    quiz_ui.send_question(chat_id, next_question, current_q_num, total_questions)
            else:
                # Answer processing failed
                error_message = quiz_ui.format_error_message(result['error_type'], result['error'])
                if result['error_type'] == 'already_answered':
                    self.answer_callback_query(callback_query['id'], "⏰ Too late! Someone else answered first.")
                elif result['error_type'] == 'already_attempted':
                    self.answer_callback_query(callback_query['id'], "🚫 You already tried this question!")
                else:
                    self.answer_callback_query(callback_query['id'], "❌ Error processing answer.")
                    
        except Exception as e:
            logger.error(f"Error processing callback query: {e}")
            try:
                self.answer_callback_query(callback_query.get('id'), "❌ An error occurred.")
            except:
                pass
    
    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        """Answer a callback query (acknowledge button press)"""
        try:
            import requests
            
            url = f"{self.telegram_api_url}/answerCallbackQuery"
            data = {
                'callback_query_id': callback_query_id,
                'show_alert': show_alert
            }
            
            if text:
                data['text'] = text
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to answer callback query: {response.text}")
                
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
    
    def edit_message_text(self, chat_id, message_id, text, parse_mode=None):
        """Edit an existing message via Telegram Bot API"""
        try:
            import requests
            url = f"{self.telegram_api_url}/editMessageText"
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': text,
                'parse_mode': parse_mode or 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.debug(f"Message {message_id} edited successfully in chat {chat_id}")
                return response.json().get('result', True)
            else:
                logger.error(f"Failed to edit message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False
    
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
    
    def set_bot_commands(self):
        """Set bot commands using Telegram's setMyCommands API"""
        try:
            import requests
            
            # Basic commands for all users
            basic_commands = [
                {"command": "start", "description": "Start the bot and show help"},
                {"command": "help", "description": "Show available commands"},
                {"command": "archive", "description": "Archive a URL"},
                {"command": "birthday_set", "description": "Set your birthday"},
                {"command": "layla", "description": "Send a random Layla image"},
                {"command": "bored", "description": "Get a random activity suggestion"},
                {"command": "bored_type", "description": "Get activity by type (education, social, etc.)"},
                {"command": "bored_participants", "description": "Get activity by number of people"},
                {"command": "bored_price", "description": "Get activity by price range (free, low, high)"},
                {"command": "age_guess", "description": "Guess someone's age based on their name"},
                {"command": "xkcd_latest", "description": "Get the latest XKCD comic"},
                {"command": "xkcd_random", "description": "Get a random XKCD comic"},
                {"command": "xkcd_number", "description": "Get a specific XKCD comic by number"},
                {"command": "iss", "description": "Get current location and crew of the International Space Station"}
            ]
            
            # Admin commands for special users
            admin_commands = [
                {"command": "start", "description": "Start the bot and show help"},
                {"command": "help", "description": "Show available commands"},
                {"command": "archive", "description": "Archive a URL"},
                {"command": "birthday_set", "description": "Set your birthday"},
                {"command": "layla", "description": "Send a random Layla image"},
                {"command": "bored", "description": "Get a random activity suggestion"},
                {"command": "bored_type", "description": "Get activity by type (education, social, etc.)"},
                {"command": "bored_participants", "description": "Get activity by number of people"},
                {"command": "bored_price", "description": "Get activity by price range (free, low, high)"},
                {"command": "age_guess", "description": "Guess someone's age based on their name"},
                {"command": "xkcd_latest", "description": "Get the latest XKCD comic"},
                {"command": "xkcd_random", "description": "Get a random XKCD comic"},
                {"command": "xkcd_number", "description": "Get a specific XKCD comic by number"},
                {"command": "iss", "description": "Get current location and crew of the International Space Station"},
                {"command": "test_birthday", "description": "Send test birthday message"},
                {"command": "delete_birthday", "description": "Delete a user's birthday"},
                {"command": "list_birthdays", "description": "List all stored birthdays"},
                {"command": "add_birthday_message", "description": "Add custom birthday message"},
                {"command": "list_birthday_messages", "description": "View all birthday messages"},
                {"command": "delete_birthday_message", "description": "Delete birthday message"}
            ]
            
            # Set admin commands globally (all users will see them, but we'll check permissions)
            # This is more reliable than trying to set user-specific commands
            url = f"{self.telegram_api_url}/setMyCommands"
            data = {'commands': admin_commands}
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                logger.info("Bot commands set successfully (admin commands visible to all)")
            else:
                logger.error(f"Failed to set commands: {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting bot commands: {e}")
            return False
    
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
        
        # Set bot commands
        if self.set_bot_commands():
            logger.info("Bot commands configured successfully")
        else:
            logger.warning("Failed to configure bot commands")
        
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