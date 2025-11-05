# Docker Desktop Testing Guide

This guide helps you test the multi-device detection system using Docker Desktop before deploying to AWS EC2.

## Prerequisites

1. **Docker Desktop** installed and running
   - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Ensure WSL 2 backend is enabled (Settings → General → Use WSL 2 based engine)

2. **Required files in project directory:**
   - `test_yolo_multi_mobile.py` - Main detection system
   - `Dockerfile` - Container image definition
   - `docker-compose.yml` - Docker Compose configuration
   - `requirements.txt` - Python dependencies
   - `.dockerignore` - Build optimization
   - `SYSTEM_DOCUMENTATION.md` - System documentation

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```powershell
# Build and start the container
docker-compose up --build

# Run in detached mode (background)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 2: Using Docker Commands Directly

```powershell
# Build the Docker image
docker build -t openpilot-detection:latest .

# Run the container
docker run -d `
  --name openpilot-detection `
  -p 5000:5000 `
  -v model-cache:/root/.cache/torch/hub/checkpoints `
  --restart unless-stopped `
  openpilot-detection:latest

# View logs
docker logs -f openpilot-detection

# Stop the container
docker stop openpilot-detection

# Remove the container
docker rm openpilot-detection
```

## Testing the System

### 1. Verify Container is Running

```powershell
# Check container status
docker ps

# Expected output:
# CONTAINER ID   IMAGE                       STATUS         PORTS
# abc123def456   openpilot-detection:latest  Up 2 minutes   0.0.0.0:5000->5000/tcp
```

### 2. Check Health Status

```powershell
# View container health
docker inspect openpilot-detection --format='{{.State.Health.Status}}'

# Expected: "healthy" (after ~40 seconds startup time)
```

### 3. Test Web Interface

Open your browser and navigate to:
- **From host machine:** http://localhost:5000
- **From mobile device:** http://[YOUR_PC_IP]:5000
  - Find your PC IP: `ipconfig` (look for IPv4 Address)
  - Example: http://192.168.1.36:5000

### 4. Connect Mobile Device

1. **Ensure mobile device is on the same WiFi network** as your PC
2. **On mobile device:**
   - Open browser
   - Navigate to http://[YOUR_PC_IP]:5000
   - Enter device name (e.g., "Mobile j517")
   - Click "Start Camera"
   - Allow camera and GPS permissions

3. **On host PC:**
   - Open http://localhost:5000
   - Select "MOBILE" detection mode
   - Choose your mobile device from dropdown
   - Click "Start Detection"

### 5. Verify Features

Test each feature to ensure proper functionality:

✅ **Object Detection**
- Point mobile camera at objects (laptop, chair, couch, bed, etc.)
- Verify bounding boxes appear with labels
- Check confidence scores

✅ **GPS Speed Tracking**
- Speed should show as "●GPS" with read-only field
- Indoor testing typically shows 0-1 km/h
- For real testing, try in a moving vehicle

✅ **Speed Limit Detection (OCR)**
- Point camera at speed limit signs
- Limit should show as "●AUTO" with read-only field
- Works with clear, visible speed limit signs (20, 30, 40, 50, 60, 70, 80 km/h)

✅ **Road Safety Alerts**
- Overspeed: Exceeding detected speed limit
- Hazards: Potholes, speed breakers, roadwork
- Traffic Signs: Stop signs, yield signs, traffic lights
- Voice alerts for critical warnings

✅ **Path-Based Detection**
- Path detection mode for intelligent filtering
- Objects only detected when in vehicle's path
- Reduces false positives

## Monitoring and Debugging

### View Real-time Logs

```powershell
# Follow logs
docker logs -f openpilot-detection

# Last 100 lines
docker logs --tail 100 openpilot-detection

# Logs with timestamps
docker logs -t openpilot-detection
```

### Common Log Messages

```
✅ Good:
- "Model loaded successfully"
- "YOLOv8 loaded successfully"
- "Device registered: Mobile j517"
- "GPS speed updated: 15.2 km/h"
- "Speed limit detected: 50 km/h"

⚠️ Warnings:
- "No text extracted from sign" - OCR couldn't read sign
- "No GPS data available" - Mobile device GPS not enabled
- "Connection lost for device: Mobile j517" - Network issue

❌ Errors:
- "Failed to load model" - Model download issue
- "Tesseract not found" - OCR dependency missing
- "Camera not available" - Permission denied
```

### Access Container Shell

```powershell
# Enter container bash
docker exec -it openpilot-detection /bin/bash

# Inside container, you can:
# - Check files: ls -la
# - Test Python: python -c "import cv2; print(cv2.__version__)"
# - Test Tesseract: tesseract --version
# - View processes: ps aux
# - Exit: exit
```

### Resource Usage

