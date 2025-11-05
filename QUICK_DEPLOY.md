# Quick Deployment Guide

## 🚀 Deploy to EC2 in 5 Minutes

Your Docker image is now on Docker Hub: **kainosit/openpilot:latest**

### Prerequisites
- AWS EC2 instance (t3.large or better)
- Security Group with port 5000 open
- SSH key pair

### Deployment Steps

#### 1. SSH to EC2
```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
```

#### 2. Install Docker (if not already installed)
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
newgrp docker
```

#### 3. Create project directory
```bash
mkdir ~/openpilot-detection
cd ~/openpilot-detection
```

#### 4. Transfer deployment files (from Windows PowerShell)
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

#### Production (EC2)
```bash
# Pulls from Docker Hub (uses docker-compose.prod.yml)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Troubleshooting

**Container not starting?**
```bash
docker logs openpilot-detection
```

**Port 5000 not accessible?**
- Check EC2 Security Group (Inbound rule for port 5000)
- Check firewall: `sudo firewall-cmd --list-ports`

**Old image cached?**
```bash
docker compose pull
docker compose up -d --force-recreate
```

### Full Documentation

- **DOCKER_COMPOSE_GUIDE.md** - Complete Compose setup explanation
- **EC2_DEPLOYMENT_GUIDE.md** - Detailed EC2 deployment guide
- **SYSTEM_DOCUMENTATION.md** - Full system documentation

---

**Need help?** Check the detailed guides above or review the container logs.
