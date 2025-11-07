# Ubuntu vs Amazon Linux - Quick Reference

This guide helps you use the correct commands for your EC2 instance OS.

## How to Check Your OS

```bash
cat /etc/os-release
```

Look for `ID=ubuntu` or `ID=amzn`

## Quick Command Reference

| Task | Ubuntu 22.04 | Amazon Linux 2 |
|------|-------------|----------------|
| **Default User** | `ubuntu` | `ec2-user` |
| **SSH Command** | `ssh -i key.pem ubuntu@IP` | `ssh -i key.pem ec2-user@IP` |
| **Update Packages** | `sudo apt-get update` | `sudo yum update -y` |
| **Install Package** | `sudo apt-get install -y <package>` | `sudo yum install -y <package>` |
| **Docker Compose** | `docker compose` (v2, built-in) | `docker-compose` (v1, needs install) |
| **Firewall** | `sudo ufw allow 5000/tcp` | `sudo firewall-cmd --permanent --add-port=5000/tcp` |
| **Check Services** | `sudo systemctl status docker` | `sudo systemctl status docker` |

## Docker Installation

### Ubuntu 22.04
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
newgrp docker
```

### Amazon Linux 2
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
newgrp docker

# Install Docker Compose separately
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Docker Compose Commands

### Ubuntu (v2 syntax)
```bash
# Start
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop
docker compose down

# Pull
docker compose pull

# Logs
docker compose logs -f

# Restart
docker compose restart
```

### Amazon Linux (v1 syntax)
```bash
# Start
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop
docker-compose down

# Pull
docker-compose pull

# Logs
docker-compose logs -f

# Restart
docker-compose restart
```

## SCP File Transfer

### To Ubuntu
```powershell
scp -i "C:\path\to\key.pem" file.txt ubuntu@IP:~/
```

### To Amazon Linux
```powershell
scp -i "C:\path\to\key.pem" file.txt ec2-user@IP:~/
```

## Firewall Configuration

### Ubuntu (UFW)
```bash
# Check status
sudo ufw status

# Allow port
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable

# Disable firewall (for testing)
sudo ufw disable
```

### Amazon Linux 2 (firewalld)
```bash
# Check status
sudo firewall-cmd --state

# Allow port
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload

# List ports
sudo firewall-cmd --list-ports
```

## Automated Deployment Script

The `deploy-ec2.sh` script **automatically detects your OS** and uses the correct commands!

```bash
chmod +x deploy-ec2.sh
./deploy-ec2.sh
```

It will:
- ✅ Detect Ubuntu or Amazon Linux
- ✅ Install Docker using the right package manager
- ✅ Install Docker Compose (plugin for Ubuntu, standalone for Amazon Linux)
- ✅ Use the correct `docker compose` or `docker-compose` command
- ✅ Show OS-specific firewall instructions

## Common Issues

### Issue: Docker Compose not found on Amazon Linux
**Solution:** The script installs it automatically, or manually:
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### Issue: Permission denied (Ubuntu)
**Solution:** Add user to docker group and re-login:
```bash
sudo usermod -aG docker ubuntu
newgrp docker
```

### Issue: Permission denied (Amazon Linux)
**Solution:** Add user to docker group and re-login:
```bash
sudo usermod -a -G docker ec2-user
newgrp docker
```

### Issue: Port 5000 not accessible
**Solution:**
1. Check EC2 Security Group (Inbound rule for port 5000)
2. **Ubuntu:** `sudo ufw allow 5000/tcp` or `sudo ufw disable`
3. **Amazon Linux:** Check if firewalld is running: `sudo systemctl status firewalld`

## Recommendations

### For New Deployments
**Use Ubuntu 22.04 LTS** because:
- ✅ Docker Compose v2 built-in (no separate install)
- ✅ More familiar to most developers
- ✅ Longer LTS support (until 2027)
- ✅ Better package availability
- ✅ Simpler syntax (`docker compose` vs `docker-compose`)

### For AWS-Optimized Workloads
**Use Amazon Linux 2** if:
- ✅ You need AWS-specific optimizations
- ✅ You use other AWS services heavily
- ✅ You want faster boot times
- ⚠️ Accept Docker Compose v1 (legacy)

## Quick Test Commands

After deployment, test with these commands:

```bash
# Check container is running
docker ps

# Check logs
docker logs openpilot-detection

# Test endpoint
curl http://localhost:5000/status

# Check disk space
df -h

# Check memory
free -h

# Check Docker version
docker --version

# Check Docker Compose version
docker compose version      # Ubuntu
docker-compose --version   # Amazon Linux
```

## Summary

| Feature | Ubuntu 22.04 | Amazon Linux 2 |
|---------|-------------|----------------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Docker Compose** | v2 (built-in) | v1 (manual install) |
| **Package Manager** | apt-get | yum |
| **LTS Support** | Until 2027 | Until 2025 |
| **Community Support** | Larger | AWS-focused |
| **Recommendation** | ✅ **Recommended for most users** | Good for AWS-heavy workloads |

---

**The deploy-ec2.sh script handles all OS differences automatically!** Just run it and it will work on both Ubuntu and Amazon Linux.