```powershell
# Container resource stats (live)
docker stats openpilot-detection

# Expected resources:
# - CPU: 20-60% (spikes to 80% during detection)
# - Memory: 800MB - 1.5GB
# - Network: Varies with video streaming
```

## Troubleshooting

### Container Won't Start

```powershell
# Check build logs
docker-compose build --no-cache

# Check startup logs
docker logs openpilot-detection

# Common issues:
# 1. Port 5000 already in use → Stop other services
# 2. Memory error → Increase Docker Desktop memory (Settings → Resources)
# 3. Build fails → Check internet connection for dependency downloads
```

### Can't Access from Mobile Device

```powershell
# 1. Verify PC IP address
ipconfig

# 2. Check Windows Firewall
# - Open Windows Defender Firewall
# - Allow inbound rule for port 5000
# - Or temporarily disable firewall for testing

# 3. Verify container is listening
docker port openpilot-detection
# Expected: 5000/tcp -> 0.0.0.0:5000

# 4. Test from PC first
# Open http://localhost:5000 in browser
# If this works, issue is network/firewall related
```

### GPS Not Working

```bash
# Check mobile browser console (DevTools)
# Look for Geolocation API errors:
# - "User denied location permission" → Grant permission
# - "Location services disabled" → Enable in device settings
# - "HTTPS required" → GPS works on HTTP for local IPs (192.168.x.x)
```

### OCR Not Detecting Speed Limits

```bash
# 1. Check Tesseract installation in container
docker exec openpilot-detection tesseract --version

# 2. Requirements for good detection:
# - Clear, well-lit sign
# - Sign facing camera directly
# - Numbers large enough (close enough to sign)
# - Minimal glare or shadows

# 3. Test OCR manually:
docker exec openpilot-detection python -c "
import pytesseract
print(pytesseract.get_tesseract_version())
"
```

### Performance Issues

```powershell
# 1. Check Docker Desktop resources
# Settings → Resources:
# - CPUs: Minimum 2, Recommended 4+
# - Memory: Minimum 4GB, Recommended 8GB+
# - Swap: 1GB

# 2. Reduce detection resolution (edit test_yolo_multi_mobile.py):
# Change: imgsz=640 → imgsz=480

# 3. Increase confidence threshold:
# Change: conf=0.25 → conf=0.40
```

## Performance Testing

### Benchmark Detection Speed

Access the `/status` endpoint to check detection performance:

```powershell
# Using PowerShell
Invoke-RestMethod -Uri http://localhost:5000/status | ConvertTo-Json

# Expected response:
# {
#   "status": "healthy",
#   "devices": ["Mobile j517"],
#   "detection_active": true,
#   "fps": 15-25
# }
```

### Load Testing

```powershell
# Multiple mobile devices (if available)
# Connect 2-3 devices simultaneously
# Monitor CPU and memory usage
docker stats openpilot-detection

# Expected limits:
# - 1 device: ~40% CPU, ~1GB RAM
# - 2 devices: ~70% CPU, ~1.5GB RAM
# - 3 devices: ~90% CPU, ~2GB RAM
```

## Cleaning Up

### Remove Containers and Images

```powershell
# Stop and remove container
docker-compose down

# Remove image
docker rmi openpilot-detection:latest

# Remove unused images and cache
docker system prune -a --volumes

# Warning: This removes ALL unused Docker resources
```

### Preserve Model Cache

The YOLOv8 model (~6MB) is cached in a Docker volume to avoid re-downloading.

```powershell
# List volumes
docker volume ls

# Keep the model-cache volume to save bandwidth
# Only remove if you want to free space:
docker volume rm openpilot_model-cache
```

## Next Steps

Once testing is successful in Docker Desktop:

1. ✅ Verify all features work correctly
2. ✅ Test with real mobile devices
3. ✅ Validate GPS and OCR functionality
4. ✅ Check performance and resource usage
5. ➡️ **Proceed to EC2 deployment** (see EC2_DEPLOYMENT_GUIDE.md)

## Additional Resources

- **System Documentation:** See `SYSTEM_DOCUMENTATION.md` for complete feature reference
- **API Documentation:** Section 11 in SYSTEM_DOCUMENTATION.md
- **Docker Documentation:** https://docs.docker.com/
- **Docker Desktop Guide:** https://docs.docker.com/desktop/

## Support

If you encounter issues:

1. Check logs: `docker logs openpilot-detection`
2. Verify health: `docker inspect openpilot-detection`
3. Test connectivity: `curl http://localhost:5000/status`
4. Review SYSTEM_DOCUMENTATION.md troubleshooting section
5. Check Docker Desktop is running and WSL 2 backend is enabled

---

**Ready for EC2 Deployment?** See [EC2_DEPLOYMENT_GUIDE.md](EC2_DEPLOYMENT_GUIDE.md) for production deployment instructions.
