#!/usr/bin/env python3
"""
YOLO-Based Multi-Device Object Detection System
Supports multiple mobile devices simultaneously, each with their own camera feed and personalized alerts

Requirements:
- pip install opencv-python numpy ultralytics pyttsx3 flask

Features:
- Multiple mobile devices can connect simultaneously
- Each device uploads their camera feed via WebRTC or image upload
- Each device receives personalized detection results and alerts
- Session-based tracking for each connected device
- Individual alert streams per device
"""

import cv2
import numpy as np
import os
import uuid
from datetime import datetime
from ultralytics import YOLO
import pyttsx3
import threading
import queue
import time
from flask import Flask, Response, render_template_string, jsonify, request, make_response
import socket
import base64
from io import BytesIO
from PIL import Image
import re

# Try to import pytesseract for OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    print("✅ Tesseract OCR available for speed limit detection")
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️ pytesseract not installed. Speed limit auto-detection disabled.")
    print("   Install with: pip install pytesseract")
    print("   Also install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")

# Configuration
WINDOW_NAME = "YOLO Multi-Device Server"
MOBILE_STREAM_PORT = 5000  # Port for mobile streaming

# ============================================================================
# DETECTION MODE: Choose based on your environment
# ============================================================================
# Set to True when driving on roads, False for indoor testing
ROAD_MODE = False  # Change to True when using in your car

# Alert thresholds based on object size in frame (percentage)
if ROAD_MODE:
    # Road driving: larger distances, faster speeds
    CRITICAL_SIZE = 0.15    # 15% of frame - immediate danger (3-5m ahead)
    WARNING_SIZE = 0.08     # 8% of frame - approaching fast (8-10m ahead)
    CAUTION_SIZE = 0.03     # 3% of frame - monitor closely (15-20m ahead)
else:
    # Indoor/testing: shorter distances, slower movement
    CRITICAL_SIZE = 0.20    # 20% of frame - very close
    WARNING_SIZE = 0.10     # 10% of frame - close
    CAUTION_SIZE = 0.04     # 4% of frame - moderate distance

# Driving path detection zone (center portion of frame width)
if ROAD_MODE:
    # Road: Narrower focus on actual lane (adjust based on your camera FOV)
    # If camera is wide-angle (>90°), use 0.35-0.40
    # If camera is normal (60-90°), use 0.45-0.50
    DRIVING_PATH_CENTER_RATIO = 0.45  # Center 45% = single lane focus
else:
    # Indoor: Wider for room navigation
    DRIVING_PATH_CENTER_RATIO = 0.40

# Priority objects that need immediate attention
if ROAD_MODE:
    # Road-specific hazards
    HIGH_PRIORITY_OBJECTS = {
        'person', 'child',           # Pedestrians (highest priority)
        'bicycle', 'motorcycle',      # Two-wheelers
        'car', 'truck', 'bus',       # Vehicles
        'dog', 'cat', 'bird',        # Animals
        'traffic light', 'stop sign'  # Road signs (if visible)
    }
    # Road infrastructure alerts
    ROAD_HAZARDS = {
        'pothole', 'speed bump', 'speed breaker', 'road damage',
        'construction', 'barrier', 'cone'
    }
    # Traffic control
    TRAFFIC_SIGNS = {
        'stop sign', 'traffic light', 'yield sign', 'speed limit',
        'no entry', 'one way', 'parking sign'
    }
    FURNITURE_OBJECTS = set()  # Ignore furniture on roads
else:
    # Indoor navigation
    HIGH_PRIORITY_OBJECTS = {'person', 'dog', 'cat', 'car', 'truck', 'bicycle', 'motorcycle', 'bus'}
    ROAD_HAZARDS = set()
    TRAFFIC_SIGNS = set()
    FURNITURE_OBJECTS = {'chair', 'couch', 'bed', 'dining table', 'desk', 'toilet', 'sink'}

# Colors (BGR format)
COLOR_CRITICAL = (0, 0, 255)      # Red
COLOR_WARNING = (0, 165, 255)     # Orange
COLOR_CAUTION = (0, 255, 255)     # Yellow
COLOR_SAFE = (0, 255, 0)          # Green
COLOR_TEXT = (255, 255, 255)      # White
COLOR_PERSON = (255, 0, 255)      # Magenta for people
COLOR_FURNITURE = (255, 255, 0)   # Cyan for furniture

# Flask app for mobile streaming
app = Flask(__name__)

# Multi-device session management
class DeviceSession:
    """Manages individual device session with its own feed and alerts"""
    def __init__(self, device_id, device_name="Mobile"):
        self.device_id = device_id
        self.device_name = device_name
        self.latest_frame = None
        self.processed_frame = None
        self.frame_lock = threading.Lock()
        self.last_update = time.time()
        self.current_alert = {
            'has_alert': False,
            'message': '',
            'voice_message': '',
            'level': 'SAFE',
            'timestamp': 0,
            'device_id': device_id
        }
        self.alert_lock = threading.Lock()
        self.frame_count = 0
        
        # User-configurable settings
        self.road_mode = False
        self.current_speed = 0.0  # km/h
        self.speed_lock = threading.Lock()
        self.last_speed_update = time.time()
        
        # Speed limit tracking
        self.speed_limit = 50  # Default 50 km/h
        self.speed_limit_lock = threading.Lock()
        
        # Road hazard tracking
        self.recent_hazards = {}  # Track recently seen hazards to avoid spam
        self.hazard_lock = threading.Lock()
        
    def update_frame(self, frame):
        """Update the latest frame for this device"""
        with self.frame_lock:
            self.latest_frame = frame.copy()
            self.last_update = time.time()
            self.frame_count += 1
            
    def get_frame(self):
        """Get the latest frame for this device"""
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
        return None
        
    def update_alert(self, alert_msg, level, voice_msg, has_alert):
        """Update alert for this device"""
        with self.alert_lock:
            self.current_alert = {
                'has_alert': has_alert,
                'message': alert_msg,
                'voice_message': voice_msg,
                'level': level,
                'timestamp': time.time(),
                'device_id': self.device_id,
                'speed_limit': self.get_speed_limit()  # Include current speed limit
            }
    
    def update_speed(self, speed_kmh):
        """Update current vehicle speed"""
        with self.speed_lock:
            self.current_speed = speed_kmh
            self.last_speed_update = time.time()
    
    def get_speed(self):
        """Get current vehicle speed"""
        with self.speed_lock:
            return self.current_speed
    
    def set_road_mode(self, enabled):
        """Set road mode on/off"""
        self.road_mode = enabled
    
    def set_speed_limit(self, limit_kmh):
        """Set speed limit for overspeed detection"""
        with self.speed_limit_lock:
            self.speed_limit = limit_kmh
    
    def get_speed_limit(self):
        """Get current speed limit"""
        with self.speed_limit_lock:
            return self.speed_limit
    
    def check_overspeed(self):
        """Check if current speed exceeds limit"""
        speed = self.get_speed()
        limit = self.get_speed_limit()
        if speed > limit and speed > 0:
            return True, speed - limit
        return False, 0
    
    def add_recent_hazard(self, hazard_type, position):
        """Track recently seen hazards to avoid alert spam"""
        with self.hazard_lock:
            current_time = time.time()
            # Clean old hazards (older than 3 seconds)
            self.recent_hazards = {
                k: v for k, v in self.recent_hazards.items() 
                if current_time - v['time'] < 3.0
            }
            # Add new hazard
            key = f"{hazard_type}_{position[0]}_{position[1]}"
            if key not in self.recent_hazards:
                self.recent_hazards[key] = {
                    'type': hazard_type,
                    'position': position,
                    'time': current_time
                }
                return True  # New hazard
            return False  # Already alerted recently
            
    def get_alert(self):
        """Get current alert for this device"""
        with self.alert_lock:
            return self.current_alert.copy()
            
    def is_active(self, timeout=30):
        """Check if device is still active (received frame within timeout)"""
        return (time.time() - self.last_update) < timeout


