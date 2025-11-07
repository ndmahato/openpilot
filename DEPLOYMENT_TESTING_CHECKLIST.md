# Deployment Testing Checklist

Use this checklist to verify your EC2 deployment works correctly on Ubuntu.

## Pre-Deployment Checklist

- [ ] EC2 instance launched (t3.large or better)
- [ ] **Ubuntu 22.04 LTS** selected as AMI
- [ ] Security Group configured:
  - [ ] SSH (port 22) from your IP
  - [ ] Custom TCP (port 5000) from 0.0.0.0/0
- [ ] SSH key pair downloaded (.pem file)
- [ ] Public IP noted from EC2 console

## Deployment Steps

### 1. Connect to EC2
- [ ] SSH connection successful:
  ```bash
  ssh -i your-key.pem ubuntu@YOUR_EC2_IP
  ```
- [ ] OS verified as Ubuntu:
  ```bash
  cat /etc/os-release
  # Should show: ID=ubuntu
  ```

### 2. Upload Files
- [ ] From Windows PowerShell, files transferred:
  ```powershell
  scp -i "C:\path\to\your-key.pem" docker-compose.yml ubuntu@YOUR_EC2_IP:~/
  scp -i "C:\path\to\your-key.pem" docker-compose.prod.yml ubuntu@YOUR_EC2_IP:~/
  scp -i "C:\path\to\your-key.pem" deploy-ec2.sh ubuntu@YOUR_EC2_IP:~/
  ```
- [ ] Files exist on EC2:
  ```bash
  ls -la ~/
  # Should show: docker-compose.yml, docker-compose.prod.yml, deploy-ec2.sh
  ```

### 3. Run Deployment Script
- [ ] Script is executable:
  ```bash
  chmod +x deploy-ec2.sh
  ```
- [ ] Script executed successfully:
  ```bash
  ./deploy-ec2.sh
  ```
