#!/usr/bin/env python3
"""
Telegram Archive Bot
Monitors messages for links and archives them using archive.ph
"""

import re
import time
import requests
from urllib.parse import urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramArchiveBot:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
        self.processed_messages = set()  # Track processed messages to avoid duplicates
        
    def extract_urls(self, text):
        """Extract URLs from text message"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        return urls
    
    def is_bot_mentioned(self, text):
        """Check if the bot is mentioned in the message"""
        return f"@{self.bot_username}" in text
    
    def archive_url(self, url):
        """Archive a URL using archive.ph"""
        try:
            # Submit URL to archive.ph
            archive_url = "https://archive.ph/"
            data = {'url': url}
            
            response = requests.post(archive_url, data=data, allow_redirects=False)
            
            # archive.ph redirects to the archived page
            if response.status_code == 302:
                archived_url = response.headers.get('Location')
                if archived_url:
                    logger.info(f"Successfully archived {url} -> {archived_url}")
                    return archived_url
            
            logger.error(f"Failed to archive {url}. Status: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error archiving {url}: {str(e)}")
            return None
    
    def process_message(self, chat_id, message_id, text, sender_name):
        """Process a message that mentions the bot"""
        # Create unique message identifier
        msg_key = f"{chat_id}_{message_id}"
        
        # Skip if already processed
        if msg_key in self.processed_messages:
            return
            
        self.processed_messages.add(msg_key)
        
        # Extract URLs from the message
        urls = self.extract_urls(text)
        
        if not urls:
            # Reply that no URLs were found
            reply_text = f"@{sender_name} I didn't find any URLs to archive in your message."
            return self.send_reply(chat_id, message_id, reply_text)
        
        # Process each URL
        archived_urls = []
        for url in urls:
            archived_url = self.archive_url(url)
            if archived_url:
                archived_urls.append(f"📁 {url} → {archived_url}")
            else:
                archived_urls.append(f"❌ Failed to archive: {url}")
        
        # Send reply with archived URLs
        reply_text = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_urls)
        self.send_reply(chat_id, message_id, reply_text)
    
    def send_reply(self, chat_id, message_id, text):
        """Send a reply to a message"""
        # This will be implemented using MCP tools
        pass
    
    def run(self):
        """Main bot loop"""
        logger.info(f"Starting {self.bot_username} archive bot...")
        
        # Get initial chats to monitor
        last_message_time = time.time()
        
        while True:
            try:
                # This is a simplified polling approach
                # In a real implementation, you'd want to use webhooks or proper polling
                time.sleep(5)  # Check every 5 seconds
                
                # Get recent chats and check for new messages
                # This will be implemented with MCP tools
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(10)  # Wait before retrying

if __name__ == "__main__":
    bot = TelegramArchiveBot()
    bot.run()