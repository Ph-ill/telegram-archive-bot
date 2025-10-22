#!/usr/bin/env python3
"""
Telegram Archive Bot Handler
Processes messages mentioning the bot and archives links
"""

import re
import requests
import json
import time
from datetime import datetime, timedelta

class ArchiveBotHandler:
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
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def is_bot_mentioned(self, text):
        """Check if the bot is mentioned in the message"""
        return f"@{self.bot_username}" in text.lower()
    
    def archive_url(self, url):
        """Archive a URL using archive.ph"""
        try:
            print(f"Archiving: {url}")
            
            # Submit URL to archive.ph
            archive_url = "https://archive.ph/"
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.post(archive_url, data=data, headers=headers, allow_redirects=False, timeout=30)
            
            # archive.ph redirects to the archived page
            if response.status_code == 302:
                archived_url = response.headers.get('Location')
                if archived_url and archived_url.startswith('https://archive.ph/'):
                    print(f"✅ Archived: {url} -> {archived_url}")
                    return archived_url
            
            print(f"❌ Failed to archive {url}. Status: {response.status_code}")
            return None
            
        except Exception as e:
            print(f"❌ Error archiving {url}: {str(e)}")
            return None
    
    def process_message(self, message, chat_info):
        """Process a single message"""
        message_id = message.get('id')
        text = message.get('text', '')
        sender = message.get('sender', {})
        sender_name = sender.get('first_name', 'User')
        chat_id = chat_info.get('id')
        
        # Create unique message identifier
        msg_key = f"{chat_id}_{message_id}"
        
        # Skip if already processed
        if msg_key in self.processed_messages:
            return False
        
        # Check if bot is mentioned
        if not self.is_bot_mentioned(text):
            return False
        
        print(f"Processing message from {sender_name}: {text[:100]}...")
        
        # Mark as processed
        self.processed_messages.add(msg_key)
        
        # Extract URLs from the message
        urls = self.extract_urls(text)
        
        if not urls:
            reply_text = f"@{sender_name} I didn't find any URLs to archive in your message."
            return self.send_reply(chat_id, message_id, reply_text)
        
        # Process each URL
        archived_urls = []
        for url in urls:
            archived_url = self.archive_url(url)
            if archived_url:
                archived_urls.append(f"📁 {url}\n   → {archived_url}")
            else:
                archived_urls.append(f"❌ Failed to archive: {url}")
        
        # Send reply with archived URLs
        if archived_urls:
            reply_text = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_urls)
            return self.send_reply(chat_id, message_id, reply_text)
        
        return True
    
    def send_reply(self, chat_id, message_id, text):
        """Send a reply to a message using MCP tools"""
        # This function will be called by the main script using MCP tools
        return {
            'action': 'reply',
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text
        }
    
    def check_recent_messages(self, hours_back=1):
        """Check for recent messages mentioning the bot"""
        replies_to_send = []
        
        # This will be implemented in the main script
        return replies_to_send

# Test the URL archiving function
if __name__ == "__main__":
    handler = ArchiveBotHandler()
    
    # Test archiving
    test_url = "https://example.com"
    result = handler.archive_url(test_url)
    print(f"Test result: {result}")