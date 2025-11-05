# AWS EC2 Deployment Guide

This guide provides step-by-step instructions for deploying the multi-device detection system to AWS EC2 using Docker.

## Overview

Deployment Architecture:
- **AWS EC2 Instance** running Docker
- **Docker Container** with detection system
- **Public IP** for mobile device access
- **Security Groups** for port access control
- **Optional:** AWS ECR for private image registry

## Prerequisites

1. **AWS Account** with EC2 access
2. **Docker Image** tested locally (see LOCAL_DOCKER_TESTING.md)
3. **SSH Key Pair** for EC2 access
4. **Basic AWS knowledge** (EC2, Security Groups, SSH)

## Step 1: Choose EC2 Instance Type

### Recommended Instance Types

| Instance Type | vCPUs | RAM | Storage | Use Case | Monthly Cost* |
|---------------|-------|-----|---------|----------|---------------|
| **t3.medium** | 2 | 4 GB | EBS | Light testing | ~$30 |
| **t3.large** | 2 | 8 GB | EBS | 1-2 devices | ~$60 |
| **c5.large** | 2 | 4 GB | EBS | CPU-optimized | ~$62 |
| **c5.xlarge** | 4 | 8 GB | EBS | 3-5 devices | ~$123 |

*Prices for us-east-1, may vary by region

### Minimum Requirements
- **vCPUs:** 2 (4+ recommended for multiple devices)
- **RAM:** 4 GB (8 GB+ recommended)
- **Storage:** 20 GB EBS (SSD)
- **Network:** Enhanced networking enabled
- **OS:** Amazon Linux 2 or Ubuntu 20.04/22.04

**Recommendation:** Start with **t3.large** for production use with 1-2 mobile devices.

## Step 2: Launch EC2 Instance

### Using AWS Console

1. **Navigate to EC2 Dashboard**
   - Go to https://console.aws.amazon.com/ec2/
   - Click "Launch Instance"

2. **Configure Instance**

   **Name and tags:**
   - Name: `openpilot-detection-server`

   **Application and OS Images (AMI):**
   - **Recommended:** Amazon Linux 2 AMI (HVM) - SSD Volume Type
   - Alternative: Ubuntu Server 22.04 LTS

   **Instance type:**
   - Select `t3.large` (or your chosen type)

   **Key pair (login):**
   - Select existing key pair OR
   - Create new key pair → Download `.pem` file

   **Network settings:**
   - Auto-assign public IP: **Enable**
   - Create security group: **New** (configure in next step)

   **Configure storage:**
   - Size: `20 GB`
   - Volume type: `gp3` (General Purpose SSD)

   **Advanced details:**
   - Leave defaults (no user data needed)

3. **Click "Launch Instance"**

## Step 3: Configure Security Group

### Required Inbound Rules

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | My IP | SSH access |
| Custom TCP | TCP | 5000 | 0.0.0.0/0 | Detection system web access |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Optional: SSL/TLS access |

### Configure Security Group

1. **Go to EC2 → Security Groups**
2. **Find your instance's security group**
3. **Edit inbound rules:**

```
Rule 1 (SSH):
- Type: SSH
- Protocol: TCP
- Port: 22
- Source: My IP (your current IP address)
- Description: SSH access from my location

Rule 2 (Detection System):
- Type: Custom TCP
- Protocol: TCP
- Port: 5000
- Source: 0.0.0.0/0 (Anywhere IPv4)
- Description: Multi-device detection web interface

Rule 3 (Optional - HTTPS):
- Type: HTTPS
- Protocol: TCP
- Port: 443
- Source: 0.0.0.0/0
- Description: HTTPS access for SSL
```

⚠️ **Security Note:** Opening port 5000 to `0.0.0.0/0` allows access from anywhere. For production:
- Consider restricting to specific IP ranges
- Implement authentication (see Security section below)
- Use SSL/TLS with domain and reverse proxy

## Step 4: Connect to EC2 Instance

### From Windows (PowerShell)

