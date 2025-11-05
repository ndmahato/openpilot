# 🔍 Logging Guide - Multi-Device Detection System

## Overview
The system now has comprehensive logging on both **server-side (Python)** and **client-side (JavaScript browser console)** to help you debug issues and monitor system activity.

---

## 📱 Server-Side Logging (Python Terminal)

The Flask server logs all important events with emoji prefixes for easy identification:

### Log Prefixes
- `📱 [INDEX]` - Page access requests
- `📱 [REGISTER]` - Device registration events
- `📸 [UPLOAD]` - Frame upload events (every 10th frame)
- `📊 [STATUS]` - System status queries
- `✅` - Success events
- `❌` - Error events
- `ℹ️` - Information events

### Example Server Logs
```
📱 [INDEX] Page requested from 192.168.1.7
📱 [REGISTER] Device registration from 192.168.1.7: Mobile a1b2 (device_1730000000000_a1b2c3d4)
✅ [REGISTER] New device registered: Mobile a1b2 (device_1730000000000_a1b2c3d4)
📸 [UPLOAD] Device Mobile a1b2: Frame #10
📸 [UPLOAD] Device Mobile a1b2: Frame #20
📊 [STATUS] Status query from 192.168.1.7
📊 [STATUS] Returning 1 device(s) (1 active)
```

### Error Logs
```
❌ [UPLOAD] Missing device_id from 192.168.1.7
❌ [UPLOAD] Device not registered: unknown_device from 192.168.1.7
❌ [UPLOAD] No frame provided by device device_123
❌ [UPLOAD] Exception processing frame from device_123: Invalid image format
❌ [UPLOAD] Processing error for device device_123
```

---

## 🌐 Client-Side Logging (Browser Console)

Open your mobile browser's developer console to see detailed JavaScript logs:

### How to Access Browser Console
- **Chrome Android**: `chrome://inspect` on desktop, connect phone via USB
- **Safari iOS**: Enable Web Inspector in Settings > Safari > Advanced
- **Firefox Android**: `about:debugging` on desktop
- **Desktop Testing**: Press F12 or right-click > Inspect

### Log Prefixes
- `🚀 [INIT]` - Script initialization
- `🆔 [INIT]` - Device ID generation
- `📝 [INIT]` - UI updates
- `📱 [CAMERA]` - Camera system checks
- `📹 [START]` - Camera startup process
- `📸 [UPLOAD]` - Frame uploads (sampled 5%)
- `🚨 [ALERT]` - Critical alerts
- `⚠️ [ALERT]` - Warning alerts
- `🔊 [VOICE]` - Voice announcements
- `✅` - Success events
- `❌` - Error events

### Example Browser Console Logs

#### Successful Startup
```javascript
🚀 [INIT] Script starting...
🆔 [INIT] Device ID: device_1730000000000_a1b2c3d4
📝 [INIT] Setting device info in UI...
✅ [INIT] Device info set successfully
📱 [CAMERA] Page loaded, checking camera support...
✅ [CAMERA] getUserMedia API is supported
🔍 [CAMERA] Enumerating devices...
📹 [CAMERA] Found 2 camera(s): [...]
✅ [CAMERA] System ready with 2 camera(s)
📹 [START] startCamera() called
🔄 [START] Requesting camera access...
📸 [START] Trying environment (back) camera...
✅ [START] Got environment camera stream
🎥 [START] Setting video source...
📝 [START] Registering device with server...
✅ [START] Device registered successfully
🚀 [START] Starting frame upload interval (5 FPS)...
🚀 [START] Starting alert check interval...
✅ [START] Camera system fully initialized
📸 [UPLOAD] Frame uploaded and processed successfully
🚨 [ALERT] CRITICAL: Car ahead at 3 meters - STOP NOW!
🔊 [VOICE] Speaking: Stop! Car ahead!
```

