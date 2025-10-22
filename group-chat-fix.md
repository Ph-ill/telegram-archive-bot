# Fix Bot Not Responding in Group Chats

## 🔍 **The Issue**
Bot works in private chats but not in group chats when mentioned. This is due to Telegram's **privacy mode** for bots.

## 🎯 **Root Cause**
By default, bots in groups only receive:
- Messages that start with `/` (commands)
- Messages that mention the bot IF privacy mode is disabled
- Messages sent as replies to the bot

## 🚀 **Solution: Disable Privacy Mode**

### Method 1: Using @BotFather (Recommended)

1. **Open Telegram** and message **@BotFather**
2. **Send**: `/mybots`
3. **Select**: `Angel Dimi Bot` (your bot)
4. **Click**: `Bot Settings`
5. **Click**: `Group Privacy`
6. **Click**: `Turn Off` (Disable)

**You should see**: `Privacy mode is disabled for Angel Dimi Bot`

### Method 2: Using Telegram Bot API

```bash
# Disable privacy mode via API
curl -X POST "https://api.telegram.org/bot8144911230:AAHA7St4TWbuYBY4hNGhkZ7YZwfZyi3RUAg/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "@Angel_Dimi_Bot",
    "menu_button": {
      "type": "default"
    }
  }'
```

## 🔧 **Alternative: Add Bot as Admin**

If you can't disable privacy mode, make the bot an admin:

1. **In the group chat**: Tap group name → `Manage Group`
2. **Tap**: `Administrators`
3. **Tap**: `Add Admin`
4. **Search and add**: `@Angel_Dimi_Bot`
5. **Grant permissions**: At minimum, `Delete Messages` (bots need some admin permission to see all messages)

## 🧪 **Test the Fix**

After disabling privacy mode or adding as admin:

1. **In the group chat**, send:
   ```
   @Angel_Dimi_Bot archive https://reddit.com
   ```

2. **Bot should respond** with archive link

## 📊 **Check Bot Logs**

Look at container logs to see if messages are being received:

```bash
# In Portainer: Containers → dimibot → Logs
# Or via CLI:
docker logs dimibot -f
```

**Before fix**: No log entries when you mention bot in group
**After fix**: Should see log entries like:
```
INFO - Processing archive request from YourName
INFO - Archiving: https://reddit.com
INFO - Message sent successfully to chat -123456789
```

## 🔍 **Troubleshooting**

### Bot Still Not Responding?

1. **Check bot is actually in the group**:
   - Group info → Members → Search for `Angel Dimi Bot`

2. **Verify privacy mode is off**:
   - Message @BotFather → `/mybots` → Your bot → `Bot Settings` → `Group Privacy`
   - Should show: `Privacy mode is disabled`

3. **Try different mention formats**:
   ```
   @Angel_Dimi_Bot archive https://example.com
   @angel_dimi_bot archive https://example.com
   Hey @Angel_Dimi_Bot, archive https://example.com
   ```

4. **Check group type**:
   - Regular groups: Should work after privacy mode disabled
   - Supergroups: Might need admin permissions
   - Channels: Bot needs to be admin

### Still Having Issues?

**Check webhook logs** for incoming messages:
```bash
docker logs dimibot -f
```

**Test webhook directly**:
```bash
curl -X POST https://dimibot.coolphill.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "message_id": 123,
      "chat": {"id": -123456789, "type": "group"},
      "from": {"id": 987654321, "first_name": "Test"},
      "text": "@Angel_Dimi_Bot archive https://test.com"
    }
  }'
```

## ✅ **Expected Behavior After Fix**

- ✅ **Private chats**: Bot responds (already working)
- ✅ **Group chats**: Bot responds when mentioned
- ✅ **Supergroups**: Bot responds when mentioned
- ✅ **Channels**: Bot responds if admin

## 🎯 **Most Likely Solution**

**Disable privacy mode via @BotFather** - this is the most common fix and should resolve the issue immediately.

After disabling privacy mode, the bot will receive ALL messages in groups (not just mentions), but your code already filters for mentions, so it will only respond when tagged.