```powershell
# Set permissions on key file (first time only)
icacls "C:\path\to\your-key.pem" /inheritance:r
icacls "C:\path\to\your-key.pem" /grant:r "$($env:USERNAME):(R)"

# Connect to instance
ssh -i "C:\path\to\your-key.pem" ec2-user@<EC2_PUBLIC_IP>
```

### Find Your EC2 Public IP

```
EC2 Dashboard → Instances → Select your instance → Copy "Public IPv4 address"
Example: 54.123.45.67
```

## Step 5: Install Docker on EC2

### For Amazon Linux 2

```bash
# Update packages
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add ec2-user to docker group (no sudo needed)
sudo usermod -a -G docker ec2-user

# Apply group changes (logout and login, or run:)
newgrp docker

# Verify installation
docker --version
# Expected: Docker version 20.10.x or higher

# Test Docker
docker run hello-world
```

### For Ubuntu 20.04/22.04

```bash
# Update packages
sudo apt-get update

# Install prerequisites
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add user to docker group
sudo usermod -aG docker ubuntu

# Logout and login again, then verify
docker --version
```

## Step 6: Deploy Docker Image to EC2

### Option A: Using Pre-built Image from Docker Hub (Recommended - Fastest)

The image is already pushed to Docker Hub: **kainosit/openpilot:latest**

```bash
# Create project directory
mkdir -p ~/openpilot-detection
cd ~/openpilot-detection

# Transfer Docker Compose files from your Windows machine (PowerShell):
scp -i "C:\path\to\your-key.pem" `
  docker-compose.yml `
  docker-compose.prod.yml `
  deploy-ec2.sh `
  ec2-user@<EC2_PUBLIC_IP>:~/openpilot-detection/

# On EC2: Make deployment script executable
chmod +x deploy-ec2.sh

# Run automated deployment
./deploy-ec2.sh

# This script will:
# - Check/install Docker if needed
# - Pull latest image from Docker Hub
# - Start container with production config
# - Display access URLs and useful commands
```

### Option B: Manual Deployment (Step-by-step)

```bash
cd ~/openpilot-detection

# Pull latest image
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Start container
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify it's running
docker ps
docker logs openpilot-detection
curl http://localhost:5000/status
```

### Option C: Build on EC2 (Slower, but no Docker Hub needed)

```bash
# Create project directory
mkdir -p ~/openpilot-detection
cd ~/openpilot-detection

# Transfer files from local machine
# From your Windows machine (PowerShell):
scp -i "C:\path\to\your-key.pem" `
  test_yolo_multi_mobile.py `
  Dockerfile `
  docker-compose.yml `
  requirements.txt `
  SYSTEM_DOCUMENTATION.md `
  ec2-user@<EC2_PUBLIC_IP>:~/openpilot-detection/

# Back on EC2:
cd ~/openpilot-detection

# Build Docker image
docker build -t openpilot-detection:latest .

# This takes 5-10 minutes (downloads dependencies)
```

### Option C: Build on EC2 (Slower, but no Docker Hub needed)

```bash
# Create project directory
mkdir -p ~/openpilot-detection
cd ~/openpilot-detection

# Transfer files from local machine
# From your Windows machine (PowerShell):
scp -i "C:\path\to\your-key.pem" `
  test_yolo_multi_mobile.py `
  Dockerfile `
  docker-compose.override.yml `
  requirements.txt `
  SYSTEM_DOCUMENTATION.md `
  ec2-user@<EC2_PUBLIC_IP>:~/openpilot-detection/

# Back on EC2:
cd ~/openpilot-detection

# Build Docker image (takes 5-10 minutes)
docker compose up --build -d
```

**Note:** Option A (pre-built image) is **much faster** and recommended for production. Option C is only needed if you want to build from source on EC2.

### Updating Production Deployment

When you make changes locally and push a new image to Docker Hub:

```bash
# On EC2:
cd ~/openpilot-detection

# Pull latest image
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Restart with new image (zero downtime)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use the deployment script
./deploy-ec2.sh
```

