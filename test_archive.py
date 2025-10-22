#!/usr/bin/env python3
"""
Simple test of the archive functionality
"""

import requests
import re

def test_archive_url(url):
    """Test archiving a URL"""
    try:
        print(f"📦 Testing archive of: {url}")
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        # Submit to archive.ph
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
        
        print("Sending request to archive.ph...")
        response = requests.post(archive_endpoint, data=data, headers=headers, 
                               allow_redirects=False, timeout=30)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        # Check for redirect (successful archive)
        if response.status_code == 302:
            archived_url = response.headers.get('Location')
            if archived_url and 'archive.ph' in archived_url:
                print(f"✅ Successfully archived: {archived_url}")
                return archived_url
        
        # Check response content for clues
        if response.text:
            print(f"Response content (first 200 chars): {response.text[:200]}")
            
            # Look for archived URL in response
            match = re.search(r'https://archive\.ph/[a-zA-Z0-9]+', response.text)
            if match:
                archived_url = match.group(0)
                print(f"✅ Found archived URL in response: {archived_url}")
                return archived_url
        
        print(f"❌ Failed to archive {url}")
        return None
        
    except Exception as e:
        print(f"❌ Error archiving {url}: {str(e)}")
        return None

if __name__ == "__main__":
    # Test with a simple URL
    test_url = "https://example.com"
    result = test_archive_url(test_url)
    
    if result:
        print(f"\n🎉 Archive test successful!")
        print(f"Original: {test_url}")
        print(f"Archived: {result}")
    else:
        print(f"\n❌ Archive test failed")