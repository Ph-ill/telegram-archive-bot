# Files to Include in Portainer Upload

When using Portainer's "Upload" method, create a ZIP file containing these files:

## Required Files:
```
dimibot.zip
├── Dockerfile
├── docker_webhook_bot.py
├── requirements-docker.txt
└── processed_messages.json (empty file: {})
```

## Create the ZIP file:

### On Linux/Mac:
```bash
# Create empty processed messages file
echo '[]' > processed_messages.json

# Create ZIP file
zip -r dimibot.zip Dockerfile docker_webhook_bot.py requirements-docker.txt processed_messages.json
```

### On Windows:
```powershell
# Create empty processed messages file
echo '[]' > processed_messages.json

# Create ZIP using PowerShell
Compress-Archive -Path Dockerfile,docker_webhook_bot.py,requirements-docker.txt,processed_messages.json -DestinationPath dimibot.zip
```

## File Contents Verification:

### Dockerfile
- Should contain the Docker build instructions
- Uses python:3.11-slim base image
- Copies application files
- Sets up non-root user

### docker_webhook_bot.py
- Main bot application
- Handles webhook requests
- Processes archive requests
- Environment variable configuration

### requirements-docker.txt
```
flask==2.3.3
requests==2.31.0
gunicorn==21.2.0
```

### processed_messages.json
```json
[]
```

## Upload Process:

1. **Create the ZIP file** with the files above
2. **In Portainer**:
   - Go to Stacks → Add stack
   - Name: `dimibot`
   - Build method: Upload
   - Upload the ZIP file
   - Set environment variables
   - Deploy

## Alternative: Git Repository

Instead of uploading files, you can:

1. **Create a Git repository** with all the files
2. **In Portainer**:
   - Build method: Repository
   - Repository URL: `https://github.com/yourusername/dimibot`
   - Reference: `refs/heads/main`
   - Compose path: `portainer-stack.yml`