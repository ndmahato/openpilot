# OpenPilot Multi-Device Detection System

AI-powered object detection system with GPS tracking, OCR speed limit detection, and road safety features. Supports multiple mobile devices streaming to a central detection server.

## 🚀 Quick Start

### Docker Hub (Production - Recommended)
```bash
docker pull kainosit/openpilot:latest
docker run -d -p 5000:5000 --name openpilot-detection kainosit/openpilot:latest
```

Access at: **http://localhost:5000**

### Local Development
```powershell
git clone https://github.com/ndmahato/openpilot.git
cd openpilot
docker-compose up --build -d
```

## ✨ Features

- 🎯 **YOLOv8 Object Detection** - 80+ object classes with real-time detection
- 📱 **Multi-Device Support** - Connect unlimited mobile devices simultaneously
- 🌍 **GPS Speed Tracking** - Automatic speed calculation from device location
- 🚦 **OCR Speed Limit Detection** - Reads speed limit signs using Tesseract OCR
- ⚠️ **Road Safety Alerts** - Overspeed warnings, hazard detection, traffic sign recognition
- 🗣️ **Voice Alerts** - Text-to-speech warnings for critical events
- 🛣️ **Path-Based Detection** - Intelligent filtering for objects in vehicle's path
- 🔄 **Real-time Streaming** - Low-latency video processing
- 💾 **Session Management** - Per-device state and alert history

## 📋 System Requirements

### For Local Development
- Docker Desktop with WSL 2 (Windows)
- 8GB RAM minimum (16GB recommended)
- 20GB disk space

### For EC2 Production
- t3.large or better (2 vCPUs, 8GB RAM minimum)
- 20GB EBS storage
- Security Group with port 5000 open

## 📦 Deployment

### Option 1: EC2 Production (5 minutes)

See **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** for step-by-step EC2 deployment.

```bash
# On EC2
mkdir ~/openpilot-detection
cd ~/openpilot-detection

# Upload docker-compose files, then:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Option 2: Local Docker Desktop

See **[LOCAL_DOCKER_TESTING.md](LOCAL_DOCKER_TESTING.md)** for detailed testing guide.

```powershell
# Clone and run
docker-compose up --build -d

# Access at http://localhost:5000
# Mobile devices: http://YOUR_PC_IP:5000
```

## 🗂️ Project Structure

```
openpilot/
├── test_yolo_multi_mobile.py       # Main Flask application
├── Dockerfile                       # Docker image definition
├── docker-compose.yml               # Base compose config (uses Docker Hub)
├── docker-compose.override.yml     # Local dev override (builds from source)
├── docker-compose.prod.yml         # Production-specific settings
├── requirements.txt                 # Python dependencies
├── deploy-ec2.sh                   # Automated EC2 deployment script
│
├── SYSTEM_DOCUMENTATION.md         # Complete system documentation
├── QUICK_DEPLOY.md                 # 5-minute EC2 deployment guide
├── DOCKER_COMPOSE_GUIDE.md         # Docker Compose usage guide
├── LOCAL_DOCKER_TESTING.md         # Local testing guide
├── EC2_DEPLOYMENT_GUIDE.md         # Detailed EC2 guide
│
└── check-docker-status.ps1         # Docker diagnostics script (Windows)
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** | 🚀 Deploy to EC2 in 5 minutes |
| **[SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md)** | 📖 Complete system reference (50+ pages) |
| **[DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)** | 🐳 Docker Compose usage for dev/prod |
| **[LOCAL_DOCKER_TESTING.md](LOCAL_DOCKER_TESTING.md)** | 💻 Local Docker Desktop testing |
| **[EC2_DEPLOYMENT_GUIDE.md](EC2_DEPLOYMENT_GUIDE.md)** | ☁️ Detailed AWS EC2 deployment |

## 🎮 Usage

### 1. Start the Server
```bash
docker-compose up -d
```

### 2. Connect Mobile Device
1. Open browser on mobile device
2. Navigate to `http://SERVER_IP:5000`
3. Enter device name (e.g., "Mobile j517")
4. Click "Start Camera" and allow permissions

### 3. Start Detection
1. On server web interface, select "MOBILE" mode
2. Choose your device from dropdown
3. Click "Start Detection"

### 4. Monitor Alerts
- View real-time detection on screen
- Listen for voice alerts (overspeed, hazards, signs)
- Check GPS speed (automatic)
- See detected speed limits (automatic OCR)

## 🔧 Configuration

### Environment Variables

Edit `docker-compose.prod.yml` for production:

```yaml
environment:
  - FLASK_ENV=production
  - AUTH_USERNAME=admin              # Optional: Basic auth
  - AUTH_PASSWORD=secure_password    # Optional: Basic auth
  - GPS_UPDATE_INTERVAL=2            # Optional: GPS update frequency (seconds)
```

### Detection Parameters

Edit `test_yolo_multi_mobile.py`:

```python
# Detection confidence threshold
conf=0.25  # 0.0 to 1.0 (higher = fewer false positives)

# Image size (lower = faster, less accurate)
imgsz=640  # 480, 640, 1280

# Speed limit default
speed_limit = 50  # km/h (overridden by OCR detection)
```

## 🛠️ Development

### Local Build
```powershell
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f

# Restart
docker-compose restart
```

### Push to Docker Hub
```powershell
# Build locally
docker-compose up --build

# Tag and push
docker tag openpilot-multi-device-detection:latest kainosit/openpilot:latest
docker push kainosit/openpilot:latest
```

### Update EC2
```bash
# SSH to EC2
ssh -i your-key.pem ec2-user@YOUR_EC2_IP

# Pull and restart
cd ~/openpilot-detection
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🔍 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Main web interface |
| `/register_device` | POST | Register new mobile device |
| `/video_feed/<device_id>` | GET | Stream video from device |
| `/upload_frame` | POST | Upload frame from mobile |
| `/start_detection` | POST | Start detection for device |
| `/stop_detection` | POST | Stop detection |
| `/get_alert` | GET | Get latest alert for device |
| `/status` | GET | System status (health check) |
| `/update_gps` | POST | Update GPS speed from device |

See **[SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md)** Section 11 for detailed API reference.

## 🐛 Troubleshooting

### Docker not working?
```powershell
.\check-docker-status.ps1
```

### Container not starting?
```bash
docker logs openpilot-detection
```

### Can't access from mobile?
- Check Windows Firewall (allow port 5000)
- Verify same WiFi network
- Check PC IP: `ipconfig` (Windows) or `ip addr` (Linux)

### GPS not working?
- Allow location permissions on mobile browser
- HTTPS not required for local IPs (192.168.x.x)
- Check browser console for errors

### OCR not detecting signs?
- Ensure sign is clear and well-lit
- Move closer to sign
- Sign should face camera directly
- Check Tesseract is installed: `docker exec openpilot-detection tesseract --version`

See **[SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md)** Section 12 for complete troubleshooting guide.

## 📊 Performance

- **Detection Speed:** 15-25 FPS (YOLOv8n on t3.large)
- **Latency:** 100-200ms (local network)
- **Memory Usage:** 800MB - 1.5GB per device
- **CPU Usage:** 40-60% per device (spikes to 80% during detection)

## 🔒 Security

### Production Recommendations

1. **Enable HTTPS** with Let's Encrypt + Nginx
2. **Add authentication** (basic auth or OAuth)
3. **Use environment variables** for secrets
4. **Restrict Security Groups** to known IPs
5. **Enable rate limiting** with Flask-Limiter
6. **Regular updates** of base image and dependencies

See **[EC2_DEPLOYMENT_GUIDE.md](EC2_DEPLOYMENT_GUIDE.md)** Section 10 for security setup.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker locally
5. Submit a pull request

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

- **YOLOv8** by Ultralytics - Object detection model
- **Tesseract OCR** - Speed limit sign recognition
- **Flask** - Web framework
- **OpenCV** - Computer vision library
- **Docker** - Containerization platform

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/ndmahato/openpilot/issues)
- **Documentation:** See markdown files in repository
- **Docker Hub:** [kainosit/openpilot](https://hub.docker.com/r/kainosit/openpilot)

---

**Ready to deploy?** Start with **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** for the fastest path to production!
