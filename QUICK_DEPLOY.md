# Quick Deployment Guide

## � Important: Docker Hub Repository Access

The Docker image `kainosit/openpilot:latest` is currently **private** on Docker Hub.

**Before deploying, you must:**

**Option A (Recommended):** Make repository public
- Visit: https://hub.docker.com/repository/docker/kainosit/openpilot/settings/general
- Change Visibility to "Public" → Save

**Option B:** Login on EC2 before running deploy script
```bash
docker login
# Enter: username=kainosit, password=YOUR_PASSWORD
```

**Option C:** Upload source files and build locally (script does this automatically if pull fails)

See **[DOCKERHUB_ACCESS_FIX.md](DOCKERHUB_ACCESS_FIX.md)** for detailed solutions.

---

## �🚀 Deploy to EC2 in 5 Minutes

Your Docker image is now on Docker Hub: **kainosit/openpilot:latest**

### Prerequisites
- AWS EC2 instance (t3.large or better)
- **Ubuntu 22.04 LTS** or Amazon Linux 2
- Security Group with port 5000 open
- SSH key pair

### Deployment Steps

#### 1. SSH to EC2

**For Ubuntu:**
```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

**For Amazon Linux:**
```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
```

#### 2. Install Docker (The deploy script does this automatically, but here's the manual way)

**Ubuntu 22.04:**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
newgrp docker
```

**Amazon Linux 2:**
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 3. Create project directory
```bash
mkdir ~/openpilot-detection
cd ~/openpilot-detection
```

#### 4. Transfer deployment files (from Windows PowerShell)

**For Ubuntu:**
```powershell
scp -i "C:\path\to\your-key.pem" `
  docker-compose.yml `
  docker-compose.prod.yml `
  deploy-ec2.sh `
  ubuntu@YOUR_EC2_IP:~/openpilot-detection/
```

**For Amazon Linux:**
```powershell
scp -i "C:\path\to\your-key.pem" `
  docker-compose.yml `
  docker-compose.prod.yml `
  deploy-ec2.sh `
  ec2-user@YOUR_EC2_IP:~/openpilot-detection/
```

#### 5. Run automated deployment (on EC2)
```bash
cd ~/openpilot-detection
chmod +x deploy-ec2.sh
./deploy-ec2.sh
```

**If you get "pull access denied" error:**
- The Docker Hub repository is private
- See **[DOCKERHUB_ACCESS_FIX.md](DOCKERHUB_ACCESS_FIX.md)** for solutions
- Quick fix: `docker login` before running the script
- Or the script will automatically build from source if you uploaded Dockerfile

**The script automatically:**
- ✅ Detects your OS (Ubuntu or Amazon Linux)
- ✅ Installs Docker and Docker Compose if needed
- ✅ Tries to pull from Docker Hub
- ✅ **Fallback:** Builds locally if pull fails and source files exist
- ✅ Starts the container
- ✅ Configures health checks
- ✅ Sets up auto-restart
- ✅ Shows you the access URLs

#### 6. Access your application
```
http://YOUR_EC2_PUBLIC_IP:5000
```

### That's it! 🎉

The deployment script automatically:
- ✅ Pulls the latest image from Docker Hub
- ✅ Starts the container
- ✅ Configures health checks
- ✅ Sets up auto-restart
- ✅ Shows you the access URLs

### Manual Commands (if needed)

**Ubuntu (Docker Compose v2):**
```bash
# Pull latest image
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Start container
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker logs -f openpilot-detection

# Check status
docker ps

# Restart
docker restart openpilot-detection

# Stop
docker compose down
```

**Amazon Linux (Docker Compose v1):**
```bash
# Pull latest image
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Start container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker logs -f openpilot-detection

# Check status
docker ps

# Restart
docker restart openpilot-detection

# Stop
docker-compose down
```

### Updating Production

When you push a new version to Docker Hub:

```bash
# On EC2
cd ~/openpilot-detection
./deploy-ec2.sh
```

Or manually:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Docker Hub Image Info

- **Repository:** kainosit/openpilot
- **Latest tag:** latest
- **Timestamped tag:** 20251105-2224
- **Size:** 12.9 GB
- **Pull command:** `docker pull kainosit/openpilot:latest`

### Local Development vs Production

#### Local (Docker Desktop)
```powershell
# Builds from Dockerfile (uses docker-compose.override.yml)
docker-compose up --build -d
```

#### Production EC2 - Ubuntu
```bash
# Pulls from Docker Hub (uses docker-compose.prod.yml)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### Production EC2 - Amazon Linux
```bash
# Pulls from Docker Hub (uses docker-compose.prod.yml)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Troubleshooting

**Container not starting?**
```bash
docker logs openpilot-detection
```

**Port 5000 not accessible?**
- Check EC2 Security Group (Inbound rule for port 5000)
- **Ubuntu:** Check firewall: `sudo ufw status` and allow if needed: `sudo ufw allow 5000/tcp`
- **Amazon Linux:** Check firewall: `sudo firewall-cmd --list-ports`

**Old image cached?**
```bash
# Ubuntu
docker compose pull
docker compose up -d --force-recreate

# Amazon Linux
docker-compose pull
docker-compose up -d --force-recreate
```

### Full Documentation

- **DOCKER_COMPOSE_GUIDE.md** - Complete Compose setup explanation
- **EC2_DEPLOYMENT_GUIDE.md** - Detailed EC2 deployment guide
- **SYSTEM_DOCUMENTATION.md** - Full system documentation

---

**Need help?** Check the detailed guides above or review the container logs.
