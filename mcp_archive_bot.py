#!/usr/bin/env python3
"""
MCP Archive Bot - Direct implementation using MCP tools
"""

import re
import requests
import sys

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

def archive_url(url):
    """Archive a URL using archive.ph"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        data = {'url': url}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://archive.ph',
            'Referer': 'https://archive.ph/'
        }
        
        response = requests.post("https://archive.ph/", data=data, headers=headers, 
                               allow_redirects=False, timeout=30)
        
        if response.status_code == 302:
            archived_url = response.headers.get('Location')
            if archived_url and 'archive.ph' in archived_url:
                return archived_url
        
        return None
        
    except Exception as e:
        return None

def process_archive_request(text, sender_name="User"):
    """Process a message for archive requests"""
    if "@angel_dimi_bot" not in text.lower():
        return None
    
    urls = extract_urls(text)
    if not urls:
        return f"@{sender_name} I didn't find any URLs to archive in your message."
    
    archived_results = []
    for url in urls:
        archived_url = archive_url(url)
        if archived_url:
            archived_results.append(f"📁 {url}\n   → {archived_url}")
        else:
            archived_results.append(f"❌ Failed to archive: {url}")
    
    reply = f"@{sender_name} Here are your archived links:\n\n" + "\n\n".join(archived_results)
    return reply

# Test the functionality
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test with command line argument
        test_message = " ".join(sys.argv[1:])
        result = process_archive_request(test_message, "TestUser")
        print(result if result else "No archive request found")
    else:
        # Test with sample message
        test_message = "@Angel_Dimi_Bot please archive https://example.com"
        result = process_archive_request(test_message, "TestUser")
        print(result if result else "No archive request found")