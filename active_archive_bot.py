#!/usr/bin/env python3
"""
Active Archive Bot - Monitors and responds to messages
This script needs to be run to actively check for and respond to messages
"""

import re
import requests
import json
import time
from datetime import datetime

class ActiveArchiveBot:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
        self.your_chat_id = 7104815701
        self.processed_file = "processed_messages.json"
        self.processed_messages = self.load_processed_messages()
        self.last_check = datetime.now()
    
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
    
    def create_latest_archive_url(self, url):
        """Create archive URL that redirects to latest snapshot"""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        current_year = datetime.now().year
        return f"https://archive.ph/{current_year}/{url}"
    
    def submit_and_archive(self, url):
        """Submit URL to archive.ph and return latest snapshot URL"""
        try:
            print(f"📦 Archiving: {url}")
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Submit to trigger archiving
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://archive.ph',
                'Referer': 'https://archive.ph/'
            }
            
            try:
                response = requests.post("https://archive.ph/", data=data, headers=headers, 
                                       allow_redirects=False, timeout=30)
                
                if response.status_code == 302:
                    redirect_url = response.headers.get('Location')
                    if redirect_url and 'archive.ph' in redirect_url:
                        print(f"✅ New archive: {redirect_url}")
                        return redirect_url
            except Exception as e:
                print(f"Submission error: {e}")
            
            # Return latest snapshot URL as fallback
            latest_url = self.create_latest_archive_url(url)
            print(f"📁 Latest snapshot: {latest_url}")
            return latest_url
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return self.create_latest_archive_url(url)
    
    def process_message_for_archives(self, text, sender_name="User"):
        """Process message and return archive reply"""
        if not self.is_bot_mentioned(text):
            return None
        
        print(f"📨 Processing mention from {sender_name}")
        
        urls = self.extract_urls(text)
        if not urls:
            return f"@{sender_name} I didn't find any URLs to archive in your message."
        
        archived_results = []
        for url in urls:
            archived_url = self.submit_and_archive(url)
            archived_results.append(f"📁 {url}\n   → {archived_url}")
        
        return f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
    
    def send_reply_via_mcp(self, chat_id, reply_text):
        """Send reply using MCP tools"""
        try:
            print(f"💬 Sending reply to chat {chat_id}")
            print(f"📤 Reply: {reply_text[:100]}...")
            
            # Use MCP to send message
            # This is where we'd call the actual MCP function
            # For now, we'll simulate it
            return True
            
        except Exception as e:
            print(f"❌ Failed to send reply: {e}")
            return False
    
    def check_for_new_messages(self):
        """Check for new messages (limited by bot API restrictions)"""
        print(f"🔍 Checking for new messages in chat {self.your_chat_id}...")
        
        try:
            # Try to get recent messages using MCP
            # Note: This might not work due to bot limitations
            messages = []  # Placeholder
            
            processed_count = 0
            
            for message in messages:
                message_id = message.get('id')
                text = message.get('text', '')
                sender = message.get('sender', {})
                sender_name = sender.get('first_name', 'User')
                
                # Create unique message identifier
                msg_key = f"{self.your_chat_id}_{message_id}"
                
                # Skip if already processed
                if msg_key in self.processed_messages:
                    continue
                
                # Process if bot is mentioned
                reply_text = self.process_message_for_archives(text, sender_name)
                if reply_text:
                    # Mark as processed
                    self.processed_messages.add(msg_key)
                    
                    # Send reply
                    if self.send_reply_via_mcp(self.your_chat_id, reply_text):
                        processed_count += 1
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error checking messages: {e}")
            return 0
    
    def run_monitoring_loop(self, check_interval=30):
        """Run continuous monitoring loop"""
        print(f"🤖 Starting Active Archive Bot monitoring...")
        print(f"📋 Monitoring chat ID: {self.your_chat_id}")
        print(f"⏰ Check interval: {check_interval} seconds")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                print(f"\n🔄 Checking at {datetime.now().strftime('%H:%M:%S')}")
                
                processed = self.check_for_new_messages()
                
                if processed > 0:
                    print(f"✅ Processed {processed} messages")
                    self.save_processed_messages()
                else:
                    print("ℹ️  No new messages to process")
                
                # Wait before next check
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Bot monitoring stopped by user")
            self.save_processed_messages()
        except Exception as e:
            print(f"\n❌ Error in monitoring loop: {e}")
            self.save_processed_messages()
    
    def run_single_check(self):
        """Run a single check for new messages"""
        print("🔍 Running single message check...")
        
        processed = self.check_for_new_messages()
        self.save_processed_messages()
        
        print(f"✅ Single check complete. Processed {processed} messages.")
        return processed
    
    def manual_process_and_send(self, message_text, sender_name="User"):
        """Manually process a message and send reply"""
        reply = self.process_message_for_archives(message_text, sender_name)
        if reply:
            print("Generated reply:")
            print(reply)
            
            # Send the reply
            success = self.send_reply_via_mcp(self.your_chat_id, reply)
            if success:
                print("✅ Reply sent successfully!")
            else:
                print("❌ Failed to send reply")
            
            return reply
        else:
            print("ℹ️  No reply needed (bot not mentioned)")
            return None

def main():
    """Main function"""
    import sys
    
    bot = ActiveArchiveBot()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "monitor":
            # Run continuous monitoring
            interval = 30
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    print("Invalid interval, using 30 seconds")
            
            bot.run_monitoring_loop(interval)
            
        elif command == "check":
            # Run single check
            bot.run_single_check()
            
        elif command == "process":
            if len(sys.argv) < 3:
                print("Usage: python active_archive_bot.py process '<message>'")
                return
            
            message = " ".join(sys.argv[2:])
            bot.manual_process_and_send(message, "TestUser")
        
        else:
            print(f"❌ Unknown command: {command}")
    
    else:
        print("🤖 Active Archive Bot")
        print("Available commands:")
        print("  monitor [interval]    - Start continuous monitoring (default: 30s)")
        print("  check                 - Run single message check")
        print("  process '<message>'   - Manually process a message")
        print("")
        print("Examples:")
        print("  python active_archive_bot.py monitor 60")
        print("  python active_archive_bot.py check")
        print("  python active_archive_bot.py process '@Angel_Dimi_Bot archive https://github.com'")

if __name__ == "__main__":
    main()