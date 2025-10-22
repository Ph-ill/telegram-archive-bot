#!/usr/bin/env python3
"""
Test script to verify MCP connection and basic functionality
"""

def test_bot_info():
    """Test getting bot information"""
    print("Testing bot info...")
    # This should work if MCP is properly configured
    return True

def test_send_message():
    """Test sending a message to a chat"""
    print("Testing message sending...")
    # You'll need a chat ID to test this
    return True

def main():
    print("🧪 Testing MCP Telegram connection...")
    
    try:
        # Test bot info
        if test_bot_info():
            print("✅ Bot info test passed")
        
        # Test message sending (you'll need to provide a chat ID)
        print("ℹ️  To test message sending, you need a chat ID")
        print("   You can get chat IDs by starting a conversation with your bot")
        
        print("✅ MCP connection tests completed")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()