#!/usr/bin/env python3
"""
Webhook-style Archive Bot
Since bot tokens can't easily read messages, this provides manual processing
"""

import re
import requests
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

def create_latest_archive_url(url):
    """Create archive URL that redirects to latest snapshot"""
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    current_year = datetime.now().year
    return f"https://archive.ph/{current_year}/{url}"

def submit_and_archive(url):
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
        
        # Return latest snapshot URL as fallback
        return create_latest_archive_url(url)
        
    except Exception as e:
        return create_latest_archive_url(url)

def process_archive_request(text, sender_name="User"):
    """Process a message for archive requests"""
    if "@angel_dimi_bot" not in text.lower():
        return None
    
    urls = extract_urls(text)
    if not urls:
        return f"@{sender_name} I didn't find any URLs to archive in your message."
    
    archived_results = []
    for url in urls:
        archived_url = submit_and_archive(url)
        archived_results.append(f"📁 {url}\n   → {archived_url}")
    
    return f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)

# Test the functionality
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        reply = process_archive_request(message, "User")
        if reply:
            print("Bot Reply:")
            print(reply)
        else:
            print("No reply (bot not mentioned)")
    else:
        # Test with sample message
        test_message = "@Angel_Dimi_Bot please archive https://github.com"
        reply = process_archive_request(test_message, "TestUser")
        print("Test Reply:")
        print(reply)