# Global device sessions storage
device_sessions = {}
sessions_lock = threading.Lock()


def get_local_ip():
    """Get local IP address for mobile access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


class VoiceAssistant:
    """Voice assistance for continuous driver instructions"""
    def __init__(self):
        self.engine = None
        self.enabled = False
        self.speech_queue = queue.Queue()
        self.speech_thread = None
        self.running = False

        try:
            print("Initializing voice assistant...")
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 190)
            self.engine.setProperty('volume', 1.0)
            
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    print(f"Using voice: {voice.name}")
                    break
            
            self.enabled = True
            self.running = True
            self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
            self.speech_thread.start()
            print("✅ Voice assistant ready!")
            
        except Exception as e:
            print(f"⚠️ Voice assistant unavailable: {e}")
            self.enabled = False

    def _speech_worker(self):
        """Background thread to handle speech queue"""
        while self.running:
            try:
                if not self.speech_queue.empty():
                    text = self.speech_queue.get(timeout=0.1)
                    if self.engine and self.enabled:
                        try:
                            self.engine.say(text)
                            self.engine.runAndWait()
                        except Exception as e:
                            print(f"Speech error: {e}")
                else:
                    time.sleep(0.05)
            except queue.Empty:
                time.sleep(0.05)

    def speak_async(self, text):
        """Add text to speech queue"""
        if self.enabled and text:
            print(f"🔊 Speaking: {text}")
            self.speech_queue.put(text)

    def generate_voice_instruction(self, alert_level, obj_class, direction, distance):
        """Generate natural voice instruction"""
        if obj_class == 'person':
            obj_phrase = "Person"
            action = "Stop now!"
        elif obj_class in HIGH_PRIORITY_OBJECTS:
            obj_phrase = obj_class
            action = "Stop!" if alert_level == "CRITICAL" else "Slow down!"
        else:
            obj_phrase = obj_class
            action = "Stop!" if alert_level == "CRITICAL" else "Slow down!"
        
        direction_phrase = direction.lower()
        return f"{action} {obj_phrase} {direction_phrase} (Alert: {alert_level})"

    def stop(self):
        """Stop the voice assistant"""
        self.running = False
        if self.speech_thread:
            self.speech_thread.join(timeout=1.0)
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass


class YOLOObjectDetector:
    def __init__(self):
        print("Loading YOLO model (this may take a moment)...")
        self.model = YOLO('yolov8n.pt')
        self.model.fuse()
        print("✅ YOLO model loaded!")
        
        # Confidence threshold based on mode
        if ROAD_MODE:
            # Road: Higher confidence to reduce false positives at speed
            self.conf_threshold = 0.35  # 35% - more strict
        else:
            # Indoor: Lower confidence for better detection
            self.conf_threshold = 0.25  # 25% - more sensitive

    def get_dynamic_thresholds(self, speed_kmh, road_mode):
        """Calculate dynamic alert thresholds based on speed and mode"""
        if not road_mode:
            # Indoor mode: fixed thresholds
            return {
                'critical': 0.20,
                'warning': 0.10,
                'caution': 0.04,
                'conf': 0.25,
                'path_ratio': 0.40
            }
        
        # Road mode: speed-based thresholds
        # Base thresholds for 50 km/h
        base_critical = 0.15
        base_warning = 0.08
        base_caution = 0.03
        
        # Speed adjustment factor
        # At higher speeds, we need earlier warnings (lower thresholds = detect at greater distance)
        # Formula: threshold decreases as speed increases
        if speed_kmh < 30:
            # City/slow: 0-30 km/h
            speed_factor = 1.1  # Slightly larger objects (closer)
        elif speed_kmh < 60:
            # Urban: 30-60 km/h
            speed_factor = 1.0  # Base thresholds
        elif speed_kmh < 90:
            # Highway: 60-90 km/h
            speed_factor = 0.85  # Smaller objects (farther)
        else:
            # Fast highway: 90+ km/h
            speed_factor = 0.70  # Much smaller objects (much farther)
        
        return {
            'critical': base_critical * speed_factor,
            'warning': base_warning * speed_factor,
            'caution': base_caution * speed_factor,
            'conf': 0.35 if road_mode else 0.25,
            'path_ratio': 0.45 if road_mode else 0.40
        }

    def detect_objects(self, frame):
        """Detect objects using YOLO"""
        height, width = frame.shape[:2]
        frame_area = height * width
        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        detections = []

        if len(results) > 0:
            result = results[0]
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x, y, w, h = int(x1), int(y1), int(x2-x1), int(y2-y1)
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls]
                    obj_area = w * h
                    size_percent = (obj_area / frame_area) * 100
                    center_x = x + w // 2
                    center_y = y + h // 2

                    detections.append({
                        'class': class_name,
                        'confidence': conf,
                        'box': (x, y, w, h),
                        'size': size_percent,
                        'center_x': center_x,
                        'center_y': center_y
                    })

        return detections

    def calculate_distance(self, size_percent, thresholds):
        """Estimate distance based on object size using dynamic thresholds"""
        critical_threshold = thresholds['critical'] * 100
        warning_threshold = thresholds['warning'] * 100
        caution_threshold = thresholds['caution'] * 100
        
        if size_percent >= critical_threshold:
            return 0.5, "CRITICAL", COLOR_CRITICAL
        elif size_percent >= warning_threshold:
            return 1.5, "WARNING", COLOR_WARNING
        elif size_percent >= caution_threshold:
            return 3.0, "CAUTION", COLOR_CAUTION
        else:
            return 5.0, "MONITOR", COLOR_SAFE

    def get_direction(self, center_x, frame_width):
        """Determine if object is left, center, or right"""
        left_third = frame_width / 3
        right_third = 2 * frame_width / 3

        if center_x < left_third:
            return "LEFT"
        elif center_x > right_third:
            return "RIGHT"
        else:
            return "AHEAD"

    def is_in_driving_path(self, center_x, frame_width, path_ratio):
        """Check if object is in the driving path (center zone)"""
        frame_center = frame_width / 2
        path_half_width = (frame_width * path_ratio) / 2
        path_left = frame_center - path_half_width
        path_right = frame_center + path_half_width
        return path_left <= center_x <= path_right

    def generate_alert(self, detections, frame_shape, speed_kmh, road_mode, frame=None):
        """Generate alert message based on detections IN THE DRIVING PATH ONLY"""
        thresholds = self.get_dynamic_thresholds(speed_kmh, road_mode)
        
        if not detections:
            return "All clear", "SAFE", COLOR_SAFE, [], thresholds, {}

        height, width = frame_shape[:2]
        path_detections = []
        road_hazards_detected = {}
        traffic_signs_detected = {}
        detected_speed_limit = None
        
        for det in detections:
            obj_class = det['class']
            
            # Categorize detections
            if obj_class in ROAD_HAZARDS:
                road_hazards_detected[obj_class] = det
            elif obj_class in TRAFFIC_SIGNS:
                traffic_signs_detected[obj_class] = det
                
                # Try to extract speed limit from speed limit signs
                if obj_class == 'speed limit' and frame is not None:
                    speed_limit = self.extract_speed_limit_from_sign(frame, det)
                    if speed_limit:
                        detected_speed_limit = speed_limit
                        print(f"🚦 [OCR] Detected speed limit: {speed_limit} km/h")
            
            # Check if in driving path for collision detection
            if self.is_in_driving_path(det['center_x'], width, thresholds['path_ratio']):
                path_detections.append(det)

        # Special handling for road hazards (even if not directly in path)
        hazard_alerts = []
        for hazard_type, det in road_hazards_detected.items():
            distance = self.estimate_hazard_distance(det, height)
            if distance < 20:  # Within 20 meters
                hazard_alerts.append({
                    'type': hazard_type,
                    'distance': distance,
                    'position': (det['center_x'], det['center_y'])
                })
        
        # Traffic sign alerts
        sign_alerts = []
        for sign_type, det in traffic_signs_detected.items():
            if sign_type == 'traffic light':
                # TODO: Add color detection (red/yellow/green) if needed
                sign_alerts.append({
                    'type': 'traffic_light',
                    'message': 'Traffic light ahead'
                })
            elif sign_type == 'stop sign':
                distance = self.estimate_hazard_distance(det, height)
                if distance < 15:
                    sign_alerts.append({
                        'type': 'stop_sign',
                        'message': f'STOP sign ahead - {distance:.0f}m',
                        'distance': distance
                    })

        if not path_detections and not hazard_alerts and not sign_alerts:
            return "Path clear", "SAFE", COLOR_SAFE, [], thresholds, {
                'hazards': hazard_alerts,
                'signs': sign_alerts
            }

        priority_objs = []
        max_priority = 0

        for det in path_detections:
            obj_class = det['class']
            size = det['size']
            distance, level, color = self.calculate_distance(size, thresholds)
            direction = self.get_direction(det['center_x'], width)

            priority = 0
            if level == "CRITICAL":
                priority = 3
            elif level == "WARNING":
                priority = 2
            elif level == "CAUTION":
                priority = 1

            # Determine which priority list to use based on road_mode
            if road_mode:
                priority_set = HIGH_PRIORITY_OBJECTS if ROAD_MODE else set()
            else:
                priority_set = HIGH_PRIORITY_OBJECTS
                
            if obj_class in priority_set:
                priority += 1

            if priority >= max_priority:
                max_priority = priority
                priority_objs.append({
                    'class': obj_class,
                    'distance': distance,
                    'direction': direction,
                    'level': level,
                    'color': color,
                    'priority': priority
                })

        # Determine final alert message
        alert_parts = []
        final_level = "SAFE"
        final_color = COLOR_SAFE
        
        # Priority 1: Critical collision alerts
        if priority_objs:
            priority_objs.sort(key=lambda x: x['priority'], reverse=True)
            top_obj = priority_objs[0]
            
            obj_name = top_obj['class'].upper().replace('_', ' ')
            direction = top_obj['direction']
            distance = top_obj['distance']
            level = top_obj['level']
            final_level = level
            final_color = top_obj['color']

            if level == "CRITICAL":
                alert_parts.append(f"🚨 STOP! {obj_name} {direction} - {distance}m")
            elif level == "WARNING":
                alert_parts.append(f"⚠️ SLOW DOWN! {obj_name} {direction} - {distance}m")
            elif level == "CAUTION":
                alert_parts.append(f"⚡ CAUTION! {obj_name} {direction} - {distance}m")
            else:
                alert_parts.append(f"✓ Monitor: {obj_name} {direction} - {distance}m")

            if len(path_detections) > 1:
                alert_parts.append(f"{len(path_detections)} in path")
        
        # Priority 2: Road hazard warnings
        if hazard_alerts:
            hazard = hazard_alerts[0]  # Most critical
            hazard_msg = f"⚠️ {hazard['type'].upper().replace('_', ' ')} - {hazard['distance']:.0f}m"
            if not priority_objs or final_level not in ["CRITICAL", "WARNING"]:
                alert_parts.insert(0, hazard_msg)
                final_level = "WARNING"
                final_color = COLOR_WARNING
            else:
                alert_parts.append(hazard_msg)
        
        # Priority 3: Traffic sign alerts
        if sign_alerts:
            sign = sign_alerts[0]
            if not priority_objs or final_level == "SAFE":
                alert_parts.insert(0, sign['message'])
                final_level = "CAUTION"
                final_color = COLOR_CAUTION
            else:
                alert_parts.append(sign['message'])
        
        # Add speed indicator if in road mode
        if road_mode and speed_kmh > 0:
            alert_parts.append(f"{speed_kmh:.0f}km/h")
        
        msg = " | ".join(alert_parts) if alert_parts else "All clear"

        return (msg, final_level, final_color, priority_objs, thresholds, {
            'hazards': hazard_alerts,
            'signs': sign_alerts,
            'detected_speed_limit': detected_speed_limit
        })
    
    def estimate_hazard_distance(self, detection, frame_height):
        """Estimate distance to road hazard based on vertical position"""
        # Simple heuristic: objects lower in frame are closer
        # Assumes camera is mounted looking ahead
        center_y = detection['center_y']
        relative_position = center_y / frame_height
        
        # Bottom of frame (1.0) = ~2m, Middle (0.5) = ~10m, Top (0.0) = ~50m
        if relative_position > 0.8:
            return 2.0 + (1.0 - relative_position) * 10
        elif relative_position > 0.5:
            return 5.0 + (0.8 - relative_position) * 20
        else:
            return 15.0 + (0.5 - relative_position) * 70
    
    def extract_speed_limit_from_sign(self, frame, detection):
        """Extract speed limit number from detected speed limit sign using OCR"""
        if not TESSERACT_AVAILABLE:
            return None
        
        try:
            # Extract the region of interest (speed limit sign)
            x1, y1 = detection['x1'], detection['y1']
            x2, y2 = detection['x2'], detection['y2']
            
            # Add some padding
            padding = 5
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(frame.shape[1], x2 + padding)
            y2 = min(frame.shape[0], y2 + padding)
            
            sign_roi = frame[y1:y2, x1:x2]
            
            if sign_roi.size == 0:
                return None
            
            # Preprocess image for better OCR
            # Convert to grayscale
            gray = cv2.cvtColor(sign_roi, cv2.COLOR_BGR2GRAY)
            
            # Increase contrast
            gray = cv2.equalizeHist(gray)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Resize for better OCR (tesseract works better with larger images)
            scale_factor = 3
            binary = cv2.resize(binary, None, fx=scale_factor, fy=scale_factor, 
                               interpolation=cv2.INTER_CUBIC)
            
            # OCR configuration - digits only
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(binary, config=custom_config)
            
            # Extract numbers using regex
            numbers = re.findall(r'\d+', text)
            
            if numbers:
                speed_limit = int(numbers[0])
                # Validate reasonable speed limits (10-200 km/h)
                if 10 <= speed_limit <= 200:
                    return speed_limit
            
            return None
            
        except Exception as e:
            print(f"⚠️ [OCR] Error extracting speed limit: {e}")
            return None


def draw_detections(frame, detections, alert_msg, alert_level, color, device_name, detector, thresholds):
    """Draw bounding boxes and labels on frame with device identifier"""
    height, width = frame.shape[:2]

    # Draw driving path zone using dynamic path ratio
    frame_center = width / 2
    path_half_width = (width * thresholds['path_ratio']) / 2
    path_left = int(frame_center - path_half_width)
    path_right = int(frame_center + path_half_width)
    
    cv2.line(frame, (path_left, 0), (path_left, height), COLOR_SAFE, 2)
    cv2.line(frame, (path_right, 0), (path_right, height), COLOR_SAFE, 2)
    
    path_label = f"{device_name} - DRIVING PATH"
    label_size = cv2.getTextSize(path_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    label_x = int(frame_center - label_size[0] / 2)
    cv2.putText(frame, path_label, (label_x, height - 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_SAFE, 2)

    in_path_detections = [det for det in detections if detector.is_in_driving_path(det['center_x'], width, thresholds['path_ratio'])]

    top_index = -1
    max_priority = -1
    for i, det in enumerate(detections):
        if det not in in_path_detections:
            continue
            
        size = det['size']
        obj_class = det['class']
        _, level, _ = detector.calculate_distance(size, thresholds)
        priority = 0
        if level == "CRITICAL":
            priority = 3
        elif level == "WARNING":
            priority = 2
        elif level == "CAUTION":
            priority = 1
        if obj_class in HIGH_PRIORITY_OBJECTS:
            priority += 1
        if priority >= max_priority:
            max_priority = priority
            top_index = i

    for i, det in enumerate(detections):
        x, y, w, h = det['box']
        class_name = det['class']
        confidence = det['confidence']
        size = det['size']
        in_path = det in in_path_detections

        distance, level, box_color = detector.calculate_distance(size, thresholds)

        if not in_path:
            box_color = (100, 100, 100)
            thickness = 1
            alpha = 0.05
        else:
            if i == top_index:
                box_color = color
                thickness = 3
            else:
                if class_name == 'person':
                    box_color = COLOR_PERSON
                elif class_name in FURNITURE_OBJECTS:
                    box_color = COLOR_FURNITURE
                thickness = 2
            alpha = 0.15

        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), box_color, -1)
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)
        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, thickness)

        label = f"{class_name} {distance}m ({confidence:.2f})"
        if not in_path:
            label = f"{class_name} (side)"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        cv2.rectangle(frame, (x, y - label_size[1] - 8),
                      (x + label_size[0] + 8, y), box_color, -1)
        cv2.putText(frame, label, (x + 4, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)

    # Alert banner
    banner_height = 120
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, banner_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, alert_msg, (15, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

    in_path_count = len(in_path_detections)
    status = f"Device: {device_name} | Total: {len(detections)} | In-Path: {in_path_count} | Level: {alert_level}"
    cv2.putText(frame, status, (15, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)

    return frame


# Initialize detector and voice assistant globally
detector = None
voice_assistant = None


def process_device_frame(device_id):
    """Process frame for a specific device"""
    global detector, voice_assistant
    
    with sessions_lock:
        if device_id not in device_sessions:
            return None
        session = device_sessions[device_id]
    
    frame = session.get_frame()
    if frame is None:
        return None
    
    # Get current speed and road mode for this device
    speed_kmh = session.get_speed()
    road_mode = session.road_mode
        
    # Detect objects
    detections = detector.detect_objects(frame)
    
    # Generate alert with speed-based dynamic thresholds (pass frame for OCR)
    alert_msg, alert_level, color, priority_objs, thresholds, extra_data = detector.generate_alert(
        detections, frame.shape, speed_kmh, road_mode, frame
    )
    
    # Update speed limit if detected from road sign
    if 'detected_speed_limit' in extra_data and extra_data['detected_speed_limit']:
        new_limit = extra_data['detected_speed_limit']
        old_limit = session.get_speed_limit()
        if new_limit != old_limit:
            session.set_speed_limit(new_limit)
            print(f"🚦 [AUTO] Device {session.device_name} speed limit updated: {old_limit} → {new_limit} km/h")
    
    # Check for overspeed
    is_overspeed, overage = session.check_overspeed()
    if is_overspeed:
        overspeed_msg = f"🚨 OVERSPEED! {speed_kmh:.0f}km/h in {session.get_speed_limit()}km/h zone (+{overage:.0f}km/h)"
        if alert_level == "CRITICAL":
            alert_msg = f"{overspeed_msg} | {alert_msg}"
        else:
            alert_msg = overspeed_msg
            alert_level = "CRITICAL"
            color = COLOR_CRITICAL
    
    # Process road hazards (prevent spam with deduplication)
    hazard_messages = []
    if 'hazards' in extra_data:
        for hazard in extra_data['hazards']:
            hazard_key = f"{hazard['type']}_{int(hazard['position'][0]/50)}"
            if session.add_recent_hazard(hazard_key):
                hazard_messages.append(f"{hazard['type'].replace('_', ' ').upper()}")
    
    if hazard_messages and alert_level not in ["CRITICAL"]:
        alert_msg = f"⚠️ {', '.join(hazard_messages)} ahead | {alert_msg}"
    
    # Voice alert (only for WARNING and CRITICAL)
    voice_msg = ""
    has_alert = False
    if alert_level in ["CRITICAL", "WARNING"]:
        if is_overspeed:
            voice_msg = f"Over speed. Slow down to {session.get_speed_limit()} kilometers per hour"
        elif hazard_messages:
            voice_msg = f"{hazard_messages[0]} ahead. Slow down"
        elif priority_objs:
            top_obj = priority_objs[0]
            voice_msg = voice_assistant.generate_voice_instruction(
                alert_level, top_obj['class'], top_obj['direction'], top_obj['distance']
            )
        
        if voice_msg and voice_assistant.enabled:
            voice_assistant.speak_async(voice_msg)
        has_alert = True
    
    # Update alert for this device
    session.update_alert(alert_msg, alert_level, voice_msg, has_alert)
    
    # Draw detections
    processed_frame = draw_detections(frame, detections, alert_msg, alert_level, color, 
                                     session.device_name, detector, thresholds)
    
    return processed_frame


# Flask routes
@app.route('/')
def index():
    """Main page for mobile devices"""
    client_ip = request.remote_addr
    print(f"📱 [INDEX] Page requested from {client_ip}")
    
    # Add timestamp to help with cache busting
    import time
    cache_buster = int(time.time())
    print(f"📱 [INDEX] Cache buster: {cache_buster}")
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Device YOLO Detection</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta charset="UTF-8">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <style>
            body {
                margin: 0;
                padding: 10px;
                background: #000;
                color: #fff;
                font-family: Arial, sans-serif;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            h1 { text-align: center; color: #0f0; margin: 10px 0; }
            .mode-indicator {
                background: """ + ("#ff8800" if ROAD_MODE else "#0088ff") + """;
                color: #000;
                font-weight: bold;
                text-align: center;
                padding: 8px;
                border-radius: 5px;
                margin: 10px 0;
                font-size: 14px;
            }
            .status {
                background: #222;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }
            #deviceInfo { color: #0ff; margin: 5px 0; }
            #connectionStatus { color: #ff0; margin: 5px 0; }
            video {
                width: 100%;
                max-width: 640px;
                height: auto;
                border: 2px solid #0f0;
                border-radius: 5px;
                display: block;
                margin: 10px auto;
            }
            #resultVideo {
                width: 100%;
                border: 2px solid #00f;
                border-radius: 5px;
            }
            .alert-box {
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                min-height: 50px;
            }
            .alert-CRITICAL { background: #f00; color: #fff; }
            .alert-WARNING { background: #ff8800; color: #000; }
            .alert-CAUTION { background: #ff0; color: #000; }
            .alert-SAFE { background: #0f0; color: #000; }
            button {
                width: 100%;
                padding: 15px;
                margin: 10px 0;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            #startBtn {
                background: #0f0;
                color: #000;
            }
            #stopBtn {
                background: #f00;
                color: #fff;
            }
            #voiceBtn {
                background: #00f;
                color: #fff;
            }
            .controls {
                margin: 20px 0;
            }
            .settings-panel {
                background: #1a1a1a;
                border: 2px solid #0f0;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }
            .settings-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin: 10px 0;
                padding: 10px;
                background: #2a2a2a;
                border-radius: 5px;
            }
            .settings-label {
                font-weight: bold;
                color: #0ff;
                font-size: 16px;
            }
            .toggle-switch {
                position: relative;
                display: inline-block;
                width: 60px;
                height: 34px;
            }
            .toggle-switch input {
                opacity: 0;
                width: 0;
                height: 0;
            }
            .slider {
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: #666;
                transition: .4s;
                border-radius: 34px;
            }
            .slider:before {
                position: absolute;
                content: "";
                height: 26px;
                width: 26px;
                left: 4px;
                bottom: 4px;
                background-color: white;
                transition: .4s;
                border-radius: 50%;
            }
            input:checked + .slider {
                background-color: #0f0;
            }
            input:checked + .slider:before {
                transform: translateX(26px);
            }
            .speed-input {
                width: 100px;
                padding: 8px;
                font-size: 18px;
                border: 2px solid #0f0;
                border-radius: 5px;
                background: #000;
                color: #0f0;
                text-align: center;
            }
            .speed-container {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .speed-unit {
                color: #0f0;
                font-size: 16px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚗 Multi-Device Detection System</h1>
            
            <div class="mode-indicator">
                """ + ("🚗 ROAD MODE: Optimized for driving (higher thresholds, road objects)" if ROAD_MODE else "🏠 INDOOR MODE: Optimized for testing (lower thresholds, all objects)") + """
            </div>
            
            <div class="status">
                <div id="deviceInfo">Device ID: ⚠️ JavaScript not loaded (clear cache!)</div>
                <div id="connectionStatus">Status: ⚠️ JavaScript not running (clear cache!)</div>
            </div>
            
            <div class="settings-panel">
                <h3 style="color: #0f0; margin-top: 0;">⚙️ Detection Settings</h3>
                
                <div class="settings-row">
                    <span class="settings-label">🚗 Road Mode:</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="roadModeToggle" onchange="toggleRoadMode()">
                        <span class="slider"></span>
                    </label>
                </div>
                
                <div class="settings-row">
                    <span class="settings-label">⚡ Current Speed:</span>
                    <div class="speed-container">
                        <input type="number" id="speedInput" class="speed-input" 
                               min="0" max="200" value="0" step="1" 
                               readonly style="background: #222; border: 2px solid #0a0;" 
                               placeholder="GPS">
                        <span class="speed-unit">km/h <span style="font-size:10px; color:#0a0;">●GPS</span></span>
                    </div>
                </div>
                
                <div class="settings-row">
                    <span class="settings-label">🚦 Speed Limit:</span>
                    <div class="speed-container">
                        <input type="number" id="speedLimitInput" class="speed-input" 
                               min="10" max="200" value="50" step="10" 
                               readonly style="background: #222; border: 2px solid #0a0;" 
                               placeholder="Auto">
                        <span class="speed-unit">km/h <span style="font-size:10px; color:#0a0;">●AUTO</span></span>
                    </div>
                </div>
                
                <div style="font-size: 12px; color: #888; margin-top: 10px;">
                    <strong>Indoor Mode:</strong> Shorter distances, all objects<br>
                    <strong>Road Mode:</strong> Longer distances, road objects only<br>
                    <strong>Current Speed:</strong> Auto-calculated from GPS 📡<br>
                    <strong>Speed Limit:</strong> Auto-detected from road signs 🚦
                </div>
            </div>
            
            <div class="controls">
                <button id="startBtn" onclick="startCamera()">📷 Start Camera & Detection</button>
                <button id="stopBtn" onclick="stopCamera()" style="display:none;">⏹️ Stop</button>
                <button id="voiceBtn" onclick="toggleVoice()">🔊 Voice: OFF</button>
            </div>

            <div id="metrics" style="font-family: monospace; font-size: 12px; color: #0ff; margin: 6px 0;">
                uploads: 0 | processed: 0 | alerts: 0
            </div>
            
            <video id="localVideo" autoplay playsinline muted></video>
            
            <div id="alertBox" class="alert-box alert-SAFE">
                ✓ Waiting to start...
            </div>
            
            <img id="resultVideo" alt="Processed video will appear here" style="display:none;">
        </div>

        <script>
            // IMMEDIATE TEST: This should run first
            console.log('🚀 [INIT] Script starting...');
            console.log('🚀 [INIT] JavaScript IS RUNNING! Time:', new Date().toISOString());
            
            // Define function FIRST before using it
            function generateDeviceId() {
                console.log('🔑 [INIT] Generating new device ID...');
                const id = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                try {
                    localStorage.setItem('deviceId', id);
                    console.log('✅ [INIT] Device ID saved to localStorage:', id);
                } catch(e) {
                    console.warn('⚠️ [INIT] Could not save to localStorage:', e);
                }
                return id;
            }
            
            // NOW we can call it
            let deviceId;
            try {
                deviceId = localStorage.getItem('deviceId') || generateDeviceId();
                console.log('🆔 [INIT] Device ID:', deviceId);
            } catch(e) {
                console.error('❌ [INIT] Error getting device ID:', e);
                deviceId = generateDeviceId();
            }
            
            let localStream = null;
            let uploadRunning = false; // async loop flag (replaces setInterval)
            let alertCheckInterval = null;
            let voiceEnabled = false;
            let lastAlertTime = 0;
            let synth = window.speechSynthesis;
            let firstProcessedShown = false;
            let uploadCount = 0;
            let processedCount = 0;
            let alertCount = 0;
            let lastResultUrl = null;
            let videoReady = false;
            let roadMode = false;
            let currentSpeed = 0;
            let gpsWatchId = null;
            let lastGpsPosition = null;
            let lastGpsTime = null;

            function updateMetrics() {
                const m = document.getElementById('metrics');
                if (!m) return;
                m.textContent = `uploads: ${uploadCount} | processed: ${processedCount} | alerts: ${alertCount}`;
            }
            
            function startGpsTracking() {
                if (!navigator.geolocation) {
                    console.warn('⚠️ [GPS] Geolocation not supported on this device');
                    document.getElementById('connectionStatus').textContent = 'Status: GPS not available';
                    return;
                }
                
                console.log('📡 [GPS] Requesting GPS permission...');
                
                const gpsOptions = {
                    enableHighAccuracy: true,  // Use GPS, not wifi/cell tower
                    timeout: 10000,            // 10 second timeout
                    maximumAge: 0              // Don't use cached position
                };
                
                gpsWatchId = navigator.geolocation.watchPosition(
                    onGpsSuccess,
                    onGpsError,
                    gpsOptions
                );
                
                console.log('✅ [GPS] GPS tracking started');
            }
            
            function onGpsSuccess(position) {
                const currentTime = Date.now();
                const currentLat = position.coords.latitude;
                const currentLon = position.coords.longitude;
                
                // Calculate speed from GPS if available
                if (position.coords.speed !== null && position.coords.speed >= 0) {
                    // GPS provides speed in m/s, convert to km/h
                    const speedKmh = position.coords.speed * 3.6;
                    currentSpeed = Math.round(speedKmh);
                    
                    console.log('📡 [GPS] Speed from GPS:', currentSpeed, 'km/h');
                } else if (lastGpsPosition && lastGpsTime) {
                    // Calculate speed from position change
                    const timeDiff = (currentTime - lastGpsTime) / 1000; // seconds
                    
                    if (timeDiff > 0.5) { // Update every 0.5 seconds
                        const distance = calculateDistance(
                            lastGpsPosition.lat, lastGpsPosition.lon,
                            currentLat, currentLon
                        );
                        
                        // Convert distance (km) and time (s) to speed (km/h)
                        const speedKmh = (distance / timeDiff) * 3600;
                        currentSpeed = Math.round(speedKmh);
                        
                        console.log('📡 [GPS] Speed calculated:', currentSpeed, 'km/h');
                        
                        lastGpsPosition = { lat: currentLat, lon: currentLon };
                        lastGpsTime = currentTime;
                    }
                } else {
                    // First GPS reading
                    lastGpsPosition = { lat: currentLat, lon: currentLon };
                    lastGpsTime = currentTime;
                    currentSpeed = 0;
                }
                
                // Update UI
                document.getElementById('speedInput').value = currentSpeed;
                
                // Send speed to server
                updateSpeedOnServer(currentSpeed);
            }
            
            function onGpsError(error) {
                console.error('❌ [GPS] GPS error:', error.message);
                let errorMsg = '';
                
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'GPS permission denied. Please enable location access.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'GPS position unavailable. Make sure GPS is enabled.';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'GPS request timed out.';
                        break;
                    default:
                        errorMsg = 'Unknown GPS error.';
                }
                
                document.getElementById('connectionStatus').textContent = 'Status: ' + errorMsg;
                console.log('⚠️ [GPS]', errorMsg);
            }
            
            function calculateDistance(lat1, lon1, lat2, lon2) {
                // Haversine formula to calculate distance between two GPS coordinates
                const R = 6371; // Earth's radius in km
                const dLat = (lat2 - lat1) * Math.PI / 180;
                const dLon = (lon2 - lon1) * Math.PI / 180;
                
                const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                         Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                         Math.sin(dLon/2) * Math.sin(dLon/2);
                
                const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                const distance = R * c; // Distance in km
                
                return distance;
            }
            
            function stopGpsTracking() {
                if (gpsWatchId) {
                    navigator.geolocation.clearWatch(gpsWatchId);
                    gpsWatchId = null;
                    console.log('🛑 [GPS] GPS tracking stopped');
                }
            }
            
            async function updateSpeedOnServer(speed) {
                try {
                    const response = await fetch('/update_settings', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            device_id: deviceId,
                            speed: speed
                        })
                    });
                    
                    if (response.ok) {
                        // Speed updated successfully
                    }
                } catch(err) {
                    console.error('❌ [GPS] Failed to update speed on server:', err);
                }
            }

            async function toggleRoadMode() {
                const checkbox = document.getElementById('roadModeToggle');
                roadMode = checkbox.checked;
                console.log('⚙️ [SETTINGS] Road mode:', roadMode ? 'ON' : 'OFF');
                
                try {
                    const response = await fetch('/update_settings', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            device_id: deviceId,
                            road_mode: roadMode
                        })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('✅ [SETTINGS] Settings updated:', data);
                        const statusEl = document.getElementById('connectionStatus');
                        statusEl.textContent = 'Status: Mode = ' + (roadMode ? '🚗 ROAD' : '🏠 INDOOR');
                        statusEl.style.color = roadMode ? '#ff8800' : '#0ff';
                    }
                } catch(err) {
                    console.error('❌ [SETTINGS] Failed to update road mode:', err);
                }
            }

            // Note: Speed is now automatically updated by GPS
            // Speed limit is automatically updated by OCR from road signs
            // These are now read-only fields

            // Update UI immediately (script is at bottom, DOM is ready)
            console.log('📝 [INIT] Updating device info in UI...');
            document.getElementById('deviceInfo').textContent = 'Device ID: ' + deviceId;
            document.getElementById('connectionStatus').textContent = 'Status: Checking camera...';
            console.log('✅ [INIT] Device info updated to:', deviceId);

            // Watch for video readiness
            const localVideoElInit = document.getElementById('localVideo');
            localVideoElInit.addEventListener('loadedmetadata', () => {
                console.log('🎬 [VIDEO] loadedmetadata width/height:', localVideoElInit.videoWidth, localVideoElInit.videoHeight);
                videoReady = true;
            });
            localVideoElInit.addEventListener('loadeddata', () => {
                console.log('🎞️ [VIDEO] loadeddata readyState:', localVideoElInit.readyState);
                videoReady = true;
            });

            // Check camera support on page load
            window.addEventListener('load', async function() {
                console.log('📱 [CAMERA] Page loaded, checking camera support...');
                
                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                    console.error('❌ [CAMERA] getUserMedia API not supported');
                    document.getElementById('connectionStatus').textContent = 'Status: ❌ Camera API not supported';
                    document.getElementById('connectionStatus').style.color = '#f00';
                    document.getElementById('startBtn').disabled = true;
                    document.getElementById('startBtn').textContent = '❌ Camera Not Supported';
                    document.getElementById('alertBox').textContent = '⚠️ Your browser does not support camera access. Try Chrome or Firefox.';
                    document.getElementById('alertBox').className = 'alert-box alert-WARNING';
                    return;
                }
                
                console.log('✅ [CAMERA] getUserMedia API is supported');
                
                // Check if any cameras are available
                try {
                    console.log('🔍 [CAMERA] Enumerating devices...');
                    const devices = await navigator.mediaDevices.enumerateDevices();
                    const cameras = devices.filter(device => device.kind === 'videoinput');
                    
                    console.log('📹 [CAMERA] Found ' + cameras.length + ' camera(s):', cameras);
                    
                    if (cameras.length === 0) {
                        console.warn('⚠️ [CAMERA] No cameras detected');
                        document.getElementById('connectionStatus').textContent = 'Status: ⚠️ No cameras detected';
                        document.getElementById('connectionStatus').style.color = '#ff0';
                    } else {
                        console.log('✅ [CAMERA] System ready with ' + cameras.length + ' camera(s)');
                        document.getElementById('connectionStatus').textContent = 'Status: ✓ Ready (' + cameras.length + ' camera(s) available)';
                        document.getElementById('connectionStatus').style.color = '#0f0';
                    }
                } catch(err) {
                    console.error('❌ [CAMERA] Could not enumerate devices:', err);
                }
            });

            async function startCamera() {
                console.log('📹 [START] startCamera() called');
                try {
                    console.log('🔄 [START] Requesting camera access...');
                    document.getElementById('connectionStatus').textContent = 'Status: Requesting camera access...';
                    document.getElementById('connectionStatus').style.color = '#ff0';
                    
                    // Try with environment camera first (back camera)
                    let constraints = {
                        video: { facingMode: 'environment', width: 640, height: 480 },
                        audio: false
                    };
                    
                    console.log('📸 [START] Trying environment (back) camera...');
                    try {
                        localStream = await navigator.mediaDevices.getUserMedia(constraints);
                        console.log('✅ [START] Got environment camera stream');
                    } catch(err) {
                        // Fallback to any available camera
                        console.warn('⚠️ [START] Environment camera not available, trying any camera:', err.name);
                        constraints = {
                            video: { width: 640, height: 480 },
                            audio: false
                        };
                        localStream = await navigator.mediaDevices.getUserMedia(constraints);
                        console.log('✅ [START] Got fallback camera stream');
                    }
                    
                    console.log('🎥 [START] Setting video source...');
                    const localVideoEl = document.getElementById('localVideo');
                    localVideoEl.srcObject = localStream;
                    document.getElementById('startBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'block';
                    document.getElementById('resultVideo').style.display = 'block';
                    document.getElementById('connectionStatus').textContent = 'Status: Camera active, uploading frames...';
                    document.getElementById('connectionStatus').style.color = '#0f0';
                    
                    // Register device
                    console.log('📝 [START] Registering device with server...');
                    const regResponse = await fetch('/register_device', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({device_id: deviceId, device_name: 'Mobile ' + deviceId.substr(-4)})
                    });
                    
                    if (!regResponse.ok) {
                        console.error('❌ [START] Failed to register device:', regResponse.status);
                        throw new Error('Failed to register device');
                    }
                    
                    console.log('✅ [START] Device registered successfully');
                    
                    // Start uploading frames with an async loop (prevents overlap)
                    console.log('🚀 [START] Starting frame upload loop (~5 FPS)...');
                    uploadRunning = true;
                    uploadLoop();
                    
                    // Start checking for alerts
                    console.log('🚀 [START] Starting alert check interval...');
                    alertCheckInterval = setInterval(checkAlerts, 500);
                    
                    // Start GPS tracking for automatic speed calculation
                    console.log('📡 [START] Starting GPS tracking...');
                    startGpsTracking();
                    
                    console.log('✅ [START] Camera system fully initialized');
                    
                } catch(err) {
                    console.error('❌ [START] Camera error:', err);
                    let errorMsg = 'Error accessing camera: ' + err.name;
                    
                    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                        errorMsg = '❌ Camera permission denied. Please: 1. Grant camera permission in browser settings 2. Refresh the page 3. Try again. On Chrome: Settings > Privacy > Camera > Allow this site';
                    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                        errorMsg = '❌ No camera found on this device. Please check: Camera is not being used by another app. Camera is physically connected. Try a different browser.';
                    } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
                        errorMsg = '❌ Camera is in use by another application. Please: Close other apps using the camera. Restart the browser. Try again.';
                    } else if (err.name === 'NotSupportedError') {
                        errorMsg = '❌ Camera not supported. This might be because: You are not using HTTPS (required on some browsers). Browser does not support camera API. Try Chrome or Firefox.';
                    }
                    
                    alert(errorMsg);
                    document.getElementById('connectionStatus').textContent = 'Status: ' + err.name;
                    document.getElementById('connectionStatus').style.color = '#f00';
                    document.getElementById('alertBox').textContent = '❌ Camera Error - See message above';
                    document.getElementById('alertBox').className = 'alert-box alert-WARNING';
                }
            }

            function stopCamera() {
                if (localStream) {
                    localStream.getTracks().forEach(track => track.stop());
                    localStream = null;
                }
                uploadRunning = false;
                if (alertCheckInterval) {
                    clearInterval(alertCheckInterval);
                    alertCheckInterval = null;
                }
                
                // Stop GPS tracking
                stopGpsTracking();
                
                document.getElementById('localVideo').srcObject = null;
                document.getElementById('startBtn').style.display = 'block';
                document.getElementById('stopBtn').style.display = 'none';
                document.getElementById('resultVideo').style.display = 'none';
                document.getElementById('connectionStatus').textContent = 'Status: Stopped';
                document.getElementById('connectionStatus').style.color = '#ff0';
                document.getElementById('alertBox').className = 'alert-box alert-SAFE';
                document.getElementById('alertBox').textContent = '✓ Stopped';
            }

            async function uploadFrame() {
                if (!localStream) return false;
                const video = document.getElementById('localVideo');
                if (!videoReady || !video.videoWidth || !video.videoHeight) {
                    // Not ready yet
                    return false;
                }
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                try {
                    ctx.drawImage(video, 0, 0);
                } catch(e) {
                    console.warn('⚠️ [UPLOAD] drawImage failed, skipping frame:', e);
                    return false;
                }

                const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
                if (!blob) {
                    console.warn('⚠️ [UPLOAD] canvas.toBlob returned null, skipping');
                    return false;
                }

                const formData = new FormData();
                formData.append('frame', blob);
                formData.append('device_id', deviceId);

                try {
                    uploadCount++;
                    if ((uploadCount % 10) === 0) updateMetrics();
                    const response = await fetch('/upload_frame', { method: 'POST', body: formData });
                    if (response.ok) {
                        const resultBlob = await response.blob();
                        const resultUrl = URL.createObjectURL(resultBlob);
                        const resultEl = document.getElementById('resultVideo');
                        try { if (lastResultUrl) URL.revokeObjectURL(lastResultUrl); } catch(e) {}
                        lastResultUrl = resultUrl;
                        resultEl.src = resultUrl;
                        processedCount++;
                        if ((processedCount % 5) === 0) updateMetrics();

                        if (!firstProcessedShown) {
                            firstProcessedShown = true;
                            // Keep local video capturable: make it tiny/transparent, but not hidden
                            const lv = document.getElementById('localVideo');
                            lv.style.opacity = '0.01';
                            lv.style.width = '120px';
                            lv.style.height = '90px';
                            lv.style.border = '1px dashed #333';
                            lv.style.margin = '4px auto';
                            // Ensure processed image is visible and scrolled into view
                            resultEl.style.display = 'block';
                            try { window.scrollTo({ top: resultEl.offsetTop - 10, behavior: 'smooth' }); } catch(e) {}
                            const ab = document.getElementById('alertBox');
                            ab.className = 'alert-box alert-CAUTION';
                            ab.textContent = '✓ Showing processed view with detection boxes';
                        }
                        if (Math.random() < 0.05) {
                            console.log('📸 [UPLOAD] Frame uploaded and processed');
                        }
                        return true;
                    } else {
                        console.error('❌ [UPLOAD] Upload failed:', response.status);
                        return false;
                    }
                } catch(err) {
                    console.error('❌ [UPLOAD] Upload error:', err);
                    return false;
                }
            }

            async function uploadLoop() {
                if (!uploadRunning) return;
                const ok = await uploadFrame();
                // Pace the loop; slow down if frames failing
                const delay = ok ? 200 : 350;
                setTimeout(uploadLoop, delay);
            }

            async function checkAlerts() {
                try {
                    const response = await fetch('/get_alert/' + deviceId);
                    const alert = await response.json();
                    
                    const alertBox = document.getElementById('alertBox');
                    alertBox.className = 'alert-box alert-' + alert.level;
                    alertBox.textContent = alert.message;
                    if (alert.has_alert) { alertCount++; if ((alertCount % 3) === 0) updateMetrics(); }
                    
                    // Update speed limit display if available
                    if (alert.speed_limit !== undefined) {
                        const speedLimitInput = document.getElementById('speedLimitInput');
                        const currentLimit = parseInt(speedLimitInput.value) || 50;
                        if (alert.speed_limit !== currentLimit) {
                            speedLimitInput.value = alert.speed_limit;
                            console.log('🚦 [AUTO] Speed limit updated to:', alert.speed_limit, 'km/h');
                        }
                    }
                    
                    // Log only when alert changes or is CRITICAL
                    if (alert.has_alert && alert.level === 'CRITICAL') {
                        console.log('🚨 [ALERT] CRITICAL:', alert.message);
                    } else if (alert.has_alert && alert.level === 'WARNING') {
                        if (Math.random() < 0.1) { // Log 10% of warnings
                            console.log('⚠️ [ALERT] WARNING:', alert.message);
                        }
                    }
                    
                    // Voice alert
                    if (voiceEnabled && alert.has_alert && alert.voice_message) {
                        const now = Date.now();
                        if (alert.level === 'CRITICAL' || now - lastAlertTime > 1000) {
                            console.log('🔊 [VOICE] Speaking:', alert.voice_message);
                            speak(alert.voice_message);
                            lastAlertTime = now;
                        }
                    }
                } catch(err) {
                    console.error('❌ [ALERT] Alert check error:', err);
                }
            }

            function toggleVoice() {
                voiceEnabled = !voiceEnabled;
                const btn = document.getElementById('voiceBtn');
                btn.textContent = voiceEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF';
                btn.style.background = voiceEnabled ? '#0f0' : '#00f';
                btn.style.color = voiceEnabled ? '#000' : '#fff';
            }

            function speak(text) {
                if (synth.speaking) {
                    synth.cancel();
                }
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.2;
                utterance.pitch = 1.0;
                synth.speak(utterance);
            }
        </script>
    </body>
    </html>
    """
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    print(f"✅ [INDEX] Serving page with no-cache headers to {client_ip}")
    return response