#### Camera Permission Denied
```javascript
🚀 [INIT] Script starting...
🆔 [INIT] Device ID: device_1730000000000_xyz
✅ [INIT] Device info set successfully
📱 [CAMERA] Page loaded, checking camera support...
✅ [CAMERA] getUserMedia API is supported
🔍 [CAMERA] Enumerating devices...
📹 [CAMERA] Found 1 camera(s): [...]
✅ [CAMERA] System ready with 1 camera(s)
📹 [START] startCamera() called
🔄 [START] Requesting camera access...
📸 [START] Trying environment (back) camera...
❌ [START] Camera error: NotAllowedError
```

#### Camera Not Found
```javascript
📱 [CAMERA] Page loaded, checking camera support...
✅ [CAMERA] getUserMedia API is supported
🔍 [CAMERA] Enumerating devices...
📹 [CAMERA] Found 0 camera(s): []
⚠️ [CAMERA] No cameras detected
```

---

## 🔧 Troubleshooting with Logs

### Issue: Page shows "Initializing..." forever

**Check Server Logs:**
```
📱 [INDEX] Page requested from 192.168.1.7
```
If you see this, the page was served successfully.

**Check Browser Console:**
If you DON'T see these logs:
```
🚀 [INIT] Script starting...
🆔 [INIT] Device ID: ...
```

**Solutions:**
1. Hard refresh: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
2. Clear browser cache
3. Try incognito/private mode
4. Check for JavaScript errors (red text in console)

---

### Issue: Camera permission denied

**Browser Console shows:**
```
❌ [START] Camera error: NotAllowedError
```

**Solutions:**
1. Click the camera icon in address bar and allow permission
2. Go to browser settings > Site permissions > Allow camera
3. Check if other apps are using the camera
4. Restart browser

---

### Issue: Frames not uploading

**Server Logs show:**
```
📱 [REGISTER] New device registered: Mobile xyz (device_...)
(No frame upload logs)
```

**Browser Console shows:**
```
✅ [START] Camera system fully initialized
(No upload logs)
```

**Solutions:**
1. Check network connection
2. Verify server IP is accessible: `http://192.168.1.36:5000/status`
3. Look for errors in browser console
4. Check if video element has stream: look for black video preview

---

### Issue: Multiple devices interfering

**Server Logs show:**
```
📱 [REGISTER] New device registered: Mobile abc (device_...)
📱 [REGISTER] New device registered: Mobile xyz (device_...)
📸 [UPLOAD] Device Mobile abc: Frame #10
📸 [UPLOAD] Device Mobile xyz: Frame #10
```

This is **normal** - each device should log separately.

**Check System Status:**
```
http://192.168.1.36:5000/status
```

You should see:
```json
{
  "total_devices": 2,
  "active_devices": 2,
  "devices": [
    {
      "device_id": "device_..._abc",
      "device_name": "Mobile abc",
      "active": true,
      "frame_count": 150
    },
    {
      "device_id": "device_..._xyz",
      "device_name": "Mobile xyz",
      "active": true,
      "frame_count": 145
    }
  ]
}
```

---

## 📊 Monitoring System Health

### Check Active Devices
Visit: `http://192.168.1.36:5000/status`

### Watch Frame Upload Rate
**Server logs** should show frame uploads every 10 frames:
```
📸 [UPLOAD] Device Mobile abc: Frame #10
📸 [UPLOAD] Device Mobile abc: Frame #20
📸 [UPLOAD] Device Mobile abc: Frame #30
```

If frames stop incrementing, the device is frozen or disconnected.

### Monitor Alert Frequency
**Browser console** shows alerts:
```
🚨 [ALERT] CRITICAL: Car ahead at 3 meters - STOP NOW!
⚠️ [ALERT] WARNING: Person on left at 5 meters
```

Too many alerts? Check if camera is moving/shaking.

---

## 🎯 Log Sampling Strategy

To prevent log spam, the system uses **smart sampling**:

### Server-Side
- **Page requests**: Always logged
- **Device registration**: Always logged
- **Frame uploads**: Every 10th frame (10% sampling)
- **Status queries**: Always logged
- **Errors**: Always logged

