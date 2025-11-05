# Docker Compose Usage Guide

This project uses Docker Compose with multiple configuration files for different environments.

## File Overview

- **docker-compose.yml** - Base configuration (uses prebuilt image from Docker Hub)
- **docker-compose.override.yml** - Local development override (builds from Dockerfile)
- **docker-compose.prod.yml** - Production-specific settings for EC2 deployment

## Usage

### Local Development (Docker Desktop)

Build and run from local Dockerfile:
```powershell
# Automatically uses docker-compose.yml + docker-compose.override.yml
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production / EC2 Deployment

Pull and run prebuilt image from Docker Hub:
```bash
# Use production config (skips override, uses prebuilt image)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or simply (if docker-compose.override.yml is not present on EC2)
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Manual Image Pull (for testing)

```powershell
# Pull latest image
docker pull kainosit/openpilot:latest

# Run directly
docker run -d \
  --name openpilot-detection \
  -p 5000:5000 \
  -v model-cache:/root/.cache/torch/hub/checkpoints \
  --restart unless-stopped \
  kainosit/openpilot:latest
```

## How It Works

### Local Development Flow
1. You run `docker-compose up --build`
2. Docker Compose reads `docker-compose.yml` first
3. Then automatically merges `docker-compose.override.yml`
4. The `build` directive in override file takes precedence
5. Image is built from local Dockerfile with your changes

### EC2 Production Flow
1. You run `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
2. Docker Compose reads both files but skips `docker-compose.override.yml`
3. The `image: kainosit/openpilot:latest` directive pulls from Docker Hub
4. No local build happens - faster deployment, consistent image

## EC2 Deployment Steps

1. **SSH to EC2:**
   ```bash
   ssh -i your-key.pem ec2-user@YOUR_EC2_IP
   ```

2. **Install Docker (Amazon Linux 2):**
   ```bash
   sudo yum update -y
   sudo yum install -y docker
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -a -G docker ec2-user
   newgrp docker
   ```

3. **Transfer only docker-compose.yml and docker-compose.prod.yml:**
   ```powershell
   # From Windows (PowerShell)
   scp -i your-key.pem docker-compose.yml ec2-user@YOUR_EC2_IP:~/
   scp -i your-key.pem docker-compose.prod.yml ec2-user@YOUR_EC2_IP:~/
   ```

4. **On EC2, start the container:**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

5. **Verify it's running:**
   ```bash
   docker ps
   docker logs openpilot-detection
   curl http://localhost:5000/status
   ```

6. **Access from browser:**
   - From PC: `http://YOUR_EC2_PUBLIC_IP:5000`
   - From mobile: `http://YOUR_EC2_PUBLIC_IP:5000`

## Updating Production Image

When you make changes and want to deploy a new version:

1. **Build and test locally:**
   ```powershell
   docker-compose up --build
   ```

2. **Push updated image to Docker Hub:**
   ```powershell
   docker tag openpilot-multi-device-detection:latest kainosit/openpilot:latest
   docker push kainosit/openpilot:latest
   ```

3. **Update EC2:**
   ```bash
   # SSH to EC2
   docker compose pull
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

## Environment Variables

Add production secrets to `docker-compose.prod.yml`:

```yaml
environment:
  - AUTH_USERNAME=your_admin_username
  - AUTH_PASSWORD=your_secure_password
  - FLASK_SECRET_KEY=your_random_secret_key
```

## Troubleshooting

### Local build not working
- Ensure `docker-compose.override.yml` exists in project directory
- Check `docker-compose config` to see merged configuration
- Run `docker-compose up --build` to force rebuild

### EC2 pulling old image
- Run `docker compose pull` to get latest image
- Check Docker Hub to verify new image was pushed
- Try pulling specific tag: `docker pull kainosit/openpilot:20251105-2224`

### Port conflicts
- Check if port 5000 is already in use: `netstat -ano | findstr :5000`
- Change port mapping in docker-compose.yml: `"8080:5000"`

## Quick Reference

| Command | Purpose |
|---------|---------|
| `docker-compose up -d` | Start (local dev with build) |
| `docker-compose up --build -d` | Rebuild and start (local dev) |
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` | Start (production with prebuilt image) |
| `docker-compose down` | Stop and remove containers |
| `docker-compose logs -f` | Follow logs |
| `docker-compose ps` | List containers |
| `docker-compose pull` | Pull latest images |
| `docker-compose restart` | Restart containers |

## See Also

- **EC2_DEPLOYMENT_GUIDE.md** - Complete EC2 setup instructions
- **LOCAL_DOCKER_TESTING.md** - Local Docker Desktop testing guide
- **SYSTEM_DOCUMENTATION.md** - Full system documentation