- [ ] Script detected Ubuntu correctly
- [ ] Docker installed (if wasn't already)
- [ ] Docker Compose plugin installed
- [ ] Image pulled from Docker Hub
- [ ] Container started successfully

### 4. Verify Container Status
- [ ] Container is running:
  ```bash
  docker ps
  # Should show: openpilot-detection with status "Up X minutes (healthy)"
  ```
- [ ] Health check passing:
  ```bash
  docker inspect openpilot-detection --format='{{.State.Health.Status}}'
  # Should show: healthy
  ```
- [ ] Logs show successful startup:
  ```bash
  docker logs openpilot-detection | tail -20
  # Should show: "Running on http://0.0.0.0:5000"
  ```

### 5. Test Local Connectivity (on EC2)
- [ ] Status endpoint responds:
  ```bash
  curl http://localhost:5000/status
  # Should return JSON with "devices":[]
  ```
- [ ] Main page accessible:
  ```bash
  curl -I http://localhost:5000
  # Should return: HTTP/1.1 200 OK
  ```

### 6. Test External Connectivity
- [ ] From your Windows PC browser:
  - [ ] Navigate to `http://YOUR_EC2_PUBLIC_IP:5000`
  - [ ] Page loads successfully
  - [ ] No SSL errors (we're using HTTP, not HTTPS)
  
- [ ] From your mobile device:
  - [ ] Connect to WiFi/4G
  - [ ] Navigate to `http://YOUR_EC2_PUBLIC_IP:5000`
  - [ ] Page loads successfully

### 7. Test Mobile Device Registration
- [ ] On mobile browser:
  - [ ] Enter device name (e.g., "Mobile j517")
  - [ ] Click "Start Camera"
  - [ ] Camera permission granted
  - [ ] Camera preview visible
  
- [ ] On server web interface:
  - [ ] Select "MOBILE" detection mode
  - [ ] Device appears in dropdown
  - [ ] Device name matches what you entered

### 8. Test Object Detection
- [ ] Click "Start Detection" on server
- [ ] Point mobile camera at objects (laptop, chair, person, etc.)
- [ ] Detection results appear with:
  - [ ] Bounding boxes around objects
  - [ ] Object labels (laptop, chair, etc.)
  - [ ] Confidence scores (e.g., 0.85)
- [ ] FPS counter showing 10-25 FPS

### 9. Test GPS Features
- [ ] GPS speed shows as "●GPS" with read-only field
- [ ] Speed value updates (may be 0 if stationary)
- [ ] No GPS errors in mobile browser console

### 10. Test OCR Features
- [ ] Point camera at speed limit sign (if available)
- [ ] Speed limit field shows "●AUTO"
- [ ] Detected speed limit appears (20, 30, 40, 50, etc.)
- [ ] Value is read-only

### 11. Test Voice Alerts
- [ ] Overspeed alert triggers when exceeding limit
- [ ] Voice speaks warning (if audio enabled)
- [ ] Critical alerts work (red background)
- [ ] Warning alerts work (yellow background)

### 12. Test Performance
- [ ] Check container resource usage:
  ```bash
  docker stats openpilot-detection
  # CPU should be 20-60%
  # Memory should be 800MB-1.5GB
  ```
- [ ] System resource usage:
  ```bash
  free -h  # Memory usage
  df -h    # Disk usage
  ```
- [ ] Network latency acceptable (< 200ms)

### 13. Test Container Restart
- [ ] Stop detection on web interface
- [ ] Restart container:
  ```bash
  docker restart openpilot-detection
  ```
- [ ] Wait 30-40 seconds for startup
- [ ] Test again - should work without issues

### 14. Test Firewall (if enabled)
- [ ] Check UFW status:
  ```bash
  sudo ufw status
  ```
- [ ] If active, port 5000 should be allowed
- [ ] If not, allow it:
  ```bash
  sudo ufw allow 5000/tcp
  ```

### 15. Test Updates
- [ ] Pull latest image:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
  ```
- [ ] Restart with new image:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
  ```
- [ ] Verify still working

## Common Issues & Solutions

### ❌ Issue: "Permission denied" when running docker
**✅ Solution:**
```bash
sudo usermod -aG docker ubuntu
newgrp docker
# Or logout and login again
```

### ❌ Issue: "docker compose: command not found"
**✅ Solution:**
```bash
# The script should install it, but if not:
sudo apt-get update
sudo apt-get install -y docker-compose-plugin
docker compose version
```

### ❌ Issue: Cannot access from browser
**✅ Solution:**
1. Check Security Group (port 5000 inbound)
2. Check firewall: `sudo ufw status`
3. Test locally first: `curl http://localhost:5000/status`
4. Verify container running: `docker ps`

### ❌ Issue: Container not healthy
**✅ Solution:**
```bash
docker logs openpilot-detection
# Look for errors
# Wait up to 60 seconds for model to load
```

### ❌ Issue: GPS not working on mobile
**✅ Solution:**
1. Grant location permission in browser
2. Use HTTPS (or HTTP with 192.168.x.x local IP works too)
3. Check browser console for errors
4. Ensure location services enabled on device

### ❌ Issue: OCR not detecting signs
**✅ Solution:**
1. Ensure sign is clear and well-lit
2. Move closer to sign
3. Sign should face camera directly
4. Test Tesseract:
   ```bash
   docker exec openpilot-detection tesseract --version
   ```

## Success Criteria

All of the following should be true:

✅ Container status: "Up X minutes (healthy)"  
✅ Web interface accessible from external browser  
✅ Mobile device can register and stream camera  
✅ Object detection working with 10+ FPS  
✅ GPS speed showing (even if 0 when stationary)  
✅ Speed limit field shows ●AUTO indicator  
✅ Voice alerts functional  
✅ Container auto-restarts after reboot  
✅ Resource usage acceptable (< 60% CPU, < 2GB RAM)  

## Post-Deployment

- [ ] Document your EC2 public IP
- [ ] Save SSH key in secure location
- [ ] Note any custom configurations
- [ ] Set up CloudWatch monitoring (optional)
- [ ] Configure automatic backups (optional)
- [ ] Enable HTTPS with Let's Encrypt (production)
- [ ] Add authentication (production)

## Monitoring Commands

Use these regularly:

```bash
# Check container status
docker ps

# View logs (last 50 lines)
docker logs --tail 50 openpilot-detection

# Follow logs in real-time
docker logs -f openpilot-detection

# Check resource usage
docker stats openpilot-detection

# Check system resources
htop  # Install with: sudo apt-get install -y htop

# Check disk space
df -h

# Check memory
free -h

# View active connections
sudo netstat -tulpn | grep 5000
```

## Next Steps

Once everything is working:

1. **Test with real driving** - Take your mobile device in a car
2. **Test multiple devices** - Connect 2-3 mobile devices
3. **Optimize performance** - Adjust detection confidence, image size
4. **Set up HTTPS** - Use Let's Encrypt + Nginx for production
5. **Add authentication** - Secure the web interface
6. **Monitor costs** - Check AWS billing regularly
7. **Create AMI backup** - Snapshot your working configuration

---

**Congratulations!** If all checks pass, your OpenPilot detection system is successfully deployed on Ubuntu EC2! 🎉
