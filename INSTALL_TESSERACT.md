# 📥 Installing Tesseract OCR for Speed Limit Auto-Detection

## Overview
The system now supports **automatic speed limit detection** from road signs using OCR (Optical Character Recognition). This requires installing Tesseract OCR engine.

---

## ✅ pytesseract Python Package (Already Installed)
The Python wrapper `pytesseract` has been installed. Now you need the actual Tesseract OCR engine.

---

## 📥 Installing Tesseract OCR Engine

### For Windows:

#### Option 1: Download Official Installer (Recommended)
1. **Download Tesseract installer:**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki
   - Download: `tesseract-ocr-w64-setup-5.x.x.exe` (latest version)
   - Or direct link: https://digi.bib.uni-mannheim.de/tesseract/

2. **Run the installer:**
   - Double-click the downloaded `.exe` file
   - **IMPORTANT:** During installation, note the installation path
   - Default path: `C:\Program Files\Tesseract-OCR`
   - Make sure to check "Add to PATH" if available

3. **Configure pytesseract (if not in PATH):**
   If Tesseract was NOT added to PATH, you need to tell pytesseract where it is.
   
   Add this line to `test_yolo_multi_mobile.py` after importing pytesseract:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

4. **Verify installation:**
   Open PowerShell and run:
   ```powershell
   tesseract --version
   ```
   
   You should see:
   ```
   tesseract 5.x.x
   leptonica-x.x.x
   ...
   ```

#### Option 2: Using Chocolatey (if you have it)
```powershell
choco install tesseract
```

---

### For Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install tesseract-ocr
```

### For macOS:
```bash
brew install tesseract
```

---

## 🧪 Testing OCR Installation

### Test 1: Command Line Test
```powershell
# Create a test image with text
tesseract --version
```

### Test 2: Python Test
Create a file `test_ocr.py`:
```python
import pytesseract
from PIL import Image
import numpy as np
import cv2

# Test if tesseract is accessible
try:
    print("Testing Tesseract OCR...")
    print(f"Tesseract version: {pytesseract.get_tesseract_version()}")
    print("✅ Tesseract OCR is working!")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure Tesseract is installed and added to PATH")
```

Run:
```powershell
python test_ocr.py
```

---

## 🚦 How Speed Limit Auto-Detection Works

### Detection Process:
1. **YOLO detects a speed limit sign** in the camera frame
2. **OCR extracts the region** where the sign is located
3. **Image preprocessing:**
   - Convert to grayscale
   - Increase contrast (histogram equalization)
   - Apply binary threshold
   - Resize for better OCR accuracy (3x scale)
4. **Tesseract OCR** reads the numbers from the sign
5. **Validation:** Only accepts values between 10-200 km/h
6. **Auto-update:** Speed limit is automatically updated in the UI

### Example Flow:
```
Camera Frame → YOLO detects "speed limit" sign
              ↓
Extract sign region (bounding box)
              ↓
Preprocess image (grayscale, threshold, resize)
              ↓
Tesseract OCR: "50" detected
              ↓
Validate: 10 ≤ 50 ≤ 200 ✓
              ↓
Update UI: Speed Limit = 50 km/h
              ↓
Enable overspeed alerts based on new limit
```

---

## 🎯 Features

### Automatic Speed Limit Detection:
- **No manual input needed** - system reads signs automatically
- **Real-time updates** - speed limit changes as you drive past signs
- **Visual confirmation** - UI shows updated limit with green "●AUTO" indicator
- **Overspeed alerts** - automatic alerts when exceeding detected limit

### UI Changes:
```
🚦 Speed Limit: [__50__] km/h ●AUTO
                ↑            ↑
           Read-only    Auto indicator
           (gray background)
```

### Console Logs:
When a speed limit sign is detected:
```
🚦 [OCR] Detected speed limit: 60 km/h
🚦 [AUTO] Device Mobile-1 speed limit updated: 50 → 60 km/h
```

---

## ⚙️ Configuration & Tuning

### OCR Settings (in code):
```python
# OCR configuration for digit extraction
custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
```

**Parameters:**
- `--oem 3`: Use LSTM neural network OCR engine
- `--psm 7`: Treat image as a single text line
- `tessedit_char_whitelist=0123456789`: Only recognize digits

### Preprocessing Steps:
You can adjust these in `extract_speed_limit_from_sign()`:

1. **Padding:** `padding = 5` (pixels around sign)
2. **Scale factor:** `scale_factor = 3` (resize for better OCR)
3. **Threshold method:** `THRESH_BINARY + THRESH_OTSU`

### Validation Range:
```python
if 10 <= speed_limit <= 200:  # Valid speed limits
    return speed_limit
```

Adjust the range if needed for different regions.

---

## 🔧 Troubleshooting

### Issue 1: "TesseractNotFoundError"
**Error:**
```
pytesseract.pytesseract.TesseractNotFoundError: tesseract is not installed
```

**Solution:**
1. Install Tesseract OCR (see installation steps above)
2. Add to PATH or configure pytesseract:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

---

### Issue 2: No Speed Limits Detected
**Causes:**
- YOLO doesn't detect "speed limit" signs (not in COCO dataset by default)
- Sign is too far or unclear
- Lighting conditions poor

**Solutions:**
1. **Check YOLO classes:**
   ```python
   # YOLO COCO dataset includes 'stop sign', 'traffic light'
   # but may not include 'speed limit' sign
   ```
   
2. **Train custom YOLO model** with speed limit signs:
   - Collect dataset of speed limit signs
   - Fine-tune YOLOv8 model
   - Replace model in code

3. **Use proxy detection:**
   - Detect all circular/octagonal signs
   - Apply OCR to all detected signs
   - Filter results based on number patterns

---

### Issue 3: Wrong Numbers Detected
**Causes:**
- Poor image quality
- Glare/reflections on sign
- Sign at extreme angle

**Solutions:**
1. **Improve preprocessing:**
   ```python
   # Add denoising
   gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
   
   # Add sharpening
   kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
   gray = cv2.filter2D(gray, -1, kernel)
   ```

2. **Increase scale factor:**
   ```python
   scale_factor = 5  # Instead of 3
   ```

3. **Add confidence scoring:**
   ```python
   # Use image_to_data instead of image_to_string
   data = pytesseract.image_to_data(binary, config=custom_config, output_type=pytesseract.Output.DICT)
   # Filter by confidence
   ```

---

### Issue 4: Speed Limit Not Updating in UI
**Causes:**
- JavaScript not receiving updates
- Alert polling not running

**Solutions:**
1. **Check browser console:**
   ```javascript
   // Should see:
   🚦 [AUTO] Speed limit updated to: 60 km/h
   ```

2. **Verify alert endpoint:**
   ```python
   # In update_alert(), speed_limit should be included
   'speed_limit': self.get_speed_limit()
   ```

3. **Check polling interval:**
   ```javascript
   // Should be running every 500ms
   alertCheckInterval = setInterval(checkAlerts, 500);
   ```

---

## 🧪 Testing Speed Limit Detection

### Test Setup:
1. **Print a test speed limit sign:**
   - Search online for "speed limit 50 sign" image
   - Print on white paper (A4 size)
   - Ensure numbers are clear and bold

2. **Camera positioning:**
   - Mount camera to capture sign clearly
   - Distance: 1-3 meters
   - Angle: Front-facing (not tilted)
   - Lighting: Good, no glare

3. **Run system:**
   ```powershell
   python test_yolo_multi_mobile.py
   ```

4. **Point camera at sign:**
   - YOLO should detect it as a sign (if trained)
   - OCR will extract the number
   - UI will update automatically

5. **Expected console output:**
   ```
   🚦 [OCR] Detected speed limit: 50 km/h
   🚦 [AUTO] Device Mobile-1 speed limit updated: 40 → 50 km/h
   ```

---

## 📊 Performance Considerations

### OCR Processing Time:
- **Per frame:** ~50-200ms (depending on image size and preprocessing)
- **Only triggered:** When YOLO detects a speed limit sign
- **Not continuous:** Only processes sign regions, not entire frame

### Optimization Tips:
1. **Skip frames:** Only run OCR every 5th detection
2. **Cache results:** Remember last detected limit for 10 seconds
3. **Limit frequency:** Maximum 1 OCR per second
4. **Reduce resolution:** Downscale large images before OCR

Example optimization:
```python
# Add to DeviceSession
self.last_ocr_time = 0
self.ocr_cooldown = 2.0  # seconds

# In generate_alert()
if time.time() - session.last_ocr_time > session.ocr_cooldown:
    speed_limit = self.extract_speed_limit_from_sign(frame, det)
    session.last_ocr_time = time.time()
```

---

## 🌍 Regional Considerations

### Speed Limit Formats by Region:

**USA/Canada:**
- Signs show mph (miles per hour)
- Need to convert: `km/h = mph × 1.60934`

**Europe/Asia:**
- Signs show km/h (default in our system)

**UK:**
- Signs show mph
- Need conversion if used in km/h system

### Conversion Code:
```python
def extract_speed_limit_from_sign(self, frame, detection, unit='kmh'):
    # ... existing code ...
    
    if unit == 'mph':
        speed_limit_kmh = int(speed_limit * 1.60934)
        return speed_limit_kmh
    return speed_limit
```

---

## 🚀 Advanced Features (Future)

### 1. Multi-Language OCR:
```python
# Detect text in multiple languages
text = pytesseract.image_to_string(binary, lang='eng+fra+deu')
```

### 2. Sign Type Detection:
```python
# Identify different sign types
if circular_shape:
    sign_type = 'mandatory'
elif triangle_shape:
    sign_type = 'warning'
```

### 3. Speed Limit Zones:
```python
# Remember speed zones with GPS
speed_zones = {
    'residential': 30,
    'school_zone': 20,
    'highway': 100
}
```

### 4. Sign Confidence Scoring:
```python
# Only accept high-confidence detections
if confidence > 0.8:
    update_speed_limit(value)
```

---

## 📝 Summary

### Installation Checklist:
- [x] Install Python package: `pip install pytesseract` ✅
- [ ] Install Tesseract OCR engine (see instructions above)
- [ ] Verify installation: `tesseract --version`
- [ ] Test with system: Point camera at speed limit sign

### System Status:
- ✅ Code integrated for auto-detection
- ✅ UI updated to show read-only speed limit with AUTO indicator
- ✅ JavaScript updates limit automatically
- ⏳ Tesseract OCR engine needs to be installed
- ⏳ YOLO model may need training for speed limit signs (COCO doesn't include them)

### Ready to Use:
Once Tesseract is installed, the system will automatically:
1. Detect speed limit signs (if trained)
2. Extract numbers using OCR
3. Update speed limit in UI
4. Trigger overspeed alerts based on new limit

---

## 🎉 Final Notes

**Benefits of Auto-Detection:**
- ✅ No manual input needed while driving
- ✅ Real-time updates as you pass signs
- ✅ Reduces distraction (hands-free)
- ✅ More accurate than manual entry
- ✅ Works with any speed limit (10-200 km/h)

**Limitations:**
- ⚠️ YOLO's COCO dataset may not include speed limit signs
- ⚠️ Requires clear view of sign (no obstructions)
- ⚠️ Works best in good lighting conditions
- ⚠️ May need custom model training for best results

**Next Steps:**
1. Install Tesseract OCR
2. Test with printed speed limit signs
3. Consider training custom YOLO model for speed limits
4. Fine-tune OCR preprocessing for your region's signs

**Happy & Safe Driving! 🚗🚦**
