#!/usr/bin/env python3
"""
Simple test to archive a URL and send the result to your chat
"""

import requests
import re

def archive_url(url):
    """Archive a URL using archive.ph"""
    try:
        print(f"Archiving: {url}")
        
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
        print(f"Error: {e}")
        return None

# Test archiving
test_url = "https://github.com"
archived = archive_url(test_url)

if archived:
    print(f"Success! {test_url} -> {archived}")
else:
    print("Failed to archive")