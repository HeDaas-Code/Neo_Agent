# Deployment Guide

[中文](DEPLOYMENT.md) | **English**

This guide covers deploying Neo_Agent in various environments.

## Table of Contents

- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Platform Deployment](#cloud-platform-deployment)
- [Backup and Monitoring](#backup-and-monitoring)
- [Security Recommendations](#security-recommendations)

---

## Local Development

### Quick Setup

```bash
# Clone repository
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp example.env .env
# Edit .env and add your API key

# Run application
python gui_enhanced.py
```

### Development Environment

```bash
# Install development dependencies
pip install pytest black flake8

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .
```

---

## Production Deployment

### System Requirements

- **OS**: Ubuntu 20.04+ / CentOS 7+ / Windows Server 2019+
- **Python**: 3.8+
- **Memory**: 2GB minimum, 4GB recommended
- **Disk**: 10GB minimum
- **Network**: Stable internet connection for API calls

### Production Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv -y

# Create application directory
sudo mkdir -p /opt/neo_agent
cd /opt/neo_agent

# Clone repository
git clone https://github.com/HeDaas-Code/Neo_Agent.git .

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp example.env .env
nano .env  # Add API key and production settings

# Set permissions
sudo chown -R www-data:www-data /opt/neo_agent
```

### Running as Service (Linux)

Create systemd service file:

```bash
sudo nano /etc/systemd/system/neo-agent.service
```

Content:

```ini
[Unit]
Description=Neo Agent Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/neo_agent
Environment="PATH=/opt/neo_agent/venv/bin"
ExecStart=/opt/neo_agent/venv/bin/python gui_enhanced.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable neo-agent
sudo systemctl start neo-agent
sudo systemctl status neo-agent
```

---

## Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (if using web interface)
EXPOSE 5000

# Run application
CMD ["python", "gui_enhanced.py"]
```

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  neo-agent:
    build: .
    container_name: neo-agent
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env
    environment:
      - DEBUG_MODE=False
    restart: unless-stopped
    ports:
      - "5000:5000"
```

### Build and Run

```bash
# Build image
docker build -t neo-agent:latest .

# Run container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down
```

---

## Cloud Platform Deployment

### AWS EC2

1. **Launch EC2 Instance**
   - AMI: Ubuntu Server 22.04 LTS
   - Instance Type: t3.medium or larger
   - Storage: 20GB GP3

2. **Configure Security Group**
   - SSH (22): Your IP only
   - HTTP (80): 0.0.0.0/0 (if web interface)
   - HTTPS (443): 0.0.0.0/0 (if web interface)

3. **Deploy Application**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   # Follow production setup steps above
   ```

### Azure VM

1. **Create Virtual Machine**
   - Image: Ubuntu Server 22.04
   - Size: Standard_B2s or larger
   - Disk: 30GB Standard SSD

2. **Configure Networking**
   - Allow SSH (22)
   - Allow HTTP/HTTPS if needed

3. **Deploy Application**
   ```bash
   ssh azureuser@your-vm-ip
   # Follow production setup steps above
   ```

### Google Cloud Platform

1. **Create Compute Engine Instance**
   - OS: Ubuntu 22.04 LTS
   - Machine type: e2-medium
   - Boot disk: 20GB

2. **Deploy**
   ```bash
   gcloud compute ssh your-instance-name
   # Follow production setup steps above
   ```

---

## Backup and Monitoring

### Automated Backup

Create backup script:

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/neo-agent"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp /opt/neo_agent/chat_agent.db $BACKUP_DIR/chat_agent_$DATE.db

# Backup configuration
cp /opt/neo_agent/.env $BACKUP_DIR/env_$DATE

# Delete backups older than 30 days
find $BACKUP_DIR -name "chat_agent_*.db" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Add to crontab:

```bash
# Run daily at 2 AM
crontab -e
0 2 * * * /opt/neo_agent/backup.sh
```

### Monitoring

#### System Resource Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop

# Monitor in real-time
htop

# Check disk usage
df -h

# Check memory usage
free -h
```

#### Application Monitoring

```python
# monitoring.py
import psutil
import time
from datetime import datetime

def monitor():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        print(f"[{datetime.now()}]")
        print(f"CPU: {cpu_percent}%")
        print(f"Memory: {memory.percent}%")
        print(f"Disk: {disk.percent}%")
        print("-" * 50)
        
        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    monitor()
```

#### Log Rotation

Configure logrotate:

```bash
sudo nano /etc/logrotate.d/neo-agent
```

Content:

```
/opt/neo_agent/debug.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

---

## Security Recommendations

### 1. API Key Security

```env
# Never commit .env to version control
# Add to .gitignore:
.env
*.db
debug.log
```

### 2. Firewall Configuration

```bash
# Ubuntu/Debian
sudo ufw enable
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP (if needed)
sudo ufw allow 443/tcp # HTTPS (if needed)
```

### 3. SSL/TLS Configuration

If exposing web interface:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com
```

### 4. Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
pip install --upgrade -r requirements.txt
```

### 5. Access Control

```bash
# Restrict file permissions
chmod 600 .env
chmod 755 *.py
chown -R www-data:www-data /opt/neo_agent
```

### 6. Database Encryption

Consider encrypting database file:

```bash
# Install cryptography
pip install cryptography

# Example encryption script (implement as needed)
python encrypt_database.py
```

---

## Performance Optimization

### 1. Enable Caching

```env
# .env
ENABLE_CACHE=True
CACHE_SIZE=1000
```

### 2. Optimize Database

```bash
# Regular VACUUM
sqlite3 chat_agent.db "VACUUM;"

# Analyze for query optimization
sqlite3 chat_agent.db "ANALYZE;"
```

### 3. Resource Limits

```ini
# In systemd service file
[Service]
MemoryLimit=2G
CPUQuota=50%
```

---

## Troubleshooting Deployment

### Issue: Service Won't Start

```bash
# Check logs
sudo journalctl -u neo-agent -n 50

# Check permissions
ls -la /opt/neo_agent

# Check Python path
which python
```

### Issue: Database Locked

```bash
# Check for other processes
fuser chat_agent.db

# Kill if necessary
kill -9 <PID>
```

### Issue: High Memory Usage

```bash
# Monitor memory
watch -n 1 free -m

# Restart service
sudo systemctl restart neo-agent
```

---

## Rollback Procedure

If deployment fails:

```bash
# Stop service
sudo systemctl stop neo-agent

# Restore from backup
cp /backup/neo-agent/chat_agent_YYYYMMDD.db /opt/neo_agent/chat_agent.db

# Revert code
git checkout previous-version

# Restart service
sudo systemctl start neo-agent
```

---

## More Information

- [Troubleshooting Guide](TROUBLESHOOTING_EN.md)
- [Development Guide](DEVELOPMENT_EN.md)
- [API Reference](API_EN.md)

---

<div align="center">

**Deploy with confidence!** 🚀

</div>
