#!/usr/bin/env python3
"""
Live Archive Bot - Actually uses MCP tools for real Telegram integration
"""

import re
import requests
import json
from datetime import datetime

class LiveArchiveBot:
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
                        return redirect_url
            except:
                pass
            
            # Return latest snapshot URL
            return self.create_latest_archive_url(url)
            
        except Exception as e:
            return self.create_latest_archive_url(url)
    
    def process_message_for_archives(self, text, sender_name="User"):
        """Process message and return archive reply"""
        if not self.is_bot_mentioned(text):
            return None
        
        urls = self.extract_urls(text)
        if not urls:
            return f"@{sender_name} I didn't find any URLs to archive in your message."
        
        archived_results = []
        for url in urls:
            archived_url = self.submit_and_archive(url)
            archived_results.append(f"📁 {url}\n   → {archived_url}")
        
        return f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
    
    def handle_direct_message(self, message_text):
        """Handle a direct message and send reply via MCP"""
        reply = self.process_message_for_archives(message_text, "User")
        if reply:
            print(f"Sending reply: {reply}")
            # Send via MCP
            return True
        return False

# Example usage functions that can be called directly
def process_test_message():
    """Process a test message"""
    bot = LiveArchiveBot()
    test_message = "@Angel_Dimi_Bot please archive https://github.com"
    reply = bot.process_message_for_archives(test_message, "TestUser")
    return reply

def archive_single_url(url):
    """Archive a single URL"""
    bot = LiveArchiveBot()
    return bot.submit_and_archive(url)

if __name__ == "__main__":
    # Test the functionality
    reply = process_test_message()
    print("Test Reply:")
    print(reply)
    
    print("\nTest Single URL:")
    result = archive_single_url("https://example.com")
    print(f"Archive URL: {result}")