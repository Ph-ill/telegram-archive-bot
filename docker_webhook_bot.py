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
            return None, "Invalid format. Use:\n@Angel_Dimi_Bot birthday set YYYY-MM-DD Timezone [username]\n\nExamples:\n• @Angel_Dimi_Bot birthday set 1990-03-15 America/New_York (uses your username/ID)\n• @Angel_Dimi_Bot birthday set 1990-03-15 America/New_York john (sets for specific user)"
        
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
                return f"@{sender_name} ✅ Your birthday has been saved!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}"
            else:
                return f"@{sender_name} ✅ Birthday saved for @{target_username}!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}"
        
        elif "delete_birthday" in text.lower():
            # Only special users can delete birthdays
            special_users = ["racistwaluigi", "kokorozasu"]
            if sender_username.lower() not in special_users:
                return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can delete birthdays."
            
            # Parse delete command
            delete_result = self.parse_delete_birthday_command(text)
            if delete_result is None:
                return f"@{sender_name} Invalid format. Use: @Angel_Dimi_Bot delete_birthday @username\nExample: @Angel_Dimi_Bot delete_birthday @john"
            
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
        
        # Try user-specific message format
        user_pattern = r'add_birthday_message\s+user\s+(\w+)\s+"([^"]+)"'
        user_match = re.search(user_pattern, text, re.IGNORECASE)
        
        if random_match:
            message_template = random_match.group(1)
            messages = self.load_birthday_messages()
            messages["random_messages"].append(message_template)
            self.save_birthday_messages(messages)
            return f"@{sender_name} ✅ Random birthday message added!\nMessage: {message_template}"
        
        elif user_match:
            target_user = user_match.group(1).lower()
            message_template = user_match.group(2)
            messages = self.load_birthday_messages()
            messages["user_specific"][target_user] = message_template
            self.save_birthday_messages(messages)
            return f"@{sender_name} ✅ User-specific birthday message added for @{target_user}!\nMessage: {message_template}"
        
        else:
            return f"@{sender_name} Invalid format. Use:\n• @Angel_Dimi_Bot add_birthday_message random \"Your message with {{username}} and {{age}}\"\n• @Angel_Dimi_Bot add_birthday_message user username \"User-specific message with {{username}} and {{age}}\"\n\nNote: Use {{username}} and {{age}} as placeholders in your message."
    
    def process_list_birthday_messages(self, sender_name, sender_username):
        """Process list birthday messages command"""
        # Only special users can view birthday messages
        special_users = ["racistwaluigi", "kokorozasu"]
        if sender_username.lower() not in special_users:
            return f"@{sender_name} Only @RacistWaluigi and @kokorozasu can view birthday messages."
        
        messages = self.load_birthday_messages()
        
        result = f"@{sender_name} 📝 Birthday Messages:\n\n"
        
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
        
        # Try user-specific message deletion
        user_pattern = r'delete_birthday_message\s+user\s+(\w+)'
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
            return f"@{sender_name} Invalid format. Use:\n• @Angel_Dimi_Bot delete_birthday_message random [number]\n• @Angel_Dimi_Bot delete_birthday_message user [username]\n\nUse list_birthday_messages to see available messages."
    
    def get_help_message(self, sender_name, sender_username):
        """Generate help message with available commands"""
        special_users = ["racistwaluigi", "kokorozasu"]
        is_special_user = sender_username.lower() in special_users
        
        help_text = f"🤖 Angel Dimi Bot Commands:\n\n> "
        
        # Archive commands (available to everyone)
        help_text += "📁 Archive Commands:\n> "
        help_text += "• /archive <URL> - Archive a link\n> "
        help_text += "  Example: /archive https://example.com\n> \n> "
        
        # Birthday commands (available to everyone for self)
        help_text += "🎂 Birthday Commands:\n> "
        help_text += "• /birthday_set <YYYY-MM-DD> <Timezone> [username] - Set birthday\n> "
        help_text += "  Example: /birthday_set 1990-03-15 America/New_York\n> "
        help_text += "• /test_birthday - Send test birthday message\n> \n> "
        
        # Special user commands
        if is_special_user:
            help_text += "👑 Admin Commands (Special Users Only):\n> "
            help_text += "• /delete_birthday <username> - Delete a birthday\n> "
            help_text += "• /list_birthdays - List all stored birthdays\n> "
            help_text += "• /add_birthday_message random \"message\" - Add random birthday message\n> "
            help_text += "• /add_birthday_message user <username> \"message\" - Add user-specific message\n> "
            help_text += "• /list_birthday_messages - View all birthday messages\n> "
            help_text += "• /delete_birthday_message random <number> - Delete random message\n> "
            help_text += "• /delete_birthday_message user <username> - Delete user message\n> "
            help_text += "• Can set birthdays for any user\n> \n> "
        
        # Additional info
        help_text += "📝 Notes:\n> "
        help_text += "• Use / to see all available commands in your chat\n> "
        help_text += "• Works in groups and private messages\n> "
        help_text += "• Birthday alerts sent to group at midnight in your timezone\n> "
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
    
    def process_slash_command(self, text, sender_name="User", sender_username=None, sender_id=None, chat_id=None):
        """Process slash commands"""
        if not text.startswith('/'):
            return None
        
        # Parse command and arguments
        parts = text.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        logger.info(f"Processing slash command '{command}' from {sender_name}")
        
        # Route commands to appropriate handlers
        if command == "/help":
            return self.get_help_message(sender_name, sender_username)
        
        elif command == "/archive":
            return self.handle_archive_command(args, sender_name)
        
        elif command == "/birthday_set":
            return self.handle_birthday_set_command(args, sender_name, sender_username, sender_id)
        
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
            return "Please provide birthday information.\nFormat: /birthday_set YYYY-MM-DD Timezone [username]\nExample: /birthday_set 1990-03-15 America/New_York"
        
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
            return f"✅ Your birthday has been saved!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}"
        else:
            return f"✅ Birthday saved for @{target_username}!\nBirthday: {birthday_data['date']}\nTimezone: {birthday_data['timezone']}\nCurrent age: {age}{update_message}"
    
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
            return "Please specify a username.\nFormat: /delete_birthday username\nExample: /delete_birthday john"
        
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
        
        return f"✅ Birthday deleted for @{username_to_delete}!\nDeleted data:\nBirthday: {existing['date']}\nTimezone: {existing['timezone']}\nAge: {existing_age}"
    
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
            formatted_date = birth_date.strftime('%B %d, %Y')  # e.g., "March 15, 1990"
            birthday_list.append(f"{username}: {formatted_date} ({data['timezone']}) - Age: {age}")
        
        total_count = len(birthdays)
        header = f"📋 Birthday Database ({total_count} users):\n\n"
        
        return header + "\n".join(birthday_list)
    
    def handle_add_birthday_message_command(self, args, sender_name, sender_username):
        """Handle /add_birthday_message command"""
        if not args.strip():
            return "Please provide message details.\nFormats:\n• /add_birthday_message random \"Your message with {username} and {age}\"\n• /add_birthday_message user username \"User-specific message\""
        
        # Use existing logic from process_add_birthday_message
        fake_text = f"add_birthday_message {args}"
        return self.process_add_birthday_message(fake_text, sender_name, sender_username)
    
    def handle_list_birthday_messages_command(self, sender_name, sender_username):
        """Handle /list_birthday_messages command"""
        return self.process_list_birthday_messages(sender_name, sender_username)
    
    def handle_delete_birthday_message_command(self, args, sender_name, sender_username):
        """Handle /delete_birthday_message command"""
        if not args.strip():
            return "Please specify what to delete.\nFormats:\n• /delete_birthday_message random [number]\n• /delete_birthday_message user [username]"
        
        # Use existing logic from process_delete_birthday_message
        fake_text = f"delete_birthday_message {args}"
        return self.process_delete_birthday_message(fake_text, sender_name, sender_username)
    
    def send_message(self, chat_id, text, reply_to_message_id=None, disable_web_page_preview=False):
        """Send message via Telegram Bot API"""
        try:
            import requests
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text
            }
            
            if reply_to_message_id:
                data['reply_to_message_id'] = reply_to_message_id
            
            if disable_web_page_preview:
                data['disable_web_page_preview'] = True
            
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
            
            # Process slash commands
            reply_text = self.process_slash_command(text, sender_name, sender_username, sender_id, chat_id)
            if reply_text:
                # Mark as processed
                self.processed_messages.add(msg_key)
                
                # Send reply (disable web page preview for help messages)
                is_help_message = "Angel Dimi Bot Commands:" in reply_text
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
                {"command": "help", "description": "Show available commands"},
                {"command": "archive", "description": "Archive a URL"},
                {"command": "birthday_set", "description": "Set your birthday"}
            ]
            
            # Admin commands for special users
            admin_commands = [
                {"command": "help", "description": "Show available commands"},
                {"command": "archive", "description": "Archive a URL"},
                {"command": "birthday_set", "description": "Set your birthday"},
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