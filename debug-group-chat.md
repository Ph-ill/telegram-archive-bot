# Debug Group Chat Issues

## 🔍 **Step-by-Step Debugging**

Since privacy mode is disabled but bot still not responding, let's find the root cause.

### Step 1: Check Container Logs in Real-Time

1. **Open container logs**:
   ```bash
   docker logs dimibot -f
   ```
   OR in **Portainer**: Containers → dimibot → Logs (enable "Auto-refresh")

2. **In the group chat**, send:
   ```
   @Angel_Dimi_Bot archive https://reddit.com
   ```

3. **Watch logs** - do you see ANY activity?

### Step 2: Check What Messages Are Being Received

Look for these patterns in logs:

**✅ Good - Message received:**
```
INFO - Processing archive request from YourName
INFO - Archiving: https://reddit.com
```

**❌ Bad - No logs at all:**
- Webhook not receiving messages
- Bot not in group properly
- Network/connectivity issue

**❌ Bad - Message received but not processed:**
```
INFO - 127.0.0.1 - - [timestamp] "POST /webhook HTTP/1.1" 200 -
```
But no "Processing archive request" - means mention detection failed

### Step 3: Verify Bot Username Detection

The bot looks for `@angel_dimi_bot` (lowercase). Try these variations:

```
@Angel_Dimi_Bot archive https://reddit.com
@angel_dimi_bot archive https://reddit.com  
Hey @Angel_Dimi_Bot please archive https://reddit.com
```

### Step 4: Check Group Type and Bot Status

1. **Group info** → **Members** → Find `Angel Dimi Bot`
2. **Check if bot shows as**:
   - ✅ Regular member
   - ✅ Admin
   - ❌ Not found (bot was removed)

3. **Group type**:
   - Regular group (< 200 members)
   - Supergroup (> 200 members) - might need different handling

### Step 5: Test Webhook Directly

Test if webhook receives group messages:

```bash
# Simulate a group message
curl -X POST https://dimibot.coolphill.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "message_id": 123,
      "chat": {
        "id": -1001234567890,
        "type": "supergroup",
        "title": "Test Group"
      },
      "from": {
        "id": 987654321,
        "first_name": "TestUser",
        "username": "testuser"
      },
      "text": "@Angel_Dimi_Bot archive https://test.com"
    }
  }'
```

Check logs for processing.

## 🔧 **Common Issues & Fixes**

### Issue 1: Bot Username Case Sensitivity

The bot code checks for lowercase. Update the code to be case-insensitive:

```python
# In docker_webhook_bot.py, update this function:
def is_bot_mentioned(self, text):
    """Check if bot is mentioned"""
    if not text:
        return False
    # Make both text and username lowercase for comparison
    return f"@{self.bot_username.lower()}" in text.lower()
```

### Issue 2: Group ID vs Chat ID

Group chats have negative IDs. Check if your bot handles negative chat IDs properly.

### Issue 3: Supergroup vs Regular Group

If it's a supergroup, the bot might need admin permissions even with privacy mode disabled.

**Try making bot admin**:
1. Group settings → Administrators → Add Administrator
2. Add `@Angel_Dimi_Bot`
3. Grant minimal permissions (just "Delete Messages")

### Issue 4: Bot Was Re-added

If bot was removed and re-added to group, it might need to be re-configured.

**Remove and re-add bot**:
1. Remove `@Angel_Dimi_Bot` from group
2. Add it back
3. Test again

## 🧪 **Debugging Commands**

### Check Bot Info
```bash
curl "https://api.telegram.org/bot8144911230:AAHA7St4TWbuYBY4hNGhkZ7YZwfZyi3RUAg/getMe"
```

### Check Webhook Info
```bash
curl "https://api.telegram.org/bot8144911230:AAHA7St4TWbuYBY4hNGhkZ7YZwfZyi3RUAg/getWebhookInfo"
```

### Get Updates (if webhook fails)
```bash
curl "https://api.telegram.org/bot8144911230:AAHA7St4TWbuYBY4hNGhkZ7YZwfZyi3RUAg/getUpdates"
```

## 📊 **What to Look For**

### In Container Logs:
1. **Webhook requests coming in**: `POST /webhook HTTP/1.1 200`
2. **Message processing**: `Processing archive request from...`
3. **Archive attempts**: `Archiving: https://...`
4. **Response sending**: `Message sent successfully to chat...`

### Missing Logs Mean:
- **No webhook requests**: Network/NPM issue
- **Webhook but no processing**: Mention detection issue
- **Processing but no response**: Telegram API issue

## 🎯 **Most Likely Issues**

1. **Case sensitivity** in mention detection
2. **Supergroup** requiring admin permissions
3. **Bot not properly added** to group
4. **Webhook not receiving** group messages

## 🚀 **Quick Test**

Try this exact message format:
```
@angel_dimi_bot archive https://example.com
```

And watch the logs in real-time to see what happens.

What do you see in the container logs when you send a message in the group?