### Client-Side
- **Initialization**: All events logged
- **Camera startup**: All events logged
- **Frame uploads**: ~5% sampled (1 in 20 frames)
- **CRITICAL alerts**: Always logged
- **WARNING alerts**: 10% sampled
- **SAFE status**: Not logged
- **Voice announcements**: Always logged
- **Errors**: Always logged

---

## 📝 Custom Log Monitoring

### Filter Logs in Browser Console
Use browser console filters:
```javascript
// Show only errors
❌

// Show only alerts
🚨 ⚠️

// Show only uploads
📸 [UPLOAD]

// Show initialization
🚀 [INIT]
```

### Save Server Logs to File
Run server with output redirection:
```bash
python test_yolo_multi_mobile.py > server_log.txt 2>&1
```

Or on Windows PowerShell:
```powershell
python test_yolo_multi_mobile.py | Tee-Object -FilePath server_log.txt
```

---

## 🚨 Common Error Patterns

### Pattern 1: Continuous 404 errors
```
❌ 192.168.1.7 - - "GET /get_alert HTTP/1.1" 404
```
**Cause**: Old cached page without device_id in URL
**Solution**: Hard refresh (Ctrl+Shift+R)

### Pattern 2: Upload errors
```
❌ [UPLOAD] Exception processing frame from device_123: array size mismatch
```
**Cause**: Corrupted frame or encoding issue
**Solution**: Usually self-recovers. If persistent, restart device.

### Pattern 3: No camera logs
```
📱 [CAMERA] Page loaded, checking camera support...
(Nothing else)
```
**Cause**: JavaScript blocked or camera API unsupported
**Solution**: Use Chrome/Firefox, enable JavaScript

---

## 🔄 Cleanup and Maintenance

### Session Cleanup
The server automatically removes inactive devices after 120 seconds:
```
🧹 Cleaned up inactive session: device_... (Mobile xyz)
```

### Memory Management
Each device stores only:
- Latest raw frame
- Latest processed frame
- Current alert

Old frames are automatically discarded.

---

## 📞 Getting Help

When reporting issues, provide:

1. **Server logs** (last 50 lines):
   ```bash
   # Copy from terminal where server is running
   ```

2. **Browser console logs**:
   ```
   # Screenshot or copy full console output
   ```

3. **System status**:
   Visit `http://192.168.1.36:5000/status` and copy JSON

4. **Device info**:
   - Browser: Chrome 120, Firefox 115, etc.
   - OS: Android 13, iOS 17, etc.
   - Camera: Front/Back

---

## ✅ Success Indicators

A fully working system shows:

**Server Terminal:**
```
✅ YOLO model loaded!
✅ Voice assistant ready!
 * Running on http://192.168.1.36:5000
📱 [INDEX] Page requested from 192.168.1.7
📱 [REGISTER] Device registration from 192.168.1.7: Mobile abc
✅ [REGISTER] New device registered
📸 [UPLOAD] Device Mobile abc: Frame #10
📸 [UPLOAD] Device Mobile abc: Frame #20
```

**Browser Console:**
```
🚀 [INIT] Script starting...
✅ [INIT] Device info set successfully
✅ [CAMERA] System ready with 1 camera(s)
✅ [START] Device registered successfully
✅ [START] Camera system fully initialized
📸 [UPLOAD] Frame uploaded and processed successfully
```

---

## 🎓 Advanced: Real-Time Log Streaming

### Stream logs with timestamp:
```bash
python test_yolo_multi_mobile.py | while read line; do echo "$(date '+%H:%M:%S') $line"; done
```

### Monitor specific device:
```bash
# Server logs for device abc
grep "Mobile abc" server_log.txt
```

### Count frames per device:
```bash
# How many frames uploaded by each device
grep "\[UPLOAD\] Device" server_log.txt | cut -d: -f2 | sort | uniq -c
```

---

## 📚 Additional Resources

- **Main Documentation**: `MULTI_DEVICE_README.md`
- **Camera Issues**: `CAMERA_TROUBLESHOOTING.md`
- **This Guide**: `LOGGING_GUIDE.md`

---

**Last Updated**: 2025-11-05  
**System Version**: Multi-Device Detection v2.0 with Enhanced Logging
