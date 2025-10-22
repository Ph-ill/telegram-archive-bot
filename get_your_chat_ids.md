# How to Get Your Chat IDs (Bot Token Method)

Since your MCP server uses a bot token with limited API access, here's how to get chat IDs:

## Step 1: Get Your Personal User ID

1. **Open Telegram**
2. **Search for and message**: `@userinfobot`
3. **Send any message** (like "hi")
4. **Copy your User ID** from the response (e.g., `123456789`)

This User ID is likely the chat ID for direct messages with your bot.

## Step 2: Test Your Personal Chat

Try sending a test message to your user ID:

```bash
# Test if your user ID works as a chat ID
python bot_limited_archive.py add-chat 123456789 "My personal chat"
python bot_limited_archive.py test-chat 123456789
```

## Step 3: Get Group Chat IDs

For each group where you want the bot to work:

1. **Add your bot** (`@Angel_Dimi_Bot`) to the group
2. **Add `@userinfobot`** to the same group  
3. **Send any message** in the group
4. **`@userinfobot` will reply** with the group information including the Chat ID
5. **Copy the Chat ID** (it will be negative, like `-1001234567890`)

## Step 4: Add Group Chat IDs

```bash
# Add each group chat ID
python bot_limited_archive.py add-chat -1001234567890 "My test group"
python bot_limited_archive.py add-chat -1009876543210 "Work group"
```

## Step 5: List and Test All Chat IDs

```bash
# See all your known chat IDs
python bot_limited_archive.py list-chats

# Test each one
python bot_limited_archive.py test-chat 123456789
python bot_limited_archive.py test-chat -1001234567890
```

## Step 6: Run the Archive Bot

Once you have working chat IDs:

```bash
# Run a check cycle to process recent messages
python bot_limited_archive.py run

# Test URL archiving
python bot_limited_archive.py test-archive https://example.com
```

## Alternative: Use Raw MCP Tools

If you want to try MCP tools directly, here are the ones that might work with bot tokens:

```python
# These should work:
mcp_telegram_mcp_get_me()  # Get bot info
mcp_telegram_mcp_send_message(chat_id=YOUR_USER_ID, message="Test")
mcp_telegram_mcp_reply_to_message(chat_id=CHAT_ID, message_id=MSG_ID, text="Reply")

# These might work:
mcp_telegram_mcp_get_messages(chat_id=CHAT_ID, page_size=10)
mcp_telegram_mcp_list_messages(chat_id=CHAT_ID, limit=10)
```

## Quick Start Example

1. Message `@userinfobot` → get your user ID (e.g., `987654321`)
2. Add it: `python bot_limited_archive.py add-chat 987654321 "My chat"`
3. Test archiving: `python bot_limited_archive.py test-archive https://github.com`
4. Run bot: `python bot_limited_archive.py run`

## Usage in Telegram

Once set up, use the bot by mentioning it with links:

```
@Angel_Dimi_Bot please archive https://interesting-article.com
```

The bot will reply with the archived link from archive.ph.