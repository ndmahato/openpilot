# Camera Error Troubleshooting Guide

## Common Camera Errors and Solutions

### 🔴 Error: "NotAllowedError" or "PermissionDeniedError"
**Cause**: Camera permission was denied

**Solutions**:
1. **Grant Permission**:
   - Chrome/Edge: Click the camera icon in address bar → Allow
   - Firefox: Click the lock icon → Permissions → Camera → Allow
   - Safari: Settings → Safari → Camera → Allow

2. **Clear Site Permissions**:
   - Chrome: Settings → Privacy → Site Settings → Camera → Remove blocked sites
   - Firefox: Settings → Privacy → Permissions → Camera → Settings
   
3. **Refresh and try again** after granting permission

---

### 🔴 Error: "NotFoundError" or "DevicesNotFoundError"
**Cause**: No camera detected on device

**Solutions**:
1. Check if camera is being used by another app (close other camera apps)
2. On Android: Check if another browser/app has camera open
3. Verify camera is working (test with native camera app)
4. Try restarting the browser
5. Try a different browser (Chrome recommended)

---

### 🔴 Error: "NotReadableError" or "TrackStartError"
**Cause**: Camera is in use or hardware issue

**Solutions**:
1. Close all other apps using the camera
2. Close all browser tabs with camera access
3. Restart the browser
4. Restart your device
5. Check if camera works in other apps

---

### 🔴 Error: "NotSupportedError"
**Cause**: Browser doesn't support camera API or connection is not secure

**Solutions**:
1. **Use HTTPS**: Camera access requires secure connection on many browsers
   - Instead of `http://192.168.1.36:5000/`
   - Use a reverse proxy with SSL or test on localhost
   
2. **Use supported browser**:
   - ✅ Chrome/Chromium (recommended)
   - ✅ Firefox
   - ✅ Edge
   - ✅ Safari (iOS 11+)
   - ❌ Older browsers may not work

3. **Update browser** to latest version

---

### 🔴 Error: "OverconstrainedError"
**Cause**: Requested camera constraints not available

**Solutions**:
1. The app will automatically fallback to any available camera
2. If still failing, your camera may not support 640x480 resolution
3. Try a different device

---

## Quick Diagnostics

### Step 1: Check Browser Support
Open browser console (F12) and run:
```javascript
navigator.mediaDevices ? "✅ Supported" : "❌ Not Supported"
```

### Step 2: List Available Cameras
```javascript
navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    const cameras = devices.filter(d => d.kind === 'videoinput');
    console.log(`Found ${cameras.length} camera(s):`, cameras);
  });
```

### Step 3: Test Simple Camera Access
```javascript
navigator.mediaDevices.getUserMedia({video: true})
  .then(stream => {
    console.log("✅ Camera working!");
    stream.getTracks().forEach(track => track.stop());
  })
  .catch(err => console.error("❌ Error:", err.name, err.message));
```

---

## Browser-Specific Issues

### Chrome on Android
- **Issue**: Camera permission popup doesn't appear
- **Fix**: Clear site data and reload
  - Settings → Site settings → All sites → Find your site → Clear & reset

### Safari on iOS
- **Issue**: Camera only works in Safari, not other browsers
- **Fix**: This is expected - iOS requires Safari for camera access in web apps

### Firefox
- **Issue**: "NotReadableError" when switching cameras
- **Fix**: Stop the stream completely before requesting new camera:
  ```javascript
  stream.getTracks().forEach(track => track.stop());
  ```

---

## Testing Without Camera

If you don't have a camera or can't get it working, you can:

1. **Use Desktop Webcam**: 
   - Connect to `http://localhost:5000` on your PC
   - Use built-in webcam or USB camera

2. **Use Virtual Camera**:
   - Install OBS Studio or ManyCam
   - Create virtual camera
   - Use as input device

3. **Use Original System**:
   - Run `test_yolo_mobile_stream.py` instead
   - Uses DroidCam or local webcam
   - No browser camera access needed

---

## Network Issues

### Can't Connect to Server
1. Verify server is running: Check terminal shows "Running on http://..."
2. Check firewall: Allow port 5000
3. Verify same WiFi: Both devices on same network
4. Try localhost: On server PC, use `http://localhost:5000`
5. Try IP directly: `http://192.168.1.36:5000` (use your PC's IP)

### Slow/Laggy Video
1. Reduce upload frequency in code (change 200ms to 500ms)
2. Reduce resolution (change 640x480 to 320x240)
3. Check WiFi signal strength
4. Close other network-heavy apps

---

## HTTPS Requirement Workaround

Some browsers require HTTPS for camera access. Options:

### Option 1: Use localhost (works without HTTPS)
- Access from the same PC: `http://localhost:5000`
- Camera access allowed on localhost

### Option 2: Create self-signed SSL certificate
```bash
# Generate certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Modify Flask app to use SSL
app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
```

Access with: `https://192.168.1.36:5000`
(You'll get a security warning - click "Advanced" → "Proceed")

### Option 3: Use ngrok (temporary public HTTPS URL)
```bash
ngrok http 5000
```
Use the `https://` URL provided by ngrok

---

## Still Not Working?

### Check Browser Console
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for error messages
4. Share error details

### Common Console Errors
- `getUserMedia is not defined` → Browser too old
- `TypeError: Cannot read property 'getUserMedia'` → Browser doesn't support camera API
- `SecurityError` → Not HTTPS (required on some browsers)
- `AbortError` → Camera initialization failed (hardware issue)

### System Requirements
- ✅ Modern browser (Chrome 53+, Firefox 36+, Safari 11+, Edge 12+)
- ✅ Working camera hardware
- ✅ Camera permissions granted
- ✅ Same network as server (for mobile access)
- ⚠️ HTTPS recommended (required on some browsers)

---

## Alternative: Use Original Single-Device System

If multi-device camera upload doesn't work, use the original system:

```bash
python test_yolo_mobile_stream.py
```

This streams from a single camera source (DroidCam or webcam) and broadcasts to multiple viewers. Mobile devices view the stream without uploading their own camera.

**Pros:**
- No camera permission issues
- Works over HTTP
- Lower bandwidth usage
- All devices see same view

**Cons:**
- Single camera source only
- Not personalized per device
- All see same alerts

---

## Getting Help

If you're still having issues:

1. **Check server logs**: Look at terminal running the Python script
2. **Check browser console**: Press F12 → Console tab
3. **Test camera**: Try native camera app to verify hardware works
4. **Try different browser**: Chrome usually has best support
5. **Try different device**: Test on another phone/tablet

**Share these details for help:**
- Browser name and version
- Device type (phone/tablet/desktop)
- OS version
- Exact error message from console
- Screenshot of error alert