```powershell
# On your Windows machine (after local testing):

# 1. Tag your image
docker tag openpilot-detection:latest YOUR_DOCKERHUB_USERNAME/openpilot-detection:latest

# 2. Login to Docker Hub
docker login
# Enter your Docker Hub username and password

# 3. Push image
docker push YOUR_DOCKERHUB_USERNAME/openpilot-detection:latest

# 4. On EC2:
# ssh to EC2, then:
docker pull YOUR_DOCKERHUB_USERNAME/openpilot-detection:latest

# 5. Run container (see Step 7)
```

### Option C: Push to AWS ECR (Private registry, recommended for production)

```powershell
# On your Windows machine:

# 1. Install AWS CLI
# Download from: https://aws.amazon.com/cli/

# 2. Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (e.g., us-east-1)

# 3. Create ECR repository
aws ecr create-repository --repository-name openpilot-detection --region us-east-1

# 4. Get login command
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 5. Tag image
docker tag openpilot-detection:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/openpilot-detection:latest

# 6. Push to ECR
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/openpilot-detection:latest

# 7. On EC2:
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Pull image
docker pull <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/openpilot-detection:latest
```

## Step 7: Run Container on EC2

### Using Docker Compose (Recommended)

```bash
cd ~/openpilot-detection

# Start container
docker-compose up -d

# Verify it's running
docker-compose ps
# Expected: State = Up

# View logs
docker-compose logs -f

# Check health
docker-compose exec multi-device-detection python -c "
import requests
print(requests.get('http://localhost:5000/status').json())
"
```

### Using Docker Run (Direct)

```bash
# Run container
docker run -d \
  --name openpilot-detection \
  -p 5000:5000 \
  -v model-cache:/root/.cache/torch/hub/checkpoints \
  --restart unless-stopped \
  -e FLASK_ENV=production \
  -e PYTHONUNBUFFERED=1 \
  openpilot-detection:latest

# Verify it's running
docker ps

# View logs
docker logs -f openpilot-detection

# Check health
docker exec openpilot-detection curl http://localhost:5000/status
```

### Configure Auto-Start on Boot

```bash
# Docker Compose method (already configured with restart: unless-stopped)
# OR for docker run:
docker update --restart unless-stopped openpilot-detection

# Verify auto-start
docker inspect openpilot-detection | grep -A 5 RestartPolicy
```

## Step 8: Access Detection System

### From Web Browser

```
http://<EC2_PUBLIC_IP>:5000
```

Example: `http://54.123.45.67:5000`

### From Mobile Device