@app.route('/register_device', methods=['POST'])
def register_device():
    """Register a new device"""
    client_ip = request.remote_addr
    data = request.get_json()
    device_id = data.get('device_id')
    device_name = data.get('device_name', 'Mobile')
    
    print(f"📱 [REGISTER] Device registration from {client_ip}: {device_name} ({device_id})")
    
    with sessions_lock:
        if device_id not in device_sessions:
            device_sessions[device_id] = DeviceSession(device_id, device_name)
            print(f"✅ [REGISTER] New device registered: {device_name} ({device_id})")
        else:
            print(f"ℹ️ [REGISTER] Device already registered: {device_name} ({device_id})")
    
    return jsonify({'status': 'registered', 'device_id': device_id})


@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    """Receive frame from mobile device"""
    device_id = request.form.get('device_id')
    client_ip = request.remote_addr
    
    if not device_id:
        print(f"❌ [UPLOAD] Missing device_id from {client_ip}")
        return "Missing device_id", 400
    
    with sessions_lock:
        if device_id not in device_sessions:
            print(f"❌ [UPLOAD] Device not registered: {device_id} from {client_ip}")
            return "Device not registered", 404
        session = device_sessions[device_id]
    
    # Get uploaded frame
    file = request.files.get('frame')
    if not file:
        print(f"❌ [UPLOAD] No frame provided by device {device_id}")
        return "No frame provided", 400
    
    try:
        # Decode image
        img = Image.open(file.stream)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Update session with new frame
        session.update_frame(frame)
        
        # Log every 10th frame to avoid spam
        if session.frame_count % 10 == 0:
            print(f"📸 [UPLOAD] Device {session.device_name}: Frame #{session.frame_count}")
        
        # Process frame
        processed_frame = process_device_frame(device_id)
        
        # Return processed frame
        if processed_frame is not None:
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return Response(buffer.tobytes(), mimetype='image/jpeg')
        else:
            print(f"❌ [UPLOAD] Processing error for device {device_id}")
            return "Processing error", 500
            
    except Exception as e:
        print(f"❌ [UPLOAD] Exception processing frame from {device_id}: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route('/get_alert/<device_id>')
def get_alert(device_id):
    """Get current alert for specific device"""
    with sessions_lock:
        if device_id not in device_sessions:
            # Don't log 404s to avoid spam
            return jsonify({'has_alert': False, 'message': 'Device not found', 'level': 'SAFE'})
        session = device_sessions[device_id]
    
    return jsonify(session.get_alert())


@app.route('/status')
def status():
    """Get system status with all connected devices"""
    client_ip = request.remote_addr
    print(f"📊 [STATUS] Status query from {client_ip}")
    
    with sessions_lock:
        devices = []
        for device_id, session in device_sessions.items():
            devices.append({
                'device_id': device_id,
                'device_name': session.device_name,
                'is_active': session.is_active(),
                'frame_count': session.frame_count,
                'last_update': session.last_update,
                'road_mode': session.road_mode,
                'speed': session.get_speed()
            })
    
    active_count = len([d for d in devices if d['is_active']])
    print(f"📊 [STATUS] Returning {len(devices)} device(s) ({active_count} active)")
    
    return jsonify({
        'total_devices': len(devices),
        'active_devices': active_count,
        'devices': devices
    })


@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update device settings (road mode, speed, speed limit)"""
    data = request.get_json()
    device_id = data.get('device_id')
    
    if not device_id:
        return jsonify({'error': 'Missing device_id'}), 400
    
    with sessions_lock:
        if device_id not in device_sessions:
            return jsonify({'error': 'Device not found'}), 404
        session = device_sessions[device_id]
    
    # Update road mode if provided
    if 'road_mode' in data:
        road_mode = data['road_mode']
        session.set_road_mode(road_mode)
        print(f"⚙️ [SETTINGS] Device {session.device_name} road_mode: {road_mode}")
    
    # Update speed if provided
    if 'speed' in data:
        speed = float(data['speed'])
        session.update_speed(speed)
        print(f"🚗 [SETTINGS] Device {session.device_name} speed: {speed} km/h")
    
    # Update speed limit if provided
    if 'speed_limit' in data:
        speed_limit = float(data['speed_limit'])
        session.set_speed_limit(speed_limit)
        print(f"🚦 [SETTINGS] Device {session.device_name} speed_limit: {speed_limit} km/h")
    
    return jsonify({
        'status': 'updated',
        'road_mode': session.road_mode,
        'speed': session.get_speed(),
        'speed_limit': session.get_speed_limit()
    })


@app.route('/get_settings/<device_id>')
def get_settings(device_id):
    """Get current settings for a device"""
    with sessions_lock:
        if device_id not in device_sessions:
            return jsonify({'error': 'Device not found'}), 404
        session = device_sessions[device_id]
    
    return jsonify({
        'road_mode': session.road_mode,
        'speed': session.get_speed(),
        'speed_limit': session.get_speed_limit(),
        'device_name': session.device_name
    })


def cleanup_inactive_sessions():
    """Periodically cleanup inactive sessions"""
    while True:
        time.sleep(60)  # Check every minute
        with sessions_lock:
            inactive = []
            for device_id, session in device_sessions.items():
                if not session.is_active(timeout=120):  # 2 minutes timeout
                    inactive.append(device_id)
            
            for device_id in inactive:
                print(f"⚠️ Removing inactive device: {device_id}")
                del device_sessions[device_id]


def main():
    global detector, voice_assistant
    
    print("=" * 70)
    print("🤖 YOLO MULTI-DEVICE DETECTION SYSTEM")
    print("=" * 70)
    print("Multiple mobile devices can connect simultaneously")
    print("Each device gets personalized detection and alerts")
    print()
    
    # Initialize detector
    detector = YOLOObjectDetector()
    
    # Initialize voice assistant
    voice_assistant = VoiceAssistant()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_inactive_sessions, daemon=True)
    cleanup_thread.start()
    
    # Get local IP
    local_ip = get_local_ip()
    print()
    print("📱 MOBILE ACCESS:")
    print("   Open browser on your mobile devices and go to:")
    print(f"   http://{local_ip}:{MOBILE_STREAM_PORT}/")
    print()
    print("💡 Each device will have its own session and receive personalized alerts")
    print(f"💡 Check system status at: http://{local_ip}:{MOBILE_STREAM_PORT}/status")
    print("=" * 70)
    
    # Run Flask server
    try:
        app.run(host='0.0.0.0', port=MOBILE_STREAM_PORT, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        if voice_assistant:
            voice_assistant.stop()
    
    print("=" * 70)
    print("Server stopped!")
    print("=" * 70)


if __name__ == "__main__":
    main()
