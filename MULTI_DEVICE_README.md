# Multi-Device YOLO Detection System

## Overview
This system allows **multiple mobile devices** to connect simultaneously, each with their own camera feed and receiving personalized real-time object detection alerts.

## Features
- ✅ **Multi-device support** - Connect unlimited mobile devices
- ✅ **Individual sessions** - Each device has its own detection stream
- ✅ **Personalized alerts** - Each device receives alerts only for objects in their driving path
- ✅ **Real-time processing** - YOLOv8 object detection on server
- ✅ **Voice alerts** - Optional voice warnings for critical/warning levels
- ✅ **Path-based detection** - Only alerts for objects in center 40% of frame
- ✅ **Automatic cleanup** - Inactive devices removed after 2 minutes

## How to Use

### 1. Start the Server
```bash
python test_yolo_multi_mobile.py
```

The server will display:
```
📱 MOBILE ACCESS:
   Open browser on your mobile devices and go to:
   http://192.168.1.36:5000/
```

### 2. Connect Mobile Devices

On **each mobile device**:
1. Open a web browser (Chrome, Safari, Firefox, etc.)
2. Navigate to `http://192.168.1.36:5000/` (use your server's IP)
3. Click **"📷 Start Camera & Detection"**
4. Allow camera access when prompted
5. Optionally enable voice alerts with **"🔊 Voice"** button

### 3. What Each Device Sees

Each mobile device will show:
- **Local camera feed** (what your camera sees)
- **Processed video** (with detection boxes and alerts)
- **Alert banner** (color-coded: Red=Critical, Orange=Warning, Yellow=Caution, Green=Safe)
- **Device ID** (unique identifier for this session)
- **Connection status**

## System Architecture

### Device Session Management
```python
{
  "device_id": "device_1730842345_xyz",
  "device_name": "Mobile xyz",
  "latest_frame": <camera frame from device>,
  "processed_frame": <frame with detections>,
  "current_alert": {
    "level": "WARNING",
    "message": "⚠️ SLOW DOWN! PERSON AHEAD - 1.5m",
    "voice_message": "Slow down! Person ahead",
    "has_alert": true
  }
}
```

### Flow Diagram
```
Mobile Device 1                    Mobile Device 2
     |                                   |
     | uploads frame (200ms)             | uploads frame (200ms)
     ↓                                   ↓
     +-----------------------------------+
     |        Flask Server               |
     |  - Registers device sessions      |
     |  - Processes frames independently |
     |  - YOLOv8 detection per device    |
     |  - Generates personalized alerts  |
     +-----------------------------------+
           ↓                        ↓
      Processed                 Processed
      Frame + Alert             Frame + Alert
           ↓                        ↓
     Mobile 1 Display          Mobile 2 Display
```

## API Endpoints

### `GET /`
Main HTML page for mobile devices

### `POST /register_device`
Register a new device session
```json
{
  "device_id": "device_xxx",
  "device_name": "Mobile xxx"
}
```

### `POST /upload_frame`
Upload camera frame for processing
- Form data: `frame` (image file), `device_id` (string)
- Returns: Processed frame with detections

### `GET /get_alert/<device_id>`
Get current alert for specific device
```json
{
  "has_alert": true,
  "message": "🚨 STOP! PERSON AHEAD - 0.5m",
  "voice_message": "Stop now! Person ahead",
  "level": "CRITICAL",
  "timestamp": 1730842345.67
}
```

### `GET /status`
View all connected devices and system status
```json
{
  "total_devices": 3,
  "active_devices": 2,
  "devices": [
    {
      "device_id": "device_1730842345_abc",
      "device_name": "Mobile abc",
      "is_active": true,
      "frame_count": 234,
      "last_update": 1730842400.12
    }
  ]
}
```

## Configuration

### Adjust Detection Sensitivity
In `test_yolo_multi_mobile.py`:
```python
CRITICAL_SIZE = 0.20    # 20% of frame = 0.5m distance
WARNING_SIZE = 0.10     # 10% of frame = 1.5m distance
CAUTION_SIZE = 0.04     # 4% of frame = 3.0m distance
```

### Adjust Driving Path Width
```python
DRIVING_PATH_CENTER_RATIO = 0.40  # 40% of frame width
# Try 0.30 for narrower path or 0.50 for wider path
```

### Adjust Upload Rate
In the HTML JavaScript:
```javascript
uploadInterval = setInterval(uploadFrame, 200); // 5 FPS (200ms)
// Lower = more frequent updates, higher CPU usage
```

## Alert Levels

| Level | Color | Distance | Action |
|-------|-------|----------|--------|
| **CRITICAL** | 🔴 Red | 0.5m | STOP! Immediate danger |
| **WARNING** | 🟠 Orange | 1.5m | SLOW DOWN! Approaching |
| **CAUTION** | 🟡 Yellow | 3.0m | Be careful |
| **SAFE/MONITOR** | 🟢 Green | 5.0m+ | All clear |

## High Priority Objects
These objects get boosted priority for alerts:
- People (person)
- Animals (dog, cat)
- Vehicles (car, truck, bus, bicycle, motorcycle)

## Troubleshooting

### "Camera access denied"
- Grant camera permissions in browser settings
- Use HTTPS or localhost for camera access
- Try different browser (Chrome recommended)

### "Device not registered"
- Refresh the page
- Clear browser cache
- Check device ID in localStorage

### "No processed video"
- Check server is running
- Verify network connection
- Open browser console for errors
- Check `/status` endpoint

### Multiple devices not working
- Ensure all devices on same WiFi
- Check firewall settings
- Verify server port 5000 is accessible
- Monitor server logs for registration messages

## Performance Tips

1. **Server Hardware**: GPU recommended for faster detection
2. **Network**: Good WiFi required for smooth streaming
3. **Frame Rate**: Adjust upload interval based on connection speed
4. **Cleanup**: Inactive devices auto-removed after 2 minutes

## Testing with Multiple Devices

### Single Device Testing
1. Start server
2. Connect one mobile device
3. Move camera around to detect objects
4. Verify alerts appear and voice works

### Multiple Device Testing
1. Start server
2. Connect Device 1 from Phone A
3. Connect Device 2 from Phone B
4. Point devices at different scenes
5. Verify each gets independent alerts
6. Check `/status` to see all devices

### Simulate Multiple Devices
- Open multiple browser tabs on same phone
- Each tab gets separate device ID
- Each tab can access camera independently

## Example Use Cases

1. **Multiple Drivers**: Each driver in a vehicle fleet gets personalized alerts
2. **Training**: Multiple trainees practice with individual feedback
3. **Surveillance**: Multiple cameras monitor different areas
4. **Comparison**: Test different camera positions/angles simultaneously

## System Monitoring

Check system status at: `http://192.168.1.36:5000/status`

Shows:
- Total connected devices
- Active vs inactive devices
- Frame counts per device
- Last update timestamps

## Security Note
⚠️ This is a development server. For production:
- Use HTTPS with SSL certificates
- Add authentication/authorization
- Deploy with production WSGI server (gunicorn, uWSGI)
- Implement rate limiting
- Add device validation

## Requirements
```bash
pip install opencv-python numpy ultralytics pyttsx3 flask pillow
```

## Comparison: Single vs Multi-Device

| Feature | Single Device (old) | Multi-Device (new) |
|---------|--------------------|--------------------|
| Concurrent users | 1 | Unlimited |
| Camera source | PC webcam or single IP cam | Each mobile's camera |
| Alert system | Shared | Individual per device |
| Session tracking | None | Per-device sessions |
| Processing | Single stream | Parallel per device |
| Scalability | Limited | High |

## Future Enhancements
- [ ] WebRTC for lower latency
- [ ] Cloud deployment support
- [ ] Device grouping/teams
- [ ] Alert history per device
- [ ] Video recording per session
- [ ] Real-time dashboard with all devices
- [ ] Mobile app (native iOS/Android)

---

**Created**: November 5, 2025  
**Version**: 1.0  
**License**: MIT