1. **Ensure mobile device has internet connection** (doesn't need to be on same network)
2. **Open browser on mobile**
3. **Navigate to:** `http://<EC2_PUBLIC_IP>:5000`
4. **Enter device name** (e.g., "Mobile j517")
5. **Click "Start Camera"** and allow permissions
6. **Select device in web interface** and start detection

### Test API Endpoints

```bash
# From EC2
curl http://localhost:5000/status

# From your PC
Invoke-RestMethod -Uri http://<EC2_PUBLIC_IP>:5000/status
```

## Step 9: Monitor and Maintain

### View Container Logs

```bash
# Real-time logs
docker logs -f openpilot-detection

# Last 100 lines
docker logs --tail 100 openpilot-detection

# With timestamps
docker logs -t openpilot-detection

# Save logs to file
docker logs openpilot-detection > detection.log 2>&1
```

### Resource Monitoring

```bash
# Container stats
docker stats openpilot-detection

# EC2 instance metrics
# Go to EC2 Console → Select Instance → Monitoring tab
# View: CPU, Network, Disk I/O

# Install htop for detailed system monitoring
sudo yum install -y htop  # Amazon Linux
sudo apt-get install -y htop  # Ubuntu
htop
```

### Container Management

```bash
# Restart container
docker restart openpilot-detection

# Stop container
docker stop openpilot-detection

# Start container
docker start openpilot-detection

# Remove container (data persists in volumes)
docker rm -f openpilot-detection

# Update container (after new image push)
docker pull openpilot-detection:latest
docker-compose up -d  # Recreates with new image
```

## Step 10: Production Security (Important!)

### 1. Enable HTTPS with SSL/TLS

**Using Nginx Reverse Proxy:**

```bash
# Install Nginx
sudo yum install -y nginx  # Amazon Linux
sudo apt-get install -y nginx  # Ubuntu

# Configure Nginx
sudo nano /etc/nginx/nginx.conf
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    # SSL certificates (use Let's Encrypt certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Install Let's Encrypt SSL Certificate:**

```bash
# Install certbot
sudo yum install -y certbot python-certbot-nginx  # Amazon Linux
sudo apt-get install -y certbot python3-certbot-nginx  # Ubuntu

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (certbot sets this up automatically)
sudo certbot renew --dry-run
```

### 2. Implement Authentication

Edit `test_yolo_multi_mobile.py` to add basic authentication:

```python
from flask import request, Response
from functools import wraps

def check_auth(username, password):
    return username == 'admin' and password == 'your-secure-password'

def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Apply to routes
@app.route('/')
@requires_auth
def index():
    # ... existing code
```

**Better approach:** Use environment variables for credentials:

```python
import os
USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
PASSWORD = os.environ.get('AUTH_PASSWORD', 'changeme')

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD
```

Update docker-compose.yml:

```yaml
environment:
  - AUTH_USERNAME=admin
  - AUTH_PASSWORD=your-secure-password-here
```

### 3. Rate Limiting

Install Flask-Limiter:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/detect', methods=['POST'])
@limiter.limit("30 per minute")
def detect():
    # ... existing code
```

### 4. Firewall Configuration

```bash
# Enable AWS WAF (Web Application Firewall) for advanced protection
# Or use EC2 instance firewall:

# Amazon Linux (firewalld)
sudo yum install -y firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload

# Ubuntu (ufw)
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 5. Regular Updates

```bash
# Create update script
nano ~/update-detection.sh
```

```bash
#!/bin/bash
cd ~/openpilot-detection

# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Clean old images
docker image prune -f

echo "Update complete!"
```

```bash
# Make executable
chmod +x ~/update-detection.sh

# Run updates
./update-detection.sh
```

## Troubleshooting

### Container Not Starting

```bash
# Check logs
docker logs openpilot-detection

# Check Docker service
sudo systemctl status docker

# Restart Docker service
sudo systemctl restart docker

# Check disk space
df -h

# Clean up Docker resources
docker system prune -a
```

### Can't Access from Internet

```bash
# 1. Check Security Group
# EC2 Console → Security Groups → Inbound rules
# Ensure port 5000 is open to 0.0.0.0/0

# 2. Check container is listening
docker port openpilot-detection
# Expected: 5000/tcp -> 0.0.0.0:5000

# 3. Test from EC2
curl http://localhost:5000/status

# 4. Test from internet
curl http://<EC2_PUBLIC_IP>:5000/status

# 5. Check EC2 firewall
sudo iptables -L -n | grep 5000
```

### Performance Issues

```bash
# 1. Check instance type
# Upgrade to larger instance if needed (t3.large → c5.xlarge)

# 2. Monitor resources
htop
docker stats

# 3. Reduce detection resolution
# Edit test_yolo_multi_mobile.py: imgsz=640 → imgsz=480

# 4. Increase confidence threshold
# Edit test_yolo_multi_mobile.py: conf=0.25 → conf=0.40
```

### Model Download Issues

```bash
# Pre-download YOLOv8 model
docker exec openpilot-detection python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
print('Model downloaded successfully')
"

# Verify model cache
docker exec openpilot-detection ls -lh /root/.cache/torch/hub/checkpoints/
```

## Cost Optimization

### 1. Use Spot Instances

- Save up to 90% on EC2 costs
- Good for development/testing
- Not recommended for production (can be terminated)

### 2. Schedule Start/Stop

```bash
# Create start/stop scripts for non-24/7 usage
# Use AWS Lambda + EventBridge to automate

# Stop instance during off-hours
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Start instance
aws ec2 start-instances --instance-ids i-1234567890abcdef0
```

### 3. Use Reserved Instances

- Commit to 1-3 years for 30-70% discount
- Good for production workloads

### 4. Monitor Costs

```bash
# Enable AWS Cost Explorer
# Set up billing alerts in AWS Budgets
# Monitor EC2 usage in AWS Cost & Usage Reports
```

## Backup and Disaster Recovery

### Backup Container Data

```bash
# Backup model cache volume
docker run --rm \
  -v openpilot_model-cache:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/model-cache-backup.tar.gz /data

# Backup container configuration
docker inspect openpilot-detection > container-config-backup.json

# Backup application files
tar czf openpilot-backup-$(date +%Y%m%d).tar.gz \
  test_yolo_multi_mobile.py \
  Dockerfile \
  docker-compose.yml \
  requirements.txt \
  SYSTEM_DOCUMENTATION.md
```

### Create AMI Snapshot

```bash
# EC2 Console → Instances → Select instance
# Actions → Image and templates → Create image
# Name: openpilot-detection-snapshot-YYYY-MM-DD
# Click "Create image"

# Restore from AMI:
# EC2 Console → AMIs → Select AMI → Launch instance from AMI
```

## Scaling Considerations

### Horizontal Scaling (Multiple Instances)

```
Load Balancer
    ↓
    ├─→ EC2 Instance 1 (Docker)
    ├─→ EC2 Instance 2 (Docker)
    └─→ EC2 Instance 3 (Docker)
```

**Use AWS Application Load Balancer (ALB):**
- Distributes traffic across multiple EC2 instances
- Health checks for automatic failover
- SSL/TLS termination

### Vertical Scaling (Larger Instance)

```bash
# 1. Stop instance
# EC2 Console → Select instance → Instance state → Stop instance

# 2. Change instance type
# Actions → Instance settings → Change instance type → c5.xlarge

# 3. Start instance
# Instance state → Start instance

# Note: Docker container will auto-start due to restart policy
```

## Monitoring and Alerts

### CloudWatch Monitoring

```bash
# Enable detailed monitoring
aws ec2 monitor-instances --instance-ids i-1234567890abcdef0

# Create CPU usage alarm
aws cloudwatch put-metric-alarm \
  --alarm-name openpilot-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0
```

### Application Monitoring

```bash
# Install CloudWatch agent on EC2
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U ./amazon-cloudwatch-agent.rpm

# Configure to send logs to CloudWatch
sudo nano /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

## Summary Checklist

- [ ] EC2 instance launched (t3.large or better)
- [ ] Security group configured (SSH + port 5000)
- [ ] Docker installed and running
- [ ] Docker image deployed (built, pulled, or from ECR)
- [ ] Container running and healthy
- [ ] Accessible from internet (http://PUBLIC_IP:5000)
- [ ] Mobile device can connect and stream
- [ ] GPS and OCR features working
- [ ] HTTPS configured with SSL certificate (production)
- [ ] Authentication enabled (production)
- [ ] Monitoring and alerts set up
- [ ] Backup strategy in place
- [ ] Auto-start on boot configured
- [ ] Cost monitoring enabled

## Next Steps

1. ✅ Test system thoroughly with multiple devices
2. ✅ Configure HTTPS and authentication for production
3. ✅ Set up monitoring and alerts
4. ✅ Create backup strategy
5. ✅ Document any custom configurations
6. ✅ Train users on mobile device connection
7. ✅ Monitor costs and optimize as needed

## Additional Resources

- **AWS EC2 Documentation:** https://docs.aws.amazon.com/ec2/
- **Docker Documentation:** https://docs.docker.com/
- **Flask Production Deployment:** https://flask.palletsprojects.com/en/latest/deploying/
- **Let's Encrypt:** https://letsencrypt.org/
- **AWS Cost Calculator:** https://calculator.aws/
- **System Documentation:** See `SYSTEM_DOCUMENTATION.md` in project directory

## Support

For technical issues:
1. Check container logs: `docker logs openpilot-detection`
2. Review EC2 instance metrics in CloudWatch
3. Test API endpoints: `curl http://localhost:5000/status`
4. Check security group and firewall rules
5. Review SYSTEM_DOCUMENTATION.md troubleshooting section

---

**Deployment Complete!** Your multi-device detection system is now running in production on AWS EC2.
