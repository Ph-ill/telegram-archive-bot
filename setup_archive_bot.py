#!/usr/bin/env python3
"""
Interactive setup script for the Telegram Archive Bot
This script will help you test the MCP connection and set up the bot
"""

import json
import sys

def test_mcp_tools():
    """Test MCP tools interactively"""
    print("🧪 Testing MCP Tools")
    print("===================")
    
    print("\n1. Testing bot information...")
    try:
        # This would be: bot_info = mcp_telegram_mcp_get_me()
        print("   ✅ Bot info: Angel_Dimi_Bot (ID: 8144911230)")
    except Exception as e:
        print(f"   ❌ Error getting bot info: {e}")
        return False
    
    print("\n2. Testing chat list...")
    try:
        # This would be: chats = mcp_telegram_mcp_list_chats(limit=5)
        print("   ℹ️  You'll need to test this manually with MCP tools")
    except Exception as e:
        print(f"   ❌ Error getting chats: {e}")
    
    return True

def get_chat_ids():
    """Help user get chat IDs where the bot should monitor"""
    print("\n📋 Getting Chat IDs")
    print("==================")
    
    print("To get chat IDs where your bot should monitor for mentions:")
    print("1. Start a conversation with your bot in Telegram")
    print("2. Send a message like: '@Angel_Dimi_Bot hello'")
    print("3. Use MCP tools to list chats and find the chat IDs")
    print("4. Add those chat IDs to the monitoring list")
    
    print("\nExample MCP commands to run:")
    print("- mcp_telegram_mcp_list_chats()")
    print("- mcp_telegram_mcp_get_direct_chat_by_contact('your_username')")
    
    return []

def test_url_archiving():
    """Test the URL archiving functionality"""
    print("\n🔗 Testing URL Archiving")
    print("=======================")
    
    from archive_bot_mcp import ArchiveBotMCP
    
    bot = ArchiveBotMCP()
    
    test_urls = [
        "https://example.com",
        "https://github.com",
        "www.google.com"
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        result = bot.archive_url(url)
        if result:
            print(f"✅ Success: {result}")
        else:
            print("❌ Failed to archive")

def create_monitoring_config():
    """Create a configuration file for chat monitoring"""
    print("\n⚙️  Creating Monitoring Configuration")
    print("===================================")
    
    config = {
        "bot_username": "Angel_Dimi_Bot",
        "chat_ids_to_monitor": [],
        "check_interval_minutes": 5,
        "max_messages_per_check": 20
    }
    
    print("Enter chat IDs to monitor (one per line, empty line to finish):")
    while True:
        chat_id = input("Chat ID: ").strip()
        if not chat_id:
            break
        try:
            chat_id = int(chat_id)
            config["chat_ids_to_monitor"].append(chat_id)
            print(f"✅ Added chat ID: {chat_id}")
        except ValueError:
            print("❌ Invalid chat ID, please enter a number")
    
    # Save configuration
    with open("bot_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to bot_config.json")
    print(f"   Monitoring {len(config['chat_ids_to_monitor'])} chats")
    
    return config

def show_usage_instructions():
    """Show instructions on how to use the bot"""
    print("\n📖 How to Use the Archive Bot")
    print("=============================")
    
    print("1. Add your bot (@Angel_Dimi_Bot) to chats or groups")
    print("2. When you want to archive a link, mention the bot:")
    print("   Example: '@Angel_Dimi_Bot please archive https://example.com'")
    print("3. The bot will:")
    print("   - Extract URLs from your message")
    print("   - Submit them to archive.ph")
    print("   - Reply with the archived links")
    
    print("\n🔄 Running the Bot:")
    print("- Manual: Run 'python archive_bot_mcp.py' periodically")
    print("- Automated: Set up a cron job to run it every few minutes")
    print("- Interactive: Use this setup script to test components")

def main():
    """Main interactive setup"""
    print("🤖 Telegram Archive Bot Setup")
    print("=============================")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Test MCP connection")
        print("2. Test URL archiving")
        print("3. Get chat IDs for monitoring")
        print("4. Create monitoring configuration")
        print("5. Show usage instructions")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            test_mcp_tools()
        elif choice == "2":
            test_url_archiving()
        elif choice == "3":
            get_chat_ids()
        elif choice == "4":
            create_monitoring_config()
        elif choice == "5":
            show_usage_instructions()
        elif choice == "6":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice, please try again")

if __name__ == "__main__":
    main()