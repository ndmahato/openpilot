# 🚗 Road Safety Features Guide

## Overview
The object detection system now includes comprehensive road safety features designed to alert drivers to potential hazards, traffic control devices, and speed violations. These features work in conjunction with the existing path-based object detection to provide a complete driving assistance system.

## Features

### 1. Overspeed Alerts 🚨
**Purpose:** Alert when vehicle speed exceeds the configured speed limit  
**How it works:**
- Default speed limit: 50 km/h
- User-adjustable from 10-200 km/h via UI
- Automatically compares current speed to limit
- Only active in Road Mode

**Alert Format:**
```
🚨 OVERSPEED! 65km/h in 50km/h zone (+15km/h)
```

**Voice Alert:**
```
"Over speed. Slow down to 50 kilometers per hour"
```

**Configuration:**
- UI: Settings panel → Speed Limit input (10-200 km/h, step: 10)
- Default: 50 km/h
- Updates in real-time

---

### 2. Road Hazard Detection ⚠️
**Purpose:** Detect and alert about road surface conditions and construction hazards  
**Detected Hazards:**
- Potholes 🕳️
- Speed bumps/breakers
- Road damage
- Construction zones
- Barriers
- Traffic cones

**Alert Format:**
```
⚠️ SPEED BREAKER ahead | CAUTION! CAR CENTER - 8m
⚠️ POTHOLE, CONSTRUCTION ahead | Monitor: TRUCK RIGHT - 12m
```

**Voice Alert:**
```
"Speed breaker ahead. Slow down"
"Pothole ahead. Slow down"
```

**Smart Deduplication:**
- Prevents alert spam: same hazard won't trigger alert for 3 seconds
- Uses spatial clustering: hazards within ~50 pixels horizontally are grouped

**Distance Estimation:**
- Based on vertical position in frame
- Bottom of frame (~80%+) = 2-5m
- Middle of frame (~50-80%) = 5-15m
- Top of frame (~0-50%) = 15-50m

---

### 3. Traffic Sign Recognition 🚦
**Purpose:** Detect traffic control devices and regulatory signs  
**Supported Signs:**
- Stop signs 🛑
- Traffic lights 🚦
- Yield signs
- Speed limit signs
- No entry signs
- One way signs
- Parking signs

**Alert Examples:**
```
STOP sign ahead - 12m | WARNING! PERSON LEFT - 6m
Traffic light ahead | All clear
```

**Stop Sign Behavior:**
- Alert triggered within 15 meters
- Includes distance estimate
- Critical level if obstructing path

**Traffic Light Detection:**
- Detects presence of traffic light
- Future enhancement: color detection (red/yellow/green)

---

### 4. Speed-Based Dynamic Thresholds ⚡
**Purpose:** Adjust detection sensitivity based on vehicle speed  
**Speed Ranges & Multipliers:**

| Speed Range | Multiplier | Critical | Warning | Caution |
|-------------|------------|----------|---------|---------|
| 0-30 km/h   | 1.1x       | 3.3m     | 5.5m    | 8.8m    |
| 30-60 km/h  | 1.0x       | 3.0m     | 5.0m    | 8.0m    |
| 60-90 km/h  | 0.85x      | 4.2m     | 7.1m    | 11.8m   |
| 90+ km/h    | 0.7x       | 6.4m     | 10.7m   | 17.1m   |

**Effect:**
- Higher speeds = Earlier warnings
- Lower speeds = Shorter distances
- Automatic adjustment in real-time

---

## User Interface

### Settings Panel
```
⚙️ Detection Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚗 Road Mode:        [Toggle Switch]
⚡ Current Speed:    [___0___] km/h
🚦 Speed Limit:      [__50___] km/h

Indoor Mode: Shorter distances, all objects
Road Mode: Longer distances, road objects only
Current Speed: Higher speed = earlier warnings
Speed Limit: Get overspeed alerts (Road Mode only)
```

### Controls:
1. **Road Mode Toggle:**
   - Off: Indoor mode (all objects, shorter distances)
   - On: Road mode (priority objects, longer distances)

2. **Current Speed Input:**
   - Range: 0-200 km/h
   - Step: 5 km/h
   - Updates: Real-time (syncs every 2 seconds)
   - Use: Adjust detection thresholds dynamically

3. **Speed Limit Input:**
   - Range: 10-200 km/h
   - Step: 10 km/h
   - Updates: Immediately on change
   - Use: Set overspeed alert threshold

---

## Alert Priority System

### Priority Levels (Highest to Lowest):

1. **CRITICAL - Immediate Collision Risk**
   - Overspeed violations
   - Objects < 3m in driving path
   - Color: Red (#f00)
   - Icon: 🚨

2. **WARNING - Imminent Hazard**
   - Road hazards within 20m
   - Objects 3-5m in driving path
   - Color: Orange (#ff0)
   - Icon: ⚠️

3. **CAUTION - Attention Required**
   - Traffic signs ahead
   - Objects 5-8m in driving path
   - Color: Yellow (#ff0)
   - Icon: ⚡

4. **SAFE - Monitoring**
   - Objects > 8m away
   - Path clear
   - Color: Green (#0f0)
   - Icon: ✓

### Combined Alert Example:
When multiple conditions occur:
```
🚨 OVERSPEED! 75km/h in 50km/h zone (+25km/h) | ⚠️ SPEED BREAKER ahead | CRITICAL! PERSON CENTER - 4m
```

Order: Overspeed → Road Hazards → Collision Warnings → Other

---

## Technical Implementation

### Object Categories

**HIGH_PRIORITY_OBJECTS** (Collision Detection):
```python
{'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 
 'dog', 'cat', 'horse', 'sheep', 'cow', 'elephant', 'bear', 
 'zebra', 'giraffe'}
```

**ROAD_HAZARDS** (Surface Conditions):
```python
{'pothole', 'speed bump', 'speed breaker', 'road damage', 
 'construction', 'barrier', 'cone'}
```

**TRAFFIC_SIGNS** (Regulatory Control):
```python
{'stop sign', 'traffic light', 'yield sign', 'speed limit', 
 'no entry', 'one way', 'parking sign'}
```

### Detection Flow

1. **Frame Processing**
   ```
   Frame Uploaded → YOLO Detection → Categorization
   ↓
   HIGH_PRIORITY_OBJECTS → Collision Detection (path-based)
   ROAD_HAZARDS → Distance estimation → Alert if < 20m
   TRAFFIC_SIGNS → Special handling (stop signs, lights)
   ↓
   Speed Check → Overspeed alert if speed > limit
   ↓
   Combine alerts by priority → Display & Voice
   ```

2. **Hazard Deduplication**
   ```python
   recent_hazards = {
       'pothole_15': 1704123456.789,  # Timestamp
       'speed_bump_20': 1704123457.123
   }
   # Same hazard ignored for 3 seconds
   ```

3. **Distance Calculation**
   - **Collision objects:** Based on bounding box size
   - **Road hazards:** Based on vertical position in frame
   - **Assumes:** Camera mounted looking ahead at road level

---

## API Endpoints

### Update Settings
**POST** `/update_settings`
```json
{
  "device_id": "device-abc123",
  "road_mode": true,          // Optional
  "speed": 65.0,              // Optional (km/h)
  "speed_limit": 80.0         // Optional (km/h)
}
```

**Response:**
```json
{
  "status": "updated",
  "road_mode": true,
  "speed": 65.0,
  "speed_limit": 80.0
}
```

### Get Settings
**GET** `/get_settings/<device_id>`

**Response:**
```json
{
  "road_mode": true,
  "speed": 65.0,
  "speed_limit": 80.0,
  "device_name": "Mobile-1"
}
```

### Status (Enhanced)
**GET** `/status`

**Response:**
```json
{
  "active_devices": 2,
  "devices": {
    "device-abc123": {
      "name": "Mobile-1",
      "last_frame": "2024-01-02 14:30:45",
      "alert_level": "CRITICAL",
      "alert_msg": "🚨 OVERSPEED! 75km/h in 50km/h zone",
      "road_mode": true,
      "speed": 75.0,
      "speed_limit": 50.0
    }
  }
}
```

---

## Voice Alerts

### Voice Assistant Configuration
- Engine: pyttsx3 (Microsoft Zira)
- Rate: 150 words/minute
- Volume: 1.0 (100%)
- Async: Non-blocking speech

### Alert Messages

| Condition | Voice Alert |
|-----------|-------------|
| Overspeed | "Over speed. Slow down to [limit] kilometers per hour" |
| Road Hazard | "[Hazard type] ahead. Slow down" |
| Stop Sign | "Stop sign ahead" |
| Critical Collision | "Stop! [Object] [direction] ahead" |
| Warning Collision | "Caution! [Object] [direction] at [distance] meters" |

### Client-Side Voice (Web Speech API)
- Fallback if server voice fails
- Browser-based synthesis
- Supports: Chrome, Edge, Safari

---

## Known Limitations

### 1. YOLO Model Constraints
**Issue:** Standard COCO dataset doesn't include:
- Potholes
- Speed bumps/breakers
- Road damage
- Some traffic signs

**Current Solution:**
- Visual heuristics based on position/size
- Proxy detection (use similar objects)
- Distance-based estimation

**Future Enhancement:**
- Train custom YOLO model with road hazard dataset
- Fine-tune existing model with additional classes
- Add traditional CV methods (edge detection for potholes)

### 2. Traffic Light Color Detection
**Current:** Detects traffic light presence only  
**Missing:** Red/Yellow/Green state identification  
**Plan:** Add color histogram analysis on detected region

### 3. Speed Limit Sign OCR
**Current:** Detects sign presence only  
**Missing:** Number extraction from sign  
**Plan:** Integrate pytesseract or EasyOCR for text recognition

### 4. Distance Accuracy
**Current:** Heuristic-based estimation  
**Limitations:**
- Assumes flat road
- Assumes standard camera mounting
- No depth sensor data

**Improvement:**
- Calibrate based on known object sizes
- Use stereo cameras if available
- Integrate GPS/map data for context

---

## Real-World Usage Scenarios

### Scenario 1: Urban Driving (30-50 km/h)
**Settings:**
- Road Mode: ON
- Current Speed: 40 km/h
- Speed Limit: 50 km/h

**Expected Behavior:**
- Detects pedestrians, vehicles in path
- Alerts for stop signs within 15m
- Warns about potholes, bumps
- No overspeed alerts (within limit)
- Moderate threshold distances (1.0x-1.1x)

---

### Scenario 2: Highway Driving (80-100 km/h)
**Settings:**
- Road Mode: ON
- Current Speed: 90 km/h
- Speed Limit: 100 km/h

**Expected Behavior:**
- Focus on vehicles, large animals only
- Very early warnings (0.7x-0.85x multiplier)
- Critical: >6m, Warning: >10m, Caution: >17m
- Construction/barrier alerts at 20m+
- No overspeed (within limit)

---

### Scenario 3: School Zone (Overspeed)
**Settings:**
- Road Mode: ON
- Current Speed: 45 km/h
- Speed Limit: 30 km/h

**Expected Behavior:**
- **🚨 OVERSPEED! 45km/h in 30km/h zone (+15km/h)**
- Voice: "Over speed. Slow down to 30 kilometers per hour"
- Critical alert level (red)
- Extra sensitivity for pedestrians
- Stop sign alerts critical priority

---

### Scenario 4: Construction Zone
**Settings:**
- Road Mode: ON
- Current Speed: 35 km/h
- Speed Limit: 40 km/h

**Detection:**
- Cones, barriers detected as road hazards
- "⚠️ CONSTRUCTION, BARRIER ahead"
- Voice: "Construction ahead. Slow down"
- Warning level alerts
- Combined with vehicle detections

---

## Testing & Calibration

### Testing Checklist

1. **Overspeed Alerts:**
   - [ ] Set speed limit to 50 km/h
   - [ ] Gradually increase speed from 40 → 60
   - [ ] Verify alert triggers at 51 km/h
   - [ ] Check voice alert plays
   - [ ] Confirm red/critical UI color

2. **Road Hazards:**
   - [ ] Test with traffic cones
   - [ ] Verify 3-second deduplication
   - [ ] Check distance estimates
   - [ ] Validate voice alerts

3. **Traffic Signs:**
   - [ ] Position stop sign at various distances
   - [ ] Verify 15m alert threshold
   - [ ] Check traffic light detection

4. **Speed-Based Thresholds:**
   - [ ] Test at 0 km/h → 3.0m critical
   - [ ] Test at 30 km/h → 3.3m critical
   - [ ] Test at 60 km/h → 4.2m critical
   - [ ] Test at 100 km/h → 6.4m critical

### Calibration Tips

**Camera Mounting:**
- Height: 1.2-1.5m above ground
- Angle: 5-15° downward
- Position: Center of windshield/dashboard
- Avoid obstructions (mirror, wipers)

**Speed Limit Settings:**
- Urban: 30-50 km/h
- Rural: 60-80 km/h
- Highway: 100-120 km/h
- School zones: 20-30 km/h

**Fine-Tuning:**
- Adjust path ratio for narrow/wide roads
- Modify multipliers for aggressive/conservative alerts
- Set speed limit 10-20% below actual for safety margin

---

## Troubleshooting

### Issue: No Overspeed Alerts
**Causes:**
- Road mode disabled (overspeed only in road mode)
- Speed input not updated
- Speed limit set too high

**Solution:**
1. Enable Road Mode toggle
2. Set current speed in UI
3. Verify speed limit (default 50 km/h)
4. Check browser console for errors

---

### Issue: Too Many Hazard Alerts
**Causes:**
- Deduplication not working
- False positives from YOLO

**Solution:**
1. Check `recent_hazards` dict in session
2. Verify 3-second timeout
3. Adjust confidence threshold (increase from 0.35)
4. Filter by distance (increase 20m threshold)

---

### Issue: Missing Traffic Signs
**Causes:**
- Signs not in YOLO COCO classes
- Low confidence threshold
- Poor lighting/angle

**Solution:**
1. Verify sign type (stop sign, traffic light in COCO)
2. Lower confidence to 0.25-0.30
3. Improve camera position/angle
4. Consider custom model training

---

## Future Enhancements

### Planned Features:
1. **Traffic Light Color Detection**
   - Red: Stop alert
   - Yellow: Prepare to stop
   - Green: Clear to proceed

2. **Speed Limit Sign OCR**
   - Extract number from sign
   - Auto-update speed limit
   - Handle multiple speed zones

3. **Lane Departure Warning**
   - Track lane markings
   - Alert if drifting
   - Use path boundaries

4. **Forward Collision Warning (FCW)**
   - Time-to-collision calculation
   - Brake recommendation
   - Multi-stage warnings

5. **Pedestrian Crossing Detection**
   - Identify crosswalk markings
   - High priority for people in crosswalk
   - Distance to crossing line

6. **Night Mode**
   - Adjust for low light
   - Headlight glare filtering
   - Enhanced contrast

---

## Safety Disclaimer

⚠️ **IMPORTANT:** This system is a **driver assistance tool** only. It does NOT replace:
- Driver attention and responsibility
- Vehicle safety systems (ABS, airbags, etc.)
- Proper vehicle maintenance
- Traffic law compliance

**Always:**
- Keep eyes on the road
- Use system as secondary awareness tool
- Follow all traffic laws and speed limits
- Maintain safe following distances
- Be prepared to take manual control

**Never:**
- Rely solely on the system
- Use on incompatible roads (off-road, etc.)
- Ignore system warnings
- Disable safety features while driving
- Use with obstructed camera view

---

## Support & Feedback

For issues, suggestions, or contributions:
1. Check existing documentation (ROAD_DRIVING_GUIDE.md)
2. Review NEW_FEATURES.md for speed-based detection
3. Test with different scenarios
4. Report bugs with specific conditions

**Happy & Safe Driving! 🚗🛡️**
