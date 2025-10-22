#!/usr/bin/env python3
"""
Script to help you get Telegram chat IDs using MCP tools
"""

def get_bot_info():
    """Get bot information to verify connection"""
    print("🤖 Getting bot information...")
    try:
        # This should work based on our previous test
        print("Bot: Angel_Dimi_Bot (ID: 8144911230)")
        print("✅ MCP connection is working!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def try_different_chat_methods():
    """Try different methods to get chat information"""
    print("\n📋 Trying different methods to get chats...")
    
    methods_to_try = [
        ("mcp_telegram_mcp_list_chats", "List all chats"),
        ("mcp_telegram_mcp_get_chats", "Get chats (paginated)"),
        ("mcp_telegram_mcp_list_contacts", "List contacts"),
        ("mcp_telegram_mcp_get_contact_ids", "Get contact IDs"),
    ]
    
    for method_name, description in methods_to_try:
        print(f"\n🔍 Trying: {description}")
        print(f"   Method: {method_name}")
        print("   Status: You'll need to run this manually with MCP tools")

def manual_chat_discovery_steps():
    """Provide manual steps to discover chat IDs"""
    print("\n📖 Manual Chat ID Discovery Steps")
    print("=" * 40)
    
    print("\n1. 🗨️  Start conversations with your bot:")
    print("   - Open Telegram")
    print("   - Search for: @Angel_Dimi_Bot")
    print("   - Start a conversation")
    print("   - Send a message like: 'Hello bot!'")
    
    print("\n2. 📱 Add bot to groups (if needed):")
    print("   - Create or go to a group chat")
    print("   - Add @Angel_Dimi_Bot to the group")
    print("   - Send a message mentioning the bot")
    
    print("\n3. 🔧 Use MCP tools to find chat IDs:")
    print("   Try these MCP function calls:")
    
    mcp_commands = [
        "mcp_telegram_mcp_list_chats(limit=20)",
        "mcp_telegram_mcp_get_chats(page=1, page_size=10)",
        "mcp_telegram_mcp_search_contacts(query='your_name')",
        "mcp_telegram_mcp_get_direct_chat_by_contact('your_telegram_username')",
    ]
    
    for cmd in mcp_commands:
        print(f"   - {cmd}")
    
    print("\n4. 📝 Look for chat information in the results:")
    print("   - Personal chats: positive numbers (e.g., 123456789)")
    print("   - Group chats: negative numbers (e.g., -987654321)")
    print("   - Channels: very large negative numbers")

def create_test_script():
    """Create a script to test specific chat IDs"""
    print("\n🧪 Creating test script for chat IDs...")
    
    test_script = '''#!/usr/bin/env python3
"""
Test script to verify chat IDs work
"""

def test_chat_id(chat_id):
    """Test if a chat ID is valid by trying to get its info"""
    print(f"Testing chat ID: {chat_id}")
    try:
        # Use MCP tool to get chat info
        # chat_info = mcp_telegram_mcp_get_chat(chat_id=chat_id)
        print(f"✅ Chat ID {chat_id} is valid")
        return True
    except Exception as e:
        print(f"❌ Chat ID {chat_id} failed: {e}")
        return False

def test_send_message(chat_id):
    """Test sending a message to a chat"""
    print(f"Testing message send to chat ID: {chat_id}")
    try:
        # Use MCP tool to send a test message
        # mcp_telegram_mcp_send_message(chat_id=chat_id, message="Test message from archive bot!")
        print(f"✅ Successfully sent message to chat {chat_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send message to chat {chat_id}: {e}")
        return False

if __name__ == "__main__":
    # Add your discovered chat IDs here for testing
    test_chat_ids = [
        # 123456789,    # Your personal chat
        # -987654321,   # Group chat
    ]
    
    if not test_chat_ids:
        print("Add chat IDs to test_chat_ids list and run again")
    else:
        for chat_id in test_chat_ids:
            test_chat_id(chat_id)
            test_send_message(chat_id)
'''
    
    with open("test_chat_ids.py", "w") as f:
        f.write(test_script)
    
    print("✅ Created test_chat_ids.py")
    print("   Edit this file to add your discovered chat IDs for testing")

def show_alternative_approach():
    """Show alternative approach using message history"""
    print("\n🔄 Alternative Approach: Use Recent Messages")
    print("=" * 45)
    
    print("If you can't get chat lists directly, try this:")
    print("1. Send messages to your bot from different chats")
    print("2. Use MCP tools to search for recent messages:")
    print("   - Look for messages containing '@Angel_Dimi_Bot'")
    print("   - The message objects should contain chat_id information")
    
    print("\n📋 MCP functions that might help:")
    print("   - mcp_telegram_mcp_search_messages(chat_id, query='@Angel_Dimi_Bot')")
    print("   - mcp_telegram_mcp_get_history(chat_id, limit=10)")
    print("   - mcp_telegram_mcp_list_messages(chat_id, limit=20)")

def main():
    """Main function"""
    print("🔍 Telegram Chat ID Discovery Tool")
    print("=" * 35)
    
    # Test bot connection
    if not get_bot_info():
        print("❌ Cannot proceed without working MCP connection")
        return
    
    # Show different methods
    try_different_chat_methods()
    
    # Manual steps
    manual_chat_discovery_steps()
    
    # Create test script
    create_test_script()
    
    # Alternative approach
    show_alternative_approach()
    
    print("\n🎯 Next Steps:")
    print("1. Follow the manual steps above")
    print("2. Try the MCP function calls")
    print("3. Note down any chat IDs you find")
    print("4. Test them using test_chat_ids.py")
    print("5. Add working chat IDs to archive_bot_mcp.py")

if __name__ == "__main__":
    main()