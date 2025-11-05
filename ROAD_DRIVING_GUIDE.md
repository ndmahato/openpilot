# Road Driving Guide - YOLO Multi-Device Detection System

## 🚗 Using the System While Driving

### IMPORTANT SAFETY NOTICE ⚠️
- **This is an ASSISTIVE tool, NOT autonomous driving**
- **Always keep your eyes on the road**
- **Do not rely solely on the system - it's a backup alert system**
- **You are responsible for safe driving**
- **Test thoroughly in safe conditions before road use**

---

## Quick Start for Road Use

### 1. Enable Road Mode

Edit `test_yolo_multi_mobile.py` and change:
```python
ROAD_MODE = False  # Change to True when using in your car
```
to:
```python
ROAD_MODE = True  # Now optimized for road driving
```

Then restart the server.

### 2. Mount Your Phone

**Recommended Setup:**
- **Location**: Dashboard center or windshield mount
- **Height**: As high as practical (better range of view)
- **Angle**: Level or 5-10° downward tilt
- **Camera**: Should face forward, capturing the road ahead
- **Stability**: Secure mount - vibration reduces accuracy

**What the camera should see:**
```
╔═══════════════════════════════════╗
║  Sky/Buildings (top 20%)          ║
║                                   ║
║  Road ahead + lane (center 60%)   ║  ← Most important
║                                   ║
║  Dashboard/hood (bottom 20%)      ║
╚═══════════════════════════════════╝
```

### 3. Configure Your Setup

Open the file and adjust based on your camera:

**For Wide-Angle Camera (>90° FOV):**
```python
DRIVING_PATH_CENTER_RATIO = 0.35  # Narrower focus on lane
```

**For Normal Camera (60-90° FOV):**
```python
DRIVING_PATH_CENTER_RATIO = 0.45  # Standard lane width
```

**For Narrow Camera (<60° FOV):**
```python
DRIVING_PATH_CENTER_RATIO = 0.50  # Wider to capture full lane
```

---

## Parameter Explanations

### Detection Sensitivity (ROAD_MODE = True)

```python
CRITICAL_SIZE = 0.15  # 15% of frame
```
- Objects occupying 15%+ of frame = CRITICAL (3-5 meters away)
- **Action**: STOP immediately
- **Example**: Person stepping onto road, car braking ahead

```python
WARNING_SIZE = 0.08   # 8% of frame
```
- Objects occupying 8-15% of frame = WARNING (8-10 meters away)
- **Action**: Slow down, prepare to stop
- **Example**: Vehicle ahead slowing, bicycle on roadside

```python
CAUTION_SIZE = 0.03   # 3% of frame
```
- Objects occupying 3-8% of frame = CAUTION (15-20 meters away)
- **Action**: Monitor, be aware
- **Example**: Pedestrian on sidewalk, parked car

### Confidence Threshold

```python
conf_threshold = 0.35  # 35% in ROAD_MODE
```
- Higher threshold = fewer false positives
- Good for fast-moving outdoor scenes
- Reduces distractions from shadows, reflections

**When to adjust:**
- **Lower to 0.30**: If missing real objects (more sensitive)
- **Raise to 0.40**: If too many false alarms (more strict)

### Priority Objects (Road Mode)

```python
HIGH_PRIORITY_OBJECTS = {
    'person', 'child',           # Pedestrians - HIGHEST priority
    'bicycle', 'motorcycle',      # Two-wheelers - unpredictable
    'car', 'truck', 'bus',       # Vehicles - maintain distance
    'dog', 'cat', 'bird',        # Animals - sudden movement
    'traffic light', 'stop sign'  # Signs (if model detects)
}
```

**What gets ignored in Road Mode:**
- Furniture, indoor objects
- Objects outside the driving path (sides of road)
- Stationary objects not in your lane

---

## Real-World Scenarios

### City Driving (30-50 km/h)
```python
CRITICAL_SIZE = 0.15  # Default - good balance
WARNING_SIZE = 0.08
CAUTION_SIZE = 0.03
```
- Alerts give you 1-2 seconds reaction time
- Good for pedestrian-heavy areas

### Highway Driving (80-120 km/h)
```python
CRITICAL_SIZE = 0.12  # Slightly lower = earlier warning
WARNING_SIZE = 0.06
CAUTION_SIZE = 0.02
```
- Earlier warnings due to higher speed
- More time to react

### Narrow Streets
```python
DRIVING_PATH_CENTER_RATIO = 0.55  # Wider detection zone
```
- Catches objects closer to edges
- Good for alleys, residential areas

### Wide Multi-Lane Roads
```python
DRIVING_PATH_CENTER_RATIO = 0.35  # Narrower detection zone
```
- Focus only on your lane
- Ignore adjacent lane traffic

---

## Optimal Conditions

### ✅ Works Best When:
- **Daylight**: Good visibility, clear objects
- **Clear weather**: No heavy rain/fog
- **Moderate speed**: 30-80 km/h
- **Urban/suburban**: Structured roads with visible objects
- **Stable mount**: Minimal phone vibration

### ⚠️ Limitations:
- **Night driving**: Reduced accuracy (headlights help)
- **Heavy rain/fog**: Objects obscured
- **Very high speed**: Less reaction time
- **Extreme angles**: Mount too low/high affects detection
- **Glare**: Direct sun can blind camera

---

## Testing Before Road Use

### Phase 1: Stationary Test (Parked Car)
1. Mount phone, start system
2. Have someone walk in front of car
3. Verify alerts trigger at appropriate distances
4. Check path boundaries align with your lane

### Phase 2: Slow Speed Test (Parking Lot)
1. Drive at 10-20 km/h in empty lot
2. Test with obstacles (cones, boxes)
3. Verify streaming is continuous
4. Check system responsiveness

### Phase 3: Controlled Road Test (Quiet Street)
1. Start on quiet neighborhood street
2. Drive at normal speed (30-40 km/h)
3. Monitor alert timing and accuracy
4. Adjust parameters if needed

### Phase 4: Normal Road Use
1. Only after successful Phase 1-3
2. Start with familiar routes
3. Keep hands on wheel, eyes on road
4. Use as backup awareness system

---

## Troubleshooting on the Road

### "Too many false alerts"
- Increase `conf_threshold` to 0.40
- Narrow `DRIVING_PATH_CENTER_RATIO` to 0.35
- Check camera angle (pointing too high/low?)

### "Missing real objects"
- Decrease `conf_threshold` to 0.30
- Lower `CRITICAL_SIZE` to 0.12
- Clean phone camera lens
- Improve lighting (use headlights)

### "Alerts too late"
- Lower all SIZE thresholds by 0.02-0.03
- Consider you're driving too fast for reaction time
- Check if camera field of view is too narrow

### "Video freezing/lag"
- Reduce phone background apps
- Ensure good WiFi/hotspot connection
- Check server CPU (YOLO processing load)
- Consider upgrading to faster model (yolov8s) if computer is powerful

---

## Network Setup for Car Use

### Option 1: Phone Hotspot + Laptop
```
Phone (Client) ──WiFi──> Laptop (Server running YOLO)
                         └─> Display results back to phone
```
- **Best for**: Powerful laptop, reliable
- **Setup**: Phone creates hotspot, laptop connects, run server
- **Connect**: Phone browser to laptop IP (shown on server start)

### Option 2: Portable WiFi Router + Raspberry Pi
```
Phone (Client) ──WiFi──> Router ──> Raspberry Pi 4/5 (Server)
```
- **Best for**: Permanent installation
- **Setup**: Dedicated hardware, always ready
- **Note**: Raspberry Pi 4/5 can run YOLO but slower

### Option 3: Single Phone (Local Processing)
- Requires running Python + YOLO directly on phone
- Advanced setup, not covered here

---

## Voice Alerts

The system speaks alerts through your laptop/server. To hear them in the car:

### Option 1: Laptop Speakers
- Place laptop where you can hear it
- Set volume appropriately (not too loud)

### Option 2: Bluetooth Speaker
- Connect Bluetooth speaker to server laptop
- Voice will play through speaker

### Option 3: Phone Voice (Client-Side)
- Currently uses Web Speech API
- Toggle "Voice" button in phone UI
- May have delay compared to server voice

---

## Legal & Safety Reminders

1. **Check local laws**: Some regions restrict phone use while driving
2. **Mount securely**: Loose phone = dangerous projectile
3. **Don't interact**: Set up BEFORE driving, don't touch while moving
4. **Driver is responsible**: System is assistive, not autonomous
5. **Regular breaks**: Don't rely on system for fatigue
6. **Test in safe conditions**: Before using on public roads

---

## Advanced Tuning

### For Experienced Users

Edit `test_yolo_multi_mobile.py` and experiment:

```python
# Fine-tune alert distances
CRITICAL_SIZE = 0.15  # Adjust based on your reaction time
WARNING_SIZE = 0.08   # Balance between early warning and false alarms
CAUTION_SIZE = 0.03   # Set based on your awareness level

# Lane focus width
DRIVING_PATH_CENTER_RATIO = 0.45  # Match your camera FOV and lane

# Detection sensitivity
conf_threshold = 0.35  # Higher = fewer false positives, might miss objects
                       # Lower = more sensitive, more false alarms
```

**Recommended Process:**
1. Record your test drive (dashcam or screen record)
2. Review: Did it miss objects? False alarms?
3. Adjust parameters
4. Test again
5. Iterate until comfortable

---

## System Performance

### Frame Rate Targets
- **5 FPS**: Minimum acceptable (current default)
- **10 FPS**: Good for city driving
- **15+ FPS**: Ideal for highway

### Server Requirements
- **CPU**: i5/Ryzen 5 or better for real-time processing
- **RAM**: 4GB+ free
- **GPU**: Optional but recommended (NVIDIA CUDA speeds up 5-10x)

### GPU Acceleration (Optional)
If you have NVIDIA GPU:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```
YOLO will automatically use GPU and process much faster.

---

## Maintenance

- **Clean camera lens daily**: Dirt/smudges reduce accuracy
- **Check mount security**: Vibration loosens mounts
- **Update system monthly**: Newer YOLO models improve over time
- **Monitor false positive rate**: If increasing, recalibrate

---

## Questions?

Common issues documented in `LOGGING_GUIDE.md` and `CAMERA_TROUBLESHOOTING.md`

**Remember**: This is a driver assistance tool. Your eyes and judgment are the primary safety system. Stay alert! 🚗💨
