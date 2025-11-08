# OpenPilot Multi-Device Detection System

AI-powered object detection system with GPS tracking, OCR speed limit detection, and road safety features. Supports multiple mobile devices streaming to a central detection server.

> Quick Validation Checklist (Road Mode)

For a fast on-road verification, use this compact checklist. Full details in [Road Mode: Use Cases Covered](#road-mode-use-cases-covered) and the [Test Scenarios Checklist](#test-scenarios-checklist).

- Path collision alerts: Center-path objects (person/bicycle/vehicle/animal) escalate CAUTION → WARNING → CRITICAL as they approach; off-center objects don’t trigger collision alerts.
- Speed-adaptive thresholds: At higher speeds (≥60 km/h), warnings trigger earlier than at low speeds (<30 km/h).
- Signs & speed limits: Stop sign proximity alert; traffic light presence notification; speed-limit sign OCR updates HUD speed limit when clear and front-facing.
- Road hazards: Proximity warnings for hazards (e.g., cone, speed bump) when included in the model classes.
- HUD visibility: GPS speed updates ~every 0.5s; speed limit shown; overlays remain readable in fullscreen.
- Voice guidance: CRITICAL continuous, WARNING ~2s, CAUTION ~3s; voice auto-pauses when fully stopped and resumes on movement; respects Voice ON/OFF.
- Controls: Voice toggle and Fullscreen operate correctly during streaming.

## 🚀 Quick Start

### Docker Hub (Production - Recommended)

**⚠️ Note:** The Docker Hub repository is currently private. You need to either:
- Make it public at https://hub.docker.com/repository/docker/kainosit/openpilot/settings/general
- Or run `docker login` before pulling

```bash
docker pull kainosit/openpilot:latest
docker run -d -p 5000:5000 --name openpilot-detection kainosit/openpilot:latest
```

Access at: **http://localhost:5000**

See **[DOCKERHUB_ACCESS_FIX.md](DOCKERHUB_ACCESS_FIX.md)** for solutions.

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

## �️ Road Mode: Use Cases Covered

These road-focused scenarios are implemented and verified in code when Road Mode is enabled:

- Collision warnings in driving path (lane-centric)
  - Pedestrians (person/child)
  - Two-wheelers (bicycle, motorcycle)
  - Vehicles (car, truck, bus)
  - Animals (dog, cat, bird)
  - Only objects in the center “driving path” zone trigger collision alerts, reducing noise from roadside objects

- Speed-adaptive alert distances (dynamic thresholds)
  - Alert thresholds scale with speed: earlier warnings at higher speeds, tighter at low speeds
  - Center-path width tuned for road use (narrower than indoor)

- Traffic sign and control awareness
  - Stop sign proximity alerts (closer than ~15m)
  - Traffic light presence notifications
  - Speed limit sign OCR (Tesseract) to auto-update current limit

- Road hazard proximity framework
  - Potholes, speed bumps/breakers, road damage, construction, barriers, cones
  - Hazards can raise warnings even if slightly outside the center path (within proximity)
  - Note: Actual detection depends on model classes; custom models can extend coverage

- Speed adherence and HUD visibility
  - Current speed (GPS) and detected speed limit shown on HUD
  - Lane/path-only collision logic reduces false positives

- Voice guidance with priority and safety rules
  - CRITICAL: repeating continuously (every check)
  - WARNING: repeats every 2s
  - CAUTION: repeats every 3s
  - Auto-suppression while the vehicle is fully stopped (visual alerts remain active)

### Alert Behavior Summary

- Levels: CRITICAL (red), WARNING (orange), CAUTION (yellow), SAFE (green)
- Polling: alerts checked every 500ms
- Voice: interval by priority; resumes automatically when moving; respects Voice ON/OFF toggle

### Notes & Extensibility

- The hazard/sign lists are configurable; using a custom-trained model can expand on-road coverage
- OCR-based speed limit updates are best-effort; quality depends on sign visibility and lighting

### Test Scenarios Checklist

Use a mobile device in Road Mode and follow these steps to validate each use case. Voice should be toggled ON unless stated.

1) Collision warnings in the driving path (people, bikes, vehicles, animals)
  - Step 1: Position an object (e.g., a person) directly in the center of the camera view (driving path).
  - Step 2: Observe HUD red/yellow/orange banner and bounding box color; read the message (e.g., STOP! PERSON AHEAD).
  - Step 3: Confirm alert levels change with distance: CAUTION → WARNING → CRITICAL as the object approaches.
  - Step 4: Listen to voice: CRITICAL repeats continuously, WARNING repeats ~every 2s, CAUTION ~every 3s.
  - Step 5: Move object to the side (outside center path) and confirm collision alert subsides (path filtering works).

2) Speed-adaptive alert distances (dynamic thresholds)
  - Step 1: While moving slowly (<30 km/h), approach an object; note the distance at which WARNING/CRITICAL triggers.
  - Step 2: Repeat at ~50–60 km/h; confirm warnings trigger earlier (smaller on-screen size) than at low speed.
  - Step 3: Repeat at >60 km/h (if safe); earlier detection should persist consistently.
  - Acceptance: Higher speed → earlier alerts for the same object size/position.

3) Traffic signs and control awareness
  - Stop sign:
    - Step 1: Present a clear stop sign in view; move closer.
    - Step 2: Expect a stop sign alert within close proximity (≈<15m message). Verify banner reflects the sign.
  - Traffic light:
    - Step 1: Present a traffic light; expect presence notification (color detection not enabled by default).
  - Speed limit OCR:
    - Step 1: Present a clean, front-facing speed-limit sign in good light.
    - Step 2: Confirm HUD “Speed Limit” updates, and a log entry indicates detected value.

4) Road hazards proximity framework
  - Step 1: Present a recognized hazard (e.g., cone/speed bump/road work) if included in the model.
  - Step 2: Move within near proximity; expect a WARNING-level banner even if slightly off-center.
  - Note: Actual trigger depends on model classes. If not detected, validate with a class known to be present.

5) Speed + HUD visibility
  - Step 1: With GPS enabled, vary speed and confirm HUD “Current Speed” updates every ~0.5s.
  - Step 2: Confirm “Speed Limit” shows either manual/default (50) or OCR-updated value when detected.
  - Step 3: Ensure all info remains readable in full-screen and overlays do not block critical visuals.

6) Voice guidance and safety suppression
  - Step 1: Enable Voice; trigger a hazard (e.g., person center-path at medium distance).
  - Step 2: While the alert is active, bring the vehicle to a complete stop (<= ~0.5–1 km/h sustained).
  - Step 3: Confirm voice stops automatically while visuals (red box/banner) remain.
  - Step 4: Start moving again; confirm voice resumes with the same priority intervals.

7) Alert behavior cadence & toggles
  - Step 1: With an active WARNING alert, time the spoken messages (≈2s apart).
  - Step 2: With an active CAUTION alert, time messages (≈3s apart).
  - Step 3: Toggle Voice OFF; confirm no speech while visuals continue. Toggle ON to resume.

Acceptance criteria
 - Path-filtered alerts: only center-zone objects drive collision messaging.
 - Dynamic thresholds: higher speed triggers earlier alerts than at low speed for the same object.
 - OCR: speed-limit value updates when a clear sign is visible; does not flicker excessively.
 - Hazards: proximity warnings appear for recognized hazards, even near-path.
 - Voice: interval by priority; pauses when stopped; resumes on movement; respects Voice toggle.

## �📋 System Requirements

### For Local Development
- Docker Desktop with WSL 2 (Windows)
- 8GB RAM minimum (16GB recommended)
- 20GB disk space

### For EC2 Production
- t3.large or better (2 vCPUs, 8GB RAM minimum)
- **Ubuntu 22.04 LTS** (recommended) or Amazon Linux 2
- 20GB EBS storage
- Security Group with port 5000 open

## 📦 Deployment

### Option 1: EC2 Production (5 minutes)

See **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** for step-by-step EC2 deployment.

**Ubuntu 22.04 (Recommended):**
```bash
# On EC2
mkdir ~/openpilot-detection
cd ~/openpilot-detection

# Upload docker-compose files and deploy-ec2.sh, then:
chmod +x deploy-ec2.sh
./deploy-ec2.sh
```

**Amazon Linux 2:**
```bash
# Same commands - the script auto-detects your OS!
chmod +x deploy-ec2.sh
./deploy-ec2.sh
```

The deployment script automatically:
- Detects your OS (Ubuntu or Amazon Linux)
- Installs Docker and Docker Compose
- Pulls the image from Docker Hub
- Starts the container

See **[UBUNTU_VS_AMAZON_LINUX.md](UBUNTU_VS_AMAZON_LINUX.md)** for OS-specific commands.

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
| **[DOCKERHUB_ACCESS_FIX.md](DOCKERHUB_ACCESS_FIX.md)** | 🔒 Fix Docker Hub pull access denied error |
| **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** | 🚀 Deploy to EC2 in 5 minutes (Ubuntu/Amazon Linux) |
| **[UBUNTU_VS_AMAZON_LINUX.md](UBUNTU_VS_AMAZON_LINUX.md)** | 📋 OS-specific command reference |
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
