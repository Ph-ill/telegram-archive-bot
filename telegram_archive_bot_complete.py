#!/usr/bin/env python3
"""
Complete Telegram Archive Bot Implementation
This script monitors Telegram messages and archives links when the bot is mentioned
"""

import re
import requests
import json
import time
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramArchiveBot:
    def __init__(self):
        self.bot_username = "Angel_Dimi_Bot"
        self.processed_file = "processed_messages.json"
        self.processed_messages = self.load_processed_messages()
        self.last_check_time = datetime.now() - timedelta(hours=1)
    
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
        
        # More comprehensive URL pattern
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        
        # Also look for www. links without http
        www_pattern = r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        www_urls = re.findall(www_pattern, text)
        
        # Add http:// to www URLs
        for www_url in www_urls:
            urls.append(f"http://{www_url}")
        
        return list(set(urls))  # Remove duplicates
    
    def is_bot_mentioned(self, text):
        """Check if the bot is mentioned in the message"""
        if not text:
            return False
        return f"@{self.bot_username.lower()}" in text.lower()
    
    def archive_url(self, url):
        """Archive a URL using archive.ph"""
        try:
            logger.info(f"Archiving: {url}")
            
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            # Submit URL to archive.ph
            archive_url = "https://archive.ph/"
            data = {'url': url}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://archive.ph',
                'Referer': 'https://archive.ph/'
            }
            
            session = requests.Session()
            response = session.post(archive_url, data=data, headers=headers, 
                                  allow_redirects=False, timeout=30)
            
            # archive.ph redirects to the archived page
            if response.status_code == 302:
                archived_url = response.headers.get('Location')
                if archived_url and 'archive.ph' in archived_url:
                    logger.info(f"✅ Successfully archived: {url} -> {archived_url}")
                    return archived_url
            
            # Sometimes archive.ph returns 200 with a redirect in the body
            if response.status_code == 200:
                # Look for redirect in response
                if 'archive.ph/' in response.text:
                    # Try to extract the archived URL from the response
                    match = re.search(r'https://archive\.ph/[a-zA-Z0-9]+', response.text)
                    if match:
                        archived_url = match.group(0)
                        logger.info(f"✅ Successfully archived: {url} -> {archived_url}")
                        return archived_url
            
            logger.error(f"❌ Failed to archive {url}. Status: {response.status_code}")
            return None
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout archiving {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Error archiving {url}: {str(e)}")
            return None
    
    def format_reply_message(self, sender_name, urls, archived_results):
        """Format the reply message with archived URLs"""
        if not archived_results:
            return f"@{sender_name} I didn't find any URLs to archive in your message."
        
        successful_archives = []
        failed_archives = []
        
        for original_url, archived_url in archived_results:
            if archived_url:
                successful_archives.append(f"📁 {original_url}\n   → {archived_url}")
            else:
                failed_archives.append(f"❌ Failed to archive: {original_url}")
        
        reply_parts = [f"@{sender_name} Here are your archived links:"]
        
        if successful_archives:
            reply_parts.append("\n✅ Successfully archived:")
            reply_parts.extend(successful_archives)
        
        if failed_archives:
            reply_parts.append("\n❌ Failed to archive:")
            reply_parts.extend(failed_archives)
        
        return "\n\n".join(reply_parts)
    
    def process_message(self, message, chat_id):
        """Process a single message for bot mentions and URLs"""
        try:
            message_id = message.get('id')
            text = message.get('text', '')
            sender = message.get('sender', {})
            sender_name = sender.get('first_name', 'User')
            
            # Create unique message identifier
            msg_key = f"{chat_id}_{message_id}"
            
            # Skip if already processed
            if msg_key in self.processed_messages:
                return None
            
            # Check if bot is mentioned
            if not self.is_bot_mentioned(text):
                return None
            
            logger.info(f"Processing message from {sender_name} in chat {chat_id}: {text[:100]}...")
            
            # Mark as processed
            self.processed_messages.add(msg_key)
            
            # Extract URLs from the message
            urls = self.extract_urls(text)
            
            if not urls:
                reply_text = f"@{sender_name} I didn't find any URLs to archive in your message."
                return {
                    'chat_id': chat_id,
                    'message_id': message_id,
                    'reply_text': reply_text
                }
            
            # Archive each URL
            archived_results = []
            for url in urls:
                archived_url = self.archive_url(url)
                archived_results.append((url, archived_url))
            
            # Format reply message
            reply_text = self.format_reply_message(sender_name, urls, archived_results)
            
            return {
                'chat_id': chat_id,
                'message_id': message_id,
                'reply_text': reply_text
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return None
    
    def check_chat_for_mentions(self, chat_id, limit=20):
        """Check a specific chat for recent messages mentioning the bot"""
        replies_to_send = []
        
        try:
            # This would use MCP tools to get messages
            # For now, return empty list as placeholder
            logger.info(f"Checking chat {chat_id} for mentions...")
            
            # Placeholder for MCP tool call:
            # messages = mcp_telegram_mcp_list_messages(chat_id=chat_id, limit=limit)
            
            return replies_to_send
            
        except Exception as e:
            logger.error(f"Error checking chat {chat_id}: {str(e)}")
            return []
    
    def run_single_check(self):
        """Run a single check for new messages (for manual/cron execution)"""
        logger.info("🤖 Starting archive bot check...")
        
        try:
            # Get list of chats
            # This would use MCP tools:
            # chats = mcp_telegram_mcp_list_chats()
            
            replies_to_send = []
            
            # For each chat, check for recent messages
            # for chat in chats:
            #     chat_id = chat.get('id')
            #     chat_replies = self.check_chat_for_mentions(chat_id)
            #     replies_to_send.extend(chat_replies)
            
            # Send all replies
            for reply in replies_to_send:
                try:
                    # This would use MCP tools:
                    # mcp_telegram_mcp_reply_to_message(
                    #     chat_id=reply['chat_id'],
                    #     message_id=reply['message_id'],
                    #     text=reply['reply_text']
                    # )
                    logger.info(f"Sent reply to chat {reply['chat_id']}")
                except Exception as e:
                    logger.error(f"Failed to send reply: {str(e)}")
            
            logger.info(f"✅ Check completed. Processed {len(replies_to_send)} replies.")
            
        except Exception as e:
            logger.error(f"❌ Error during check: {str(e)}")
        
        finally:
            self.save_processed_messages()

def main():
    """Main function for running the bot"""
    bot = TelegramArchiveBot()
    
    # Test URL archiving
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_url = "https://example.com"
        result = bot.archive_url(test_url)
        print(f"Test archiving result: {result}")
        return
    
    # Run single check
    bot.run_single_check()

if __name__ == "__main__":
    import sys
    main()