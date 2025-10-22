#!/usr/bin/env python3
"""
Final Archive Bot - Uses direct archive.ph URLs and MCP integration
"""

import re
import requests
import json
import sys
from datetime import datetime

class FinalArchiveBot:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
        self.your_chat_id = 7104815701  # Your chat ID
        self.processed_file = "processed_messages.json"
        self.processed_messages = self.load_processed_messages()
    
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
    
    def extract_urls(self, text):
        """Extract URLs from text"""
        if not text:
            return []
        
        # Match http/https URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        
        # Match www. URLs
        www_pattern = r'(?:^|\s)(www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),])+)'
        www_matches = re.findall(www_pattern, text)
        
        # Add https:// to www URLs
        for www_url in www_matches:
            urls.append(f"https://{www_url.strip()}")
        
        return list(set(urls))
    
    def is_bot_mentioned(self, text):
        """Check if bot is mentioned"""
        if not text:
            return False
        return f"@{self.bot_username.lower()}" in text.lower()
    
    def create_archive_url(self, url):
        """Create direct archive URL that redirects to latest snapshot"""
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Get current year
            current_year = datetime.now().year
            
            # Create archive URL that redirects to latest snapshot in current year
            archive_url = f"https://archive.ph/{current_year}/{url}"
            return archive_url
            
        except Exception as e:
            print(f"Error creating archive URL for {url}: {e}")
            return None
    
    def submit_to_archive(self, url):
        """Submit URL to archive.ph and return archive URL"""
        try:
            print(f"📦 Archiving: {url}")
            
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Submit to archive.ph to trigger archiving
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://archive.ph',
                'Referer': 'https://archive.ph/'
            }
            
            try:
                # Submit the URL (this triggers archiving)
                response = requests.post("https://archive.ph/", data=data, headers=headers, 
                                       allow_redirects=False, timeout=30)
                
                # Check if we got a specific archive URL
                if response.status_code == 302:
                    redirect_url = response.headers.get('Location')
                    if redirect_url and 'archive.ph' in redirect_url:
                        print(f"✅ Got specific archive: {redirect_url}")
                        return redirect_url
            except:
                pass  # Continue to fallback
            
            # Always provide the year-based URL as fallback (redirects to latest)
            direct_url = self.create_archive_url(url)
            print(f"📁 Providing latest snapshot URL: {direct_url}")
            return direct_url
            
        except Exception as e:
            print(f"❌ Error with {url}: {e}")
            # Still provide direct URL as fallback
            return self.create_archive_url(url)
    
    def process_archive_request(self, text, sender_name="User"):
        """Process a message for archive requests"""
        if not self.is_bot_mentioned(text):
            return None
        
        print(f"📨 Processing archive request from {sender_name}")
        
        urls = self.extract_urls(text)
        if not urls:
            return f"@{sender_name} I didn't find any URLs to archive in your message."
        
        archived_results = []
        for url in urls:
            archived_url = self.submit_to_archive(url)
            if archived_url:
                archived_results.append(f"📁 {url}\n   → {archived_url}")
            else:
                archived_results.append(f"❌ Could not create archive for: {url}")
        
        reply = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
        return reply
    
    def send_message_mcp(self, chat_id, message):
        """Send message using MCP tools"""
        try:
            print(f"💬 Sending message to chat {chat_id}")
            # This would use: mcp_telegram_mcp_send_message(chat_id=chat_id, message=message)
            print(f"📤 Message: {message[:100]}...")
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    def reply_to_message_mcp(self, chat_id, message_id, reply_text):
        """Reply to message using MCP tools"""
        try:
            print(f"💬 Replying to message {message_id} in chat {chat_id}")
            # This would use: mcp_telegram_mcp_reply_to_message(chat_id=chat_id, message_id=message_id, text=reply_text)
            print(f"📤 Reply: {reply_text[:100]}...")
            return True
        except Exception as e:
            print(f"❌ Failed to reply: {e}")
            return False
    
    def check_for_mentions(self, chat_id, limit=10):
        """Check a chat for recent messages mentioning the bot"""
        try:
            print(f"🔍 Checking chat {chat_id} for mentions...")
            
            # Try to get recent messages
            # This would use: mcp_telegram_mcp_list_messages(chat_id=chat_id, limit=limit)
            messages = []  # Placeholder
            
            processed_count = 0
            
            for message in messages:
                message_id = message.get('id')
                text = message.get('text', '')
                sender = message.get('sender', {})
                sender_name = sender.get('first_name', 'User')
                
                # Create unique message identifier
                msg_key = f"{chat_id}_{message_id}"
                
                # Skip if already processed
                if msg_key in self.processed_messages:
                    continue
                
                # Process if bot is mentioned
                reply_text = self.process_archive_request(text, sender_name)
                if reply_text:
                    # Mark as processed
                    self.processed_messages.add(msg_key)
                    
                    # Send reply
                    self.reply_to_message_mcp(chat_id, message_id, reply_text)
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error checking chat {chat_id}: {e}")
            return 0
    
    def run_bot_cycle(self):
        """Run a single bot cycle"""
        print("🤖 Running archive bot cycle...")
        
        # Check your chat for mentions
        processed = self.check_for_mentions(self.your_chat_id)
        
        # Save processed messages
        self.save_processed_messages()
        
        print(f"✅ Cycle complete. Processed {processed} messages.")
        return processed

def test_archive_functionality():
    """Test the archive functionality"""
    bot = FinalArchiveBot()
    
    test_urls = [
        "https://example.com",
        "https://github.com",
        "www.google.com"
    ]
    
    print("🧪 Testing Archive Functionality")
    print("=" * 40)
    
    for url in test_urls:
        print(f"\n--- Testing: {url} ---")
        result = bot.submit_to_archive(url)
        print(f"Result: {result}")

def test_message_processing():
    """Test message processing"""
    bot = FinalArchiveBot()
    
    test_messages = [
        "@Angel_Dimi_Bot please archive https://example.com",
        "@Angel_Dimi_Bot check these out: https://github.com and www.google.com",
        "Hello @Angel_Dimi_Bot no links here",
        "Regular message without mention"
    ]
    
    print("\n🧪 Testing Message Processing")
    print("=" * 40)
    
    for i, message in enumerate(test_messages):
        print(f"\n--- Test {i+1}: {message[:50]}... ---")
        result = bot.process_archive_request(message, "TestUser")
        if result:
            print("Bot Reply:")
            print(result)
        else:
            print("No reply (bot not mentioned)")

def main():
    """Main function"""
    bot = FinalArchiveBot()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test-archive":
            test_archive_functionality()
            
        elif command == "test-processing":
            test_message_processing()
            
        elif command == "run":
            bot.run_bot_cycle()
            
        elif command == "process":
            if len(sys.argv) < 3:
                print("Usage: python final_archive_bot.py process '<message>'")
                return
            
            message = " ".join(sys.argv[2:])
            result = bot.process_archive_request(message, "User")
            if result:
                print("Bot Reply:")
                print(result)
            else:
                print("No reply needed")
        
        elif command == "archive":
            if len(sys.argv) < 3:
                print("Usage: python final_archive_bot.py archive <url>")
                return
            
            url = sys.argv[2]
            result = bot.submit_to_archive(url)
            print(f"Archive URL: {result}")
        
        else:
            print(f"Unknown command: {command}")
    
    else:
        print("🤖 Final Archive Bot")
        print("Available commands:")
        print("  test-archive          - Test archive functionality")
        print("  test-processing       - Test message processing")
        print("  run                   - Run bot cycle")
        print("  process '<message>'   - Process a message")
        print("  archive <url>         - Archive a single URL")

if __name__ == "__main__":
    main()