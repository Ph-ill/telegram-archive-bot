#!/usr/bin/env python3
"""
Test archive functionality and send result via MCP
"""

import re
import requests
from datetime import datetime

def create_direct_archive_url(url):
    """Create direct archive URL"""
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    # Simple approach - just reference all snapshots
    return f"https://archive.ph/{url}"

def submit_and_get_archive_url(url):
    """Submit to archive.ph and return URL"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        # Submit to archive
        data = {'url': url}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://archive.ph',
            'Referer': 'https://archive.ph/'
        }
        
        response = requests.post("https://archive.ph/", data=data, headers=headers, 
                               allow_redirects=False, timeout=30)
        
        # Check for successful redirect
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            if redirect_url and 'archive.ph' in redirect_url:
                return redirect_url
        
        # Fallback to direct URL
        return create_direct_archive_url(url)
        
    except Exception as e:
        # Fallback to direct URL
        return create_direct_archive_url(url)

# Test with example.com
test_url = "https://example.com"
archive_result = submit_and_get_archive_url(test_url)

print(f"Original: {test_url}")
print(f"Archive: {archive_result}")

# Test message processing
def process_message(text, sender="User"):
    """Process message for archive requests"""
    if "@angel_dimi_bot" not in text.lower():
        return None
    
    # Extract URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    
    if not urls:
        return f"@{sender} I didn't find any URLs to archive."
    
    results = []
    for url in urls:
        archived = submit_and_get_archive_url(url)
        results.append(f"📁 {url}\n   → {archived}")
    
    return f"@{sender} Here are your archived links:\n\n" + "\n\n".join(results)

# Test message
test_message = "@Angel_Dimi_Bot please archive https://github.com"
reply = process_message(test_message, "TestUser")
print(f"\nTest message: {test_message}")
print(f"Bot reply: {reply}")