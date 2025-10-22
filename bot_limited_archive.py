#!/usr/bin/env python3
"""
Archive Bot for Bot Token (Limited API Access)
This version works with the restrictions of bot tokens
"""

import re
import requests
import json
from datetime import datetime

class BotLimitedArchive:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
        self.processed_file = "processed_messages.json"
        self.chat_ids_file = "known_chat_ids.json"
        self.processed_messages = self.load_processed_messages()
        self.known_chat_ids = self.load_known_chat_ids()
    
    def load_processed_messages(self):
        """Load previously processed message IDs"""
        try:
            with open(self.processed_file, 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()
    
    def save_processed_messages(self):
        """Save processed message IDs"""
        with open(self.processed_file, 'w') as f:
            json.dump(list(self.processed_messages), f)
    
    def load_known_chat_ids(self):
        """Load known working chat IDs"""
        try:
            with open(self.chat_ids_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_known_chat_ids(self):
        """Save known working chat IDs"""
        with open(self.chat_ids_file, 'w') as f:
            json.dump(self.known_chat_ids, f, indent=2)
    
    def add_known_chat_id(self, chat_id, description):
        """Add a working chat ID to our known list"""
        self.known_chat_ids[str(chat_id)] = {
            "description": description,
            "added_date": datetime.now().isoformat(),
            "last_used": None
        }
        self.save_known_chat_ids()
        print(f"✅ Added chat ID {chat_id}: {description}")
    
    def extract_urls(self, text):
        """Extract URLs from text message"""
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
        """Check if the bot is mentioned in the message"""
        if not text:
            return False
        return f"@{self.bot_username.lower()}" in text.lower()
    
    def archive_url(self, url):
        """Archive a URL using archive.ph"""
        try:
            print(f"📦 Archiving: {url}")
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            archive_endpoint = "https://archive.ph/"
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://archive.ph',
                'Referer': 'https://archive.ph/'
            }
            
            response = requests.post(archive_endpoint, data=data, headers=headers, 
                                   allow_redirects=False, timeout=30)
            
            if response.status_code == 302:
                archived_url = response.headers.get('Location')
                if archived_url and 'archive.ph' in archived_url:
                    print(f"✅ Archived: {archived_url}")
                    return archived_url
            
            print(f"❌ Failed to archive {url} (Status: {response.status_code})")
            return None
            
        except Exception as e:
            print(f"❌ Error archiving {url}: {str(e)}")
            return None
    
    def test_chat_id(self, chat_id):
        """Test if we can send messages to a chat ID"""
        try:
            print(f"🧪 Testing chat ID: {chat_id}")
            # This would use MCP: mcp_telegram_mcp_send_message(chat_id=chat_id, message="Test")
            print(f"   This would test sending to chat {chat_id}")
            return True
        except Exception as e:
            print(f"❌ Chat ID {chat_id} failed: {e}")
            return False
    
    def check_chat_for_messages(self, chat_id, limit=10):
        """Check a specific chat for recent messages (if bot has access)"""
        try:
            print(f"🔍 Checking chat {chat_id} for messages...")
            # This would use MCP: mcp_telegram_mcp_get_messages(chat_id=chat_id, page_size=limit)
            # or: mcp_telegram_mcp_list_messages(chat_id=chat_id, limit=limit)
            
            # For now, return empty list
            messages = []
            
            processed_count = 0
            for message in messages:
                if self.process_message_for_mentions(message, chat_id):
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error checking chat {chat_id}: {e}")
            return 0
    
    def process_message_for_mentions(self, message, chat_id):
        """Process a message for bot mentions and archive links"""
        try:
            message_id = message.get('id')
            text = message.get('text', '')
            sender = message.get('sender', {})
            sender_name = sender.get('first_name', 'User')
            
            msg_key = f"{chat_id}_{message_id}"
            
            if msg_key in self.processed_messages:
                return False
            
            if not self.is_bot_mentioned(text):
                return False
            
            print(f"📨 Processing mention from {sender_name}: {text[:100]}...")
            
            self.processed_messages.add(msg_key)
            
            urls = self.extract_urls(text)
            
            if not urls:
                reply_text = f"@{sender_name} I didn't find any URLs to archive in your message."
            else:
                archived_results = []
                for url in urls:
                    archived_url = self.archive_url(url)
                    if archived_url:
                        archived_results.append(f"📁 {url}\n   → {archived_url}")
                    else:
                        archived_results.append(f"❌ Failed to archive: {url}")
                
                reply_text = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
            
            # Send reply using MCP
            self.send_reply_to_chat(chat_id, message_id, reply_text)
            return True
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            return False
    
    def send_reply_to_chat(self, chat_id, message_id, text):
        """Send a reply to a specific message"""
        try:
            print(f"💬 Sending reply to chat {chat_id}...")
            # This would use MCP: mcp_telegram_mcp_reply_to_message(chat_id=chat_id, message_id=message_id, text=text)
            print(f"📤 Would send: {text[:50]}...")
            return True
        except Exception as e:
            print(f"❌ Failed to send reply: {e}")
            return False
    
    def run_check_cycle(self):
        """Run a check cycle on all known chat IDs"""
        print("🤖 Starting archive bot check cycle...")
        
        if not self.known_chat_ids:
            print("❌ No known chat IDs to check!")
            print("   Use add_chat_id() to add chat IDs first")
            return
        
        total_processed = 0
        
        for chat_id_str, info in self.known_chat_ids.items():
            chat_id = int(chat_id_str)
            print(f"\n📋 Checking {info['description']} (ID: {chat_id})")
            
            processed = self.check_chat_for_messages(chat_id)
            total_processed += processed
            
            if processed > 0:
                # Update last used time
                self.known_chat_ids[chat_id_str]["last_used"] = datetime.now().isoformat()
        
        self.save_known_chat_ids()
        self.save_processed_messages()
        
        print(f"\n✅ Check cycle completed! Processed {total_processed} messages.")

def main():
    """Main function with interactive options"""
    bot = BotLimitedArchive()
    
    print("🤖 Telegram Archive Bot - Bot Token Version")
    print("=" * 45)
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "add-chat":
            if len(sys.argv) < 4:
                print("Usage: python bot_limited_archive.py add-chat <chat_id> <description>")
                return
            
            chat_id = int(sys.argv[2])
            description = " ".join(sys.argv[3:])
            bot.add_known_chat_id(chat_id, description)
            
        elif command == "test-chat":
            if len(sys.argv) < 3:
                print("Usage: python bot_limited_archive.py test-chat <chat_id>")
                return
            
            chat_id = int(sys.argv[2])
            bot.test_chat_id(chat_id)
            
        elif command == "list-chats":
            print("Known chat IDs:")
            for chat_id, info in bot.known_chat_ids.items():
                print(f"  {chat_id}: {info['description']}")
                if info.get('last_used'):
                    print(f"    Last used: {info['last_used']}")
            
        elif command == "run":
            bot.run_check_cycle()
            
        elif command == "test-archive":
            if len(sys.argv) < 3:
                print("Usage: python bot_limited_archive.py test-archive <url>")
                return
            
            url = sys.argv[2]
            result = bot.archive_url(url)
            if result:
                print(f"✅ Archive successful: {result}")
            else:
                print("❌ Archive failed")
        
        else:
            print(f"Unknown command: {command}")
    
    else:
        print("Available commands:")
        print("  add-chat <chat_id> <description>  - Add a known chat ID")
        print("  test-chat <chat_id>               - Test sending to a chat ID")
        print("  list-chats                        - List known chat IDs")
        print("  run                               - Run check cycle")
        print("  test-archive <url>                - Test URL archiving")

if __name__ == "__main__":
    main()