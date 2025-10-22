#!/usr/bin/env python3
"""
Manual Archive Processor
Run this script with a message to process it and send the reply
"""

import re
import requests
import sys
from datetime import datetime

def extract_urls(text):
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

def create_archive_url(url):
    """Create latest snapshot archive URL"""
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    current_year = datetime.now().year
    return f"https://archive.ph/{current_year}/{url}"

def submit_and_archive(url):
    """Submit URL and return archive link"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        print(f"📦 Submitting {url} to archive.ph...")
        
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
                    print(f"✅ New archive created: {redirect_url}")
                    return redirect_url
        except Exception as e:
            print(f"Submission error: {e}")
        
        # Fallback to latest snapshot URL
        latest_url = create_archive_url(url)
        print(f"📁 Using latest snapshot URL: {latest_url}")
        return latest_url
        
    except Exception as e:
        print(f"Error: {e}")
        return create_archive_url(url)

def process_message(text, sender_name="User"):
    """Process message and return reply"""
    if "@angel_dimi_bot" not in text.lower():
        return None
    
    print(f"📨 Processing archive request from {sender_name}")
    
    urls = extract_urls(text)
    if not urls:
        return f"@{sender_name} I didn't find any URLs to archive in your message."
    
    archived_results = []
    for url in urls:
        archived_url = submit_and_archive(url)
        archived_results.append(f"📁 {url}\n   → {archived_url}")
    
    return f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)

def send_reply_via_mcp(reply_text, chat_id=7104815701):
    """Send reply using MCP (placeholder)"""
    print(f"💬 Sending reply to chat {chat_id}:")
    print("=" * 50)
    print(reply_text)
    print("=" * 50)
    
    # Here you would use the actual MCP call:
    # mcp_telegram_mcp_send_message(chat_id=chat_id, message=reply_text)
    
    return True

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python manual_archive.py '<message>'")
        print("Example: python manual_archive.py '@Angel_Dimi_Bot archive https://github.com'")
        return
    
    message = " ".join(sys.argv[1:])
    print(f"Input message: {message}")
    
    reply = process_message(message, "User")
    
    if reply:
        print("\n🤖 Generated Reply:")
        send_reply_via_mcp(reply)
        
        # Optionally send via MCP automatically
        # Uncomment the next line to actually send:
        # mcp_telegram_mcp_send_message(chat_id=7104815701, message=reply)
        
    else:
        print("ℹ️  No reply needed (bot not mentioned)")

if __name__ == "__main__":
    main()