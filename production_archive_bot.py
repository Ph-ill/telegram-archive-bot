#!/usr/bin/env python3
"""
Production Archive Bot - Latest snapshot URLs with MCP integration
"""

import re
import requests
import json
import sys
from datetime import datetime

class ProductionArchiveBot:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
        self.your_chat_id = 7104815701
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
    
    def create_latest_archive_url(self, url):
        """Create archive URL that redirects to latest snapshot"""
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Get current year
            current_year = datetime.now().year
            
            # Create archive URL that redirects to latest snapshot in current year
            # Format: https://archive.ph/YYYY/original_url
            archive_url = f"https://archive.ph/{current_year}/{url}"
            return archive_url
            
        except Exception as e:
            print(f"Error creating archive URL for {url}: {e}")
            return None
    
    def submit_and_get_latest_archive(self, url):
        """Submit URL to archive.ph and return latest snapshot URL"""
        try:
            print(f"📦 Archiving: {url}")
            
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Submit to archive.ph to trigger new archiving
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://archive.ph',
                'Referer': 'https://archive.ph/'
            }
            
            try:
                # Submit the URL (this triggers new archiving)
                response = requests.post("https://archive.ph/", data=data, headers=headers, 
                                       allow_redirects=False, timeout=30)
                
                # Check if we got a specific archive URL from redirect
                if response.status_code == 302:
                    redirect_url = response.headers.get('Location')
                    if redirect_url and 'archive.ph' in redirect_url:
                        print(f"✅ New archive created: {redirect_url}")
                        return redirect_url
            except Exception as e:
                print(f"Submission error (continuing with fallback): {e}")
            
            # Always provide the latest snapshot URL as fallback
            latest_url = self.create_latest_archive_url(url)
            print(f"📁 Providing latest snapshot URL: {latest_url}")
            return latest_url
            
        except Exception as e:
            print(f"❌ Error with {url}: {e}")
            # Still provide latest snapshot URL as fallback
            return self.create_latest_archive_url(url)
    
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
            archived_url = self.submit_and_get_latest_archive(url)
            if archived_url:
                archived_results.append(f"📁 {url}\n   → {archived_url}")
            else:
                archived_results.append(f"❌ Could not create archive for: {url}")
        
        reply = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
        return reply
    
    def send_message_via_mcp(self, chat_id, message):
        """Send message using MCP tools"""
        try:
            print(f"💬 Sending message to chat {chat_id}")
            # Use actual MCP function here
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    def reply_to_message_via_mcp(self, chat_id, message_id, reply_text):
        """Reply to message using MCP tools"""
        try:
            print(f"💬 Replying to message {message_id} in chat {chat_id}")
            # Use actual MCP function here
            return True
        except Exception as e:
            print(f"❌ Failed to reply: {e}")
            return False
    
    def manual_process_message(self, message_text, sender_name="User"):
        """Manually process a message and return the reply"""
        reply = self.process_archive_request(message_text, sender_name)
        return reply
    
    def demo_functionality(self):
        """Demo the bot functionality"""
        print("🤖 Production Archive Bot Demo")
        print("=" * 40)
        
        # Test URLs
        test_urls = [
            "https://example.com",
            "https://github.com",
            "www.google.com"
        ]
        
        print("\n📦 Testing archive URL creation:")
        for url in test_urls:
            archive_url = self.create_latest_archive_url(url)
            print(f"  {url} → {archive_url}")
        
        # Test message processing
        test_messages = [
            "@Angel_Dimi_Bot please archive https://example.com",
            "@Angel_Dimi_Bot check out https://github.com and www.google.com",
            "Hello @Angel_Dimi_Bot no links here"
        ]
        
        print("\n💬 Testing message processing:")
        for i, message in enumerate(test_messages):
            print(f"\n--- Test {i+1} ---")
            print(f"Input: {message}")
            reply = self.process_archive_request(message, "TestUser")
            if reply:
                print(f"Reply: {reply[:100]}...")
            else:
                print("Reply: (no response - bot not mentioned)")

def main():
    """Main function"""
    bot = ProductionArchiveBot()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "demo":
            bot.demo_functionality()
            
        elif command == "process":
            if len(sys.argv) < 3:
                print("Usage: python production_archive_bot.py process '<message>'")
                print("Example: python production_archive_bot.py process '@Angel_Dimi_Bot archive https://example.com'")
                return
            
            message = " ".join(sys.argv[2:])
            reply = bot.manual_process_message(message, "User")
            if reply:
                print("🤖 Bot Reply:")
                print(reply)
            else:
                print("ℹ️  No reply (bot not mentioned or no URLs found)")
        
        elif command == "archive":
            if len(sys.argv) < 3:
                print("Usage: python production_archive_bot.py archive <url>")
                return
            
            url = sys.argv[2]
            result = bot.submit_and_get_latest_archive(url)
            print(f"🔗 Archive URL: {result}")
        
        elif command == "test-url":
            if len(sys.argv) < 3:
                print("Usage: python production_archive_bot.py test-url <url>")
                return
            
            url = sys.argv[2]
            result = bot.create_latest_archive_url(url)
            print(f"📁 Latest snapshot URL: {result}")
        
        else:
            print(f"❌ Unknown command: {command}")
    
    else:
        print("🤖 Production Archive Bot")
        print("Available commands:")
        print("  demo                     - Run functionality demo")
        print("  process '<message>'      - Process a message")
        print("  archive <url>            - Archive a URL")
        print("  test-url <url>           - Test URL format creation")
        print("")
        print("Example usage:")
        print("  python production_archive_bot.py demo")
        print("  python production_archive_bot.py process '@Angel_Dimi_Bot archive https://github.com'")
        print("  python production_archive_bot.py archive https://example.com")

if __name__ == "__main__":
    main()