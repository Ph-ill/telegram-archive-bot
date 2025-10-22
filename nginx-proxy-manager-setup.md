# Nginx Proxy Manager Setup for Telegram Archive Bot

## 🔍 **Current Issue Analysis**

**Container**: ✅ Working perfectly (logs show health checks passing)
**NPM**: ❌ 502 Bad Gateway - can't reach container

## 🎯 **Root Cause**
Nginx Proxy Manager can't connect to your `dimibot` container, likely due to:
1. Wrong forward hostname/port in NPM
2. Network connectivity between NPM and container
3. Container not accessible from NPM's network

## 🚀 **Fix in Nginx Proxy Manager**

### Step 1: Check Current Proxy Host
1. **Open NPM Admin Panel** (usually `http://your-server:81`)
2. **Go to "Proxy Hosts"**
3. **Find** `dimibot.coolphill.com` entry
4. **Click "Edit"** (pencil icon)

### Step 2: Update Forward Configuration

**In the "Details" tab:**

| Field | Correct Value | Notes |
|-------|---------------|-------|
| **Forward Hostname/IP** | `dimibot` | Container name (preferred) |
| **Forward Port** | `8443` | Container internal port |
| **Cache Assets** | ❌ Unchecked | Not needed for webhook |
| **Block Common Exploits** | ✅ Checked | Security |
| **Websockets Support** | ❌ Unchecked | Not needed |

**Alternative Forward Options** (try in this order):
1. `dimibot` (container name) - **Try this first**
2. `172.24.0.2` (container IP from logs)
3. `host.docker.internal` (if NPM is containerized)
4. `your-server-ip` (if container port is exposed)

### Step 3: SSL Configuration
**In the "SSL" tab:**
- **SSL Certificate**: Let's Encrypt or your existing cert
- **Force SSL**: ✅ Enabled
- **HTTP/2 Support**: ✅ Enabled
- **HSTS Enabled**: ✅ Enabled (optional)

### Step 4: Advanced Configuration (if needed)
**In the "Advanced" tab, add:**

```nginx
# Webhook-specific settings
proxy_read_timeout 60s;
proxy_connect_timeout 60s;
proxy_send_timeout 60s;

# Buffer settings for webhook payloads
proxy_buffering off;
proxy_request_buffering off;

# Headers for proper forwarding
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Server $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

## 🔧 **Troubleshooting Steps**

### 1. Test Container Accessibility
First, determine how NPM should reach your container:

```bash
# Get container details
docker inspect dimibot | grep -E "(IPAddress|NetworkMode)"

# Check if NPM and dimibot are on same network
docker network ls
docker network inspect Shared  # Your container's network
```

### 2. Test Different Forward Addresses

**Option A: Container Name** (if on same network)
- Forward Hostname: `dimibot`
- Forward Port: `8443`

**Option B: Container IP** (from logs: 172.24.0.2)
- Forward Hostname: `172.24.0.2`
- Forward Port: `8443`

**Option C: Host Network** (if port is exposed)
- Forward Hostname: `your-server-ip` or `localhost`
- Forward Port: `8443`

### 3. Check NPM Network Configuration

**If NPM is containerized:**
```bash
# Check NPM container network
docker inspect nginxproxymanager | grep NetworkMode

# If NPM is on different network, add it to Shared network:
docker network connect Shared nginxproxymanager
```

**If NPM is on host:**
- Use `localhost:8443` or `127.0.0.1:8443`

## 🧪 **Quick Test Methods**

### Test 1: Direct Container Access
```bash
# From host system
curl http://localhost:8443/health

# Should return: {"status": "healthy", "bot": "Angel_Dimi_Bot", ...}
```

### Test 2: Test from NPM Container (if containerized)
```bash
# Get into NPM container
docker exec -it nginxproxymanager bash

# Test connectivity
curl http://dimibot:8443/health
# OR
curl http://172.24.0.2:8443/health
```

### Test 3: Check NPM Logs
```bash
# NPM container logs
docker logs nginxproxymanager -f

# Look for connection errors when accessing dimibot.coolphill.com
```

## 📋 **Step-by-Step Fix**

### Method 1: Same Docker Network (Recommended)

1. **Ensure both containers on same network:**
   ```bash
   # Add NPM to Shared network (if not already)
   docker network connect Shared nginxproxymanager
   ```

2. **In NPM:**
   - Forward Hostname: `dimibot`
   - Forward Port: `8443`

3. **Test:**
   ```bash
   curl https://dimibot.coolphill.com/health
   ```

### Method 2: Host Network Access

1. **In NPM:**
   - Forward Hostname: `host.docker.internal` (if NPM containerized)
   - OR Forward Hostname: `localhost` (if NPM on host)
   - Forward Port: `8443`

2. **Test:**
   ```bash
   curl https://dimibot.coolphill.com/health
   ```

## ✅ **Expected Result**

After fixing NPM configuration:

```bash
curl https://dimibot.coolphill.com/health
```

Should return:
```json
{
  "status": "healthy",
  "bot": "Angel_Dimi_Bot",
  "timestamp": "2025-10-22T19:20:30...",
  "processed_messages": 0
}
```

## 🎯 **Most Likely Solution**

Based on your setup, try this in NPM:

1. **Edit Proxy Host** for `dimibot.coolphill.com`
2. **Forward Hostname**: `dimibot` (container name)
3. **Forward Port**: `8443`
4. **Save** and test

If that doesn't work, try `172.24.0.2:8443` (the container IP from your logs).

## 🔄 **After Fix - Test Bot**

Once health check works:

1. **Add @Angel_Dimi_Bot to a chat**
2. **Send**: `@Angel_Dimi_Bot archive https://reddit.com`
3. **Should get instant reply** with archive link!

The container is working perfectly - just need to fix the NPM proxy configuration! 🚀