#!/usr/bin/env python3
"""
Telegram Archive Bot using MCP tools
Run this script to check for messages mentioning the bot and archive any links
"""

import re
import requests
import json
import sys
from datetime import datetime

class ArchiveBotMCP:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
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
        """Extract URLs from text message"""
        if not text:
            return []
        
        # URL pattern to match http/https URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        
        # Also look for www. links without http
        www_pattern = r'(?:^|\s)(www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),])+)'
        www_matches = re.findall(www_pattern, text)
        
        # Add https:// to www URLs
        for www_url in www_matches:
            urls.append(f"https://{www_url.strip()}")
        
        return list(set(urls))  # Remove duplicates
    
    def is_bot_mentioned(self, text):
        """Check if the bot is mentioned in the message"""
        if not text:
            return False
        return f"@{self.bot_username.lower()}" in text.lower()
    
    def archive_url(self, url):
        """Archive a URL using archive.ph"""
        try:
            print(f"📦 Archiving: {url}")
            
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Submit URL to archive.ph
            archive_endpoint = "https://archive.ph/"
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://archive.ph',
                'Referer': 'https://archive.ph/'
            }
            
            response = requests.post(archive_endpoint, data=data, headers=headers, 
                                   allow_redirects=False, timeout=30)
            
            # archive.ph redirects to the archived page
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
    
    def process_chat_messages(self, chat_id, limit=20):
        """Process recent messages in a chat for bot mentions"""
        print(f"🔍 Checking chat {chat_id} for mentions...")
        
        processed_count = 0
        
        try:
            # Get recent messages from the chat
            # Note: This is a placeholder - you'll need to implement the actual MCP call
            messages = []  # mcp_telegram_mcp_list_messages(chat_id=chat_id, limit=limit)
            
            for message in messages:
                if self.process_single_message(message, chat_id):
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error processing chat {chat_id}: {str(e)}")
            return 0
    
    def process_single_message(self, message, chat_id):
        """Process a single message"""
        try:
            message_id = message.get('id')
            text = message.get('text', '')
            sender = message.get('sender', {})
            sender_name = sender.get('first_name', 'User')
            
            # Create unique message identifier
            msg_key = f"{chat_id}_{message_id}"
            
            # Skip if already processed
            if msg_key in self.processed_messages:
                return False
            
            # Check if bot is mentioned
            if not self.is_bot_mentioned(text):
                return False
            
            print(f"📨 Processing mention from {sender_name}: {text[:100]}...")
            
            # Mark as processed
            self.processed_messages.add(msg_key)
            
            # Extract URLs
            urls = self.extract_urls(text)
            
            if not urls:
                reply_text = f"@{sender_name} I didn't find any URLs to archive in your message."
            else:
                # Archive URLs
                archived_results = []
                for url in urls:
                    archived_url = self.archive_url(url)
                    if archived_url:
                        archived_results.append(f"📁 {url}\n   → {archived_url}")
                    else:
                        archived_results.append(f"❌ Failed to archive: {url}")
                
                reply_text = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
            
            # Send reply
            self.send_reply(chat_id, message_id, reply_text)
            return True
            
        except Exception as e:
            print(f"❌ Error processing message: {str(e)}")
            return False
    
    def send_reply(self, chat_id, message_id, text):
        """Send a reply to a message"""
        try:
            print(f"💬 Sending reply to chat {chat_id}...")
            # Note: This is a placeholder - you'll need to implement the actual MCP call
            # mcp_telegram_mcp_reply_to_message(chat_id=chat_id, message_id=message_id, text=text)
            print(f"📤 Reply sent: {text[:50]}...")
            return True
        except Exception as e:
            print(f"❌ Failed to send reply: {str(e)}")
            return False

def main():
    """Main function"""
    bot = ArchiveBotMCP()
    
    print("🤖 Telegram Archive Bot - MCP Version")
    print("=====================================")
    
    # Test URL archiving if requested
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_url = input("Enter URL to test archiving: ").strip()
        if test_url:
            result = bot.archive_url(test_url)
            if result:
                print(f"✅ Test successful: {result}")
            else:
                print("❌ Test failed")
        return
    
    try:
        # Get list of chats where bot is present
        print("📋 Getting chat list...")
        # chats = mcp_telegram_mcp_list_chats(limit=50)
        
        # For now, you can manually specify chat IDs to monitor
        # Replace these with actual chat IDs where your bot is present
        chat_ids_to_monitor = []
        
        if not chat_ids_to_monitor:
            print("ℹ️  No chat IDs specified to monitor.")
            print("   To use this bot:")
            print("   1. Add your bot to chats/groups")
            print("   2. Get the chat IDs using MCP tools")
            print("   3. Add them to the chat_ids_to_monitor list in this script")
            return
        
        total_processed = 0
        
        for chat_id in chat_ids_to_monitor:
            processed = bot.process_chat_messages(chat_id)
            total_processed += processed
        
        print(f"✅ Completed! Processed {total_processed} messages with bot mentions.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    finally:
        bot.save_processed_messages()
        print("💾 Saved processed messages state")

if __name__ == "__main__":
    main()