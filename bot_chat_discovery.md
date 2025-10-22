# Getting Chat IDs with Bot Token Limitations

## The Problem
Your MCP server is using a **bot token**, which has restricted API access. Bots cannot:
- List chats/dialogs (`get_dialogs`)
- Get contacts (`GetContactsRequest`) 
- Search contacts (`SearchRequest`)

## Solutions for Getting Chat IDs

### Method 1: Manual Chat ID Discovery
1. **Start conversations with your bot**:
   - Open Telegram
   - Search for `@Angel_Dimi_Bot`
   - Send a message: "Hello bot!"

2. **Add bot to groups**:
   - Create or join a group
   - Add `@Angel_Dimi_Bot` to the group
   - Send a message mentioning the bot

3. **Use a Telegram bot to get chat IDs**:
   - Send `/start` to `@userinfobot` 
   - It will show your user ID
   - For groups: Add `@userinfobot` to the group, it will show the group ID

### Method 2: Use Bot-Compatible MCP Functions
Let's try functions that bots CAN use:

```python
# These might work with bot tokens:
mcp_telegram_mcp_get_me()  # ✅ Works - gets bot info
mcp_telegram_mcp_send_message(chat_id=KNOWN_ID, message="test")  # ✅ Should work
mcp_telegram_mcp_get_messages(chat_id=KNOWN_ID)  # ❓ Might work
```

### Method 3: Webhook Approach (Recommended)
Instead of polling for messages, set up a webhook:

1. **Set up webhook** (if MCP server supports it)
2. **Receive updates** when users message the bot
3. **Extract chat IDs** from incoming messages
4. **Store chat IDs** for future use

### Method 4: Use Known Chat IDs
If you know specific chat IDs, you can test them directly:

- **Your personal chat with bot**: Usually your user ID
- **Group chats**: Negative numbers (e.g., -1001234567890)
- **Channels**: Very large negative numbers

## Practical Steps

### Step 1: Get Your User ID
1. Message `@userinfobot` in Telegram
2. It will reply with your user ID (e.g., 123456789)
3. This is likely the chat ID for your personal chat with your bot

### Step 2: Test Direct Message
Try sending a message to your user ID:
```python
mcp_telegram_mcp_send_message(chat_id=YOUR_USER_ID, message="Test from archive bot")
```

### Step 3: Get Group Chat IDs
1. Add your bot to a group
2. Add `@userinfobot` to the same group
3. Send any message - userinfobot will show the group ID
4. Test sending to that group ID

### Step 4: Create a Chat ID Logger
Create a simple script that logs any chat IDs from successful operations:

```python
def log_working_chat_id(chat_id, description):
    with open("working_chat_ids.txt", "a") as f:
        f.write(f"{chat_id} - {description}\n")
```

## Alternative: Use User Token Instead of Bot Token
If you need full API access, you could:
1. Use your personal Telegram account credentials
2. Configure MCP server with user session instead of bot token
3. This gives access to all user methods (get_dialogs, contacts, etc.)

**Note**: This requires your personal phone number and may have security implications.

## Next Steps
1. Get your user ID from `@userinfobot`
2. Test sending messages to that chat ID
3. Add bot to groups and get their IDs
4. Update the archive bot with known working chat IDs