#!/usr/bin/env python3
"""
YOLO-Based Object Detection with Driver Alerts + Voice Assistance + Mobile Streaming
Streams processed video with detections back to mobile device

Requirements:
- pip install opencv-python numpy ultralytics pyttsx3 flask

New Feature: 
- Streams processed video (with boxes, alerts, distances) to mobile browser
- Access from mobile: http://<your-pc-ip>:5000/video
"""

import cv2
import numpy as np
import os
from datetime import datetime
from ultralytics import YOLO
import pyttsx3
import threading
import queue
import time
from flask import Flask, Response, render_template_string, jsonify
import socket

# Configuration
# You can override camera URL by setting environment variable CAMERA_URL
# Example (PowerShell): $env:CAMERA_URL = "http://<phone-ip>:4747/video"
CAMERA_URL = os.getenv("CAMERA_URL", "http://192.168.1.7:4747/video")
WINDOW_NAME = "YOLO Object Detection - Driver Alerts"
MOBILE_STREAM_PORT = 5000  # Port for mobile streaming

# Alert thresholds based on object size in frame (percentage)
CRITICAL_SIZE = 0.20    # 20% of frame - very close
WARNING_SIZE = 0.10     # 10% of frame - close
CAUTION_SIZE = 0.04     # 4% of frame - moderate distance

# Driving path detection zone (center portion of frame width)
# Only alert for objects in this zone (as percentage from center)
DRIVING_PATH_CENTER_RATIO = 0.40  # Center 40% of frame width is the driving path
# Objects outside this zone are detected but not alerted

# Priority objects that need immediate attention
HIGH_PRIORITY_OBJECTS = {'person', 'dog', 'cat', 'car', 'truck', 'bicycle', 'motorcycle', 'bus'}
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

# Global variable to hold the latest processed frame
latest_frame = None
frame_lock = threading.Lock()

# Global variables for alert tracking (for mobile voice)
current_alert = {
    'has_alert': False,
    'message': '',
    'voice_message': '',
    'level': 'SAFE',
    'timestamp': 0
}
alert_lock = threading.Lock()


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
    """
    Voice assistance for continuous driver instructions
    Uses queue-based single-threaded speech for reliability
    """
    def __init__(self):
        self.engine = None
        self.enabled = False
        self.speech_queue = queue.Queue()
        self.speech_thread = None
        self.running = False

        try:
            print("Initializing voice assistant...")
            self.engine = pyttsx3.init()

            # Configure voice properties for better clarity
            self.engine.setProperty('rate', 190)  # Faster speed for urgency
            self.engine.setProperty('volume', 1.0)  # Maximum volume

            # Try to use a female voice if available (Zira on Windows)
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    print(f"Using voice: {voice.name}")
                    break

            # Start speech worker thread
            self.running = True
            self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
            self.speech_thread.start()

            print("✅ Voice assistant ready!")
            self.enabled = True

        except Exception as e:
            print(f"⚠️ Voice assistant unavailable: {e}")
            self.engine = None
            self.enabled = False

    def _speech_worker(self):
        """Worker thread that processes speech queue"""
        while self.running:
            try:
                # Get message from queue (wait up to 0.1 seconds)
                message = self.speech_queue.get(timeout=0.1)
                if message and self.engine:
                    self.engine.say(message)
                    self.engine.runAndWait()
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech worker error: {e}")
                time.sleep(0.1)

    def speak_now(self, message):
        """
        Speak immediately - adds to queue for immediate processing
        """
        if not self.engine or not message or not self.enabled:
            return False

        try:
            # Clear queue and add urgent message
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break
            self.speech_queue.put(message)
            return True
        except Exception as e:
            print(f"Speech error: {e}")
            return False

    def speak_async(self, message):
        """
        Speak in background - adds message to queue
        Queue processes messages one at a time
        """
        if not self.engine or not message or not self.enabled:
            return

        try:
            # Don't let queue grow too large
            if self.speech_queue.qsize() < 2:
                self.speech_queue.put(message)
        except Exception as e:
            print(f"Queue error: {e}")

    def generate_voice_instruction(self, alert_level, obj_class, direction, distance):
        """
        Generate natural language instruction for voice
        Returns: spoken instruction text
        """
        # Simplify object names for natural speech
        obj_name = obj_class.replace('_', ' ')

        if alert_level == "CRITICAL":
            if obj_class == "person":
                return f"Stop now! Person {direction.lower()}"
            elif obj_class in HIGH_PRIORITY_OBJECTS:
                return f"Stop! {obj_name} {direction.lower()}"
            else:
                return f"Stop! {obj_name} {direction.lower()}"

        elif alert_level == "WARNING":
            if obj_class == "person":
                return f"Caution! Person {direction.lower()}"
            else:
                return f"Slow down! {obj_name} {direction.lower()}"

        elif alert_level == "CAUTION":
            return f"{obj_name} detected {direction.lower()}"

        else:
            return None  # Don't speak for MONITOR level

    def announce_detection(self, detections_count):
        """Announce when multiple objects are detected"""
        if detections_count > 5:
            return "Multiple objects detected"
        return None

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
        self.model = YOLO('yolov8n.pt')  # Use nano model for speed
        self.model.fuse()  # Optimize model
        print("✅ YOLO model loaded!")

        # Confidence threshold
        self.conf_threshold = 0.25

    def detect_objects(self, frame):
        """
        Detect objects using YOLO
        Returns: list of (class_name, confidence, x, y, w, h, size_percent)
        """
        height, width = frame.shape[:2]
        frame_area = height * width

        # Run YOLO detection
        results = self.model(frame, conf=self.conf_threshold, verbose=False)

        detections = []

        if len(results) > 0:
            result = results[0]
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x, y, w, h = int(x1), int(y1), int(x2-x1), int(y2-y1)

                    # Get class and confidence
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls]

                    # Calculate object size as percentage of frame
                    obj_area = w * h
                    size_percent = (obj_area / frame_area) * 100

                    # Calculate center
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

    def calculate_distance(self, size_percent):
        """
        Estimate distance based on object size
        Returns: (distance_m, alert_level, color)
        """
        if size_percent >= CRITICAL_SIZE * 100:
            return 0.5, "CRITICAL", COLOR_CRITICAL
        elif size_percent >= WARNING_SIZE * 100:
            return 1.5, "WARNING", COLOR_WARNING
        elif size_percent >= CAUTION_SIZE * 100:
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

    def is_in_driving_path(self, center_x, frame_width):
        """
        Check if object is in the driving path (center zone of frame)
        Only objects in this zone should trigger alerts
        Returns: True if object is in driving path, False otherwise
        """
        frame_center = frame_width / 2
        path_half_width = (frame_width * DRIVING_PATH_CENTER_RATIO) / 2
        
        # Define driving path boundaries
        path_left = frame_center - path_half_width
        path_right = frame_center + path_half_width
        
        return path_left <= center_x <= path_right

    def generate_alert(self, detections, frame_shape):
        """
        Generate alert message based on detections IN THE DRIVING PATH ONLY
        Objects outside the driving path are detected but won't trigger alerts
        Returns: (message, alert_level, color, priority_objects)
        """
        if not detections:
            return "All clear", "SAFE", COLOR_SAFE, []

        height, width = frame_shape[:2]

        # Filter detections to only those in the driving path
        path_detections = []
        for det in detections:
            if self.is_in_driving_path(det['center_x'], width):
                path_detections.append(det)

        # If no objects in driving path, return safe status
        if not path_detections:
            return "Path clear", "SAFE", COLOR_SAFE, []

        # Find highest priority object IN THE DRIVING PATH
        priority_objs = []
        max_priority = 0

        for det in path_detections:
            obj_class = det['class']
            size = det['size']
            distance, level, color = self.calculate_distance(size)
            direction = self.get_direction(det['center_x'], width)

            # Priority calculation
            priority = 0
            if level == "CRITICAL":
                priority = 3
            elif level == "WARNING":
                priority = 2
            elif level == "CAUTION":
                priority = 1

            # Boost priority for high-priority objects
            if obj_class in HIGH_PRIORITY_OBJECTS:
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

        # Get highest priority object
        priority_objs.sort(key=lambda x: x['priority'], reverse=True)
        top_obj = priority_objs[0]

        # Generate message
        obj_name = top_obj['class'].upper().replace('_', ' ')
        direction = top_obj['direction']
        distance = top_obj['distance']
        level = top_obj['level']
        color = top_obj['color']

        if level == "CRITICAL":
            msg = f"🚨 STOP! {obj_name} {direction} - {distance}m"
        elif level == "WARNING":
            msg = f"⚠️ SLOW DOWN! {obj_name} {direction} - {distance}m"
        elif level == "CAUTION":
            msg = f"⚡ CAUTION! {obj_name} {direction} - {distance}m"
        else:
            msg = f"✓ Monitor: {obj_name} {direction} - {distance}m"

        # Show only in-path object count
        if len(path_detections) > 1:
            msg += f" | {len(path_detections)} in path"

        return (msg, level, color, priority_objs)


def draw_detections(frame, detections, alert_msg, alert_level, color, voice_active=True, detector=None):
    """Draw bounding boxes and labels on frame.
    Shows driving path zone and only highlights in-path objects.
    Ensure the top-priority IN-PATH object's box color matches the alert banner color.
    """
    height, width = frame.shape[:2]

    # Draw driving path zone (semi-transparent overlay on center)
    frame_center = width / 2
    path_half_width = (width * DRIVING_PATH_CENTER_RATIO) / 2
    path_left = int(frame_center - path_half_width)
    path_right = int(frame_center + path_half_width)
    
    # Draw vertical lines to mark driving path boundaries
    cv2.line(frame, (path_left, 0), (path_left, height), COLOR_SAFE, 2)
    cv2.line(frame, (path_right, 0), (path_right, height), COLOR_SAFE, 2)
    
    # Add "DRIVING PATH" label at top
    path_label = "DRIVING PATH"
    label_size = cv2.getTextSize(path_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    label_x = int(frame_center - label_size[0] / 2)
    cv2.putText(frame, path_label, (label_x, height - 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_SAFE, 2)

    # Filter detections to those in driving path for priority calculation
    in_path_detections = [det for det in detections if detector.is_in_driving_path(det['center_x'], width)]

    # Determine top-priority detection index (only from in-path objects)
    top_index = -1
    max_priority = -1
    for i, det in enumerate(detections):
        # Only consider objects in driving path for top priority
        if det not in in_path_detections:
            continue
            
        size = det['size']
        obj_class = det['class']
        _, level, _ = detector.calculate_distance(size)
        priority = 0
        if level == "CRITICAL":
            priority = 3
        elif level == "WARNING":
            priority = 2
        elif level == "CAUTION":
            priority = 1
        # Boost priority for high-priority objects
        if obj_class in HIGH_PRIORITY_OBJECTS:
            priority += 1
        if priority >= max_priority:
            max_priority = priority
            top_index = i

    # Draw each detection
    for i, det in enumerate(detections):
        x, y, w, h = det['box']
        class_name = det['class']
        confidence = det['confidence']
        size = det['size']
        in_path = det in in_path_detections

        # Get distance and default color for this object
        distance, level, box_color = detector.calculate_distance(size)

        # Dim out-of-path objects
        if not in_path:
            box_color = (100, 100, 100)  # Gray for out-of-path objects
            thickness = 1
            alpha = 0.05  # Very light fill
        else:
            # In-path objects get full color treatment
            if i == top_index:
                # Top-priority in-path object matches banner color
                box_color = color
                thickness = 3
            else:
                # Other in-path objects use special colors
                if class_name == 'person':
                    box_color = COLOR_PERSON
                elif class_name in FURNITURE_OBJECTS:
                    box_color = COLOR_FURNITURE
                thickness = 2 if level in ["CRITICAL", "WARNING"] else 2
            alpha = 0.15

        # Draw semi-transparent filled box
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), box_color, -1)
        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)

        # Draw border
        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, thickness)

        # Label background
        label = f"{class_name} {distance}m ({confidence:.2f})"
        if not in_path:
            label = f"{class_name} (side)"  # Shorter label for side objects
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        cv2.rectangle(frame, (x, y - label_size[1] - 8),
                      (x + label_size[0] + 8, y), box_color, -1)

        # Label text
        cv2.putText(frame, label, (x + 4, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)

    # Alert banner
    banner_height = 120
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, banner_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Alert message
    cv2.putText(frame, alert_msg, (15, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 3)

    # Status - show both total and in-path counts
    in_path_count = len(in_path_detections)
    status = f"Total: {len(detections)} | In-Path: {in_path_count} | Level: {alert_level} | AI: YOLOv8"
    cv2.putText(frame, status, (15, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

    # Voice assistant indicator
    voice_status = "🔊 Voice: ON" if voice_active else "🔇 Voice: OFF"
    voice_color = COLOR_SAFE if voice_active else (128, 128, 128)
    cv2.putText(frame, voice_status, (width - 200, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, voice_color, 2)

    # Instructions
    cv2.putText(frame, "Desktop + Mobile View | Press 'q' to quit",
               (15, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

    return frame


def generate_frames():
    """Generator function for Flask streaming"""
    global latest_frame, frame_lock
    
    # Wait for first frame but don't block forever
    # If no frame yet, send a lightweight placeholder periodically
    wait_loops = 0
    while latest_frame is None and wait_loops < 50:  # ~5 seconds
        time.sleep(0.1)
        wait_loops += 1
    
    while True:
        # Default to a placeholder frame if nothing available yet
        with frame_lock:
            frame = latest_frame.copy() if latest_frame is not None else None

        if frame is None:
            # Create a small placeholder image
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Waiting for camera...", (30, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
        
        # Encode frame as JPEG
        try:
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print(f"Frame encoding error: {e}")
        
        time.sleep(0.033)  # ~30 fps


@app.route('/')
def index():
    """Mobile-friendly HTML page with voice alerts"""
    local_ip = get_local_ip()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Driver Alerts - Mobile View</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: #000;
                font-family: Arial, sans-serif;
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .header p {{
                margin: 5px 0 0 0;
                font-size: 14px;
                opacity: 0.9;
            }}
            .video-container {{
                width: 100%;
                height: calc(100vh - 140px);
                display: flex;
                justify-content: center;
                align-items: center;
                background: #000;
            }}
            img {{
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }}
            .info {{
                position: fixed;
                bottom: 10px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 12px;
            }}
            .voice-control {{
                position: fixed;
                top: 110px;
                right: 10px;
                background: rgba(0,255,0,0.8);
                color: white;
                padding: 10px 15px;
                border-radius: 50%;
                font-size: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.5);
                cursor: pointer;
                z-index: 1000;
                user-select: none;
            }}
            .voice-control.muted {{
                background: rgba(255,0,0,0.8);
            }}
            .alert-toast {{
                position: fixed;
                top: 120px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(255,0,0,0.9);
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                display: none;
                z-index: 999;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 Driver Alert System</h1>
            <p>Real-time Object Detection with Voice Alerts</p>
        </div>
        <div class="voice-control" id="voiceToggle" onclick="toggleVoice()">
            🔊
        </div>
        <div class="alert-toast" id="alertToast"></div>
        <div class="video-container">
            <img src="/video_feed" alt="Detection Stream">
        </div>
        <div class="info">
            📱 Mobile View | 🔊 Voice: <span id="voiceStatus">ON</span> | {local_ip}:{MOBILE_STREAM_PORT}
        </div>

        <script>
            let voiceEnabled = true;
            let lastAlert = "";
            let lastAlertTime = 0;
            let synth = window.speechSynthesis;
            let currentUtterance = null;

            function toggleVoice() {{
                voiceEnabled = !voiceEnabled;
                const btn = document.getElementById('voiceToggle');
                const status = document.getElementById('voiceStatus');
                
                if (voiceEnabled) {{
                    btn.textContent = '🔊';
                    btn.classList.remove('muted');
                    status.textContent = 'ON';
                }} else {{
                    btn.textContent = '🔇';
                    btn.classList.add('muted');
                    status.textContent = 'OFF';
                    // Stop any ongoing speech
                    if (synth.speaking) {{
                        synth.cancel();
                    }}
                }}
            }}

            function showAlertToast(message, level) {{
                const toast = document.getElementById('alertToast');
                toast.textContent = message;
                
                // Color based on alert level
                if (level === 'CRITICAL') {{
                    toast.style.background = 'rgba(255,0,0,0.95)';
                }} else if (level === 'WARNING') {{
                    toast.style.background = 'rgba(255,165,0,0.95)';
                }} else if (level === 'CAUTION') {{
                    toast.style.background = 'rgba(255,255,0,0.95)';
                    toast.style.color = '#000';
                }} else {{
                    toast.style.background = 'rgba(0,255,0,0.8)';
                }}
                
                toast.style.display = 'block';
                setTimeout(() => {{
                    toast.style.display = 'none';
                }}, 2000);
            }}

            function speak(message, level) {{
                if (!voiceEnabled) return;
                if (!synth) return;

                const now = Date.now();

                if (level === 'CRITICAL') {{
                    // For red alerts: repeat continuously as fast as the TTS can finish
                    // Do NOT cancel ongoing speech to avoid stutter; wait until it finishes
                    if (synth.speaking) return;
                    lastAlert = message;
                    lastAlertTime = now;
                }} else if (level === 'WARNING') {{
                    // For amber alerts: throttle repeats to ~1s
                    if (message === lastAlert && (now - lastAlertTime) < 1000) return;
                    lastAlert = message;
                    lastAlertTime = now;
                }} else {{
                    // No speech for other levels
                    return;
                }}

                // Create utterance
                const utterance = new SpeechSynthesisUtterance(message);
                utterance.rate = 1.2;  // Slightly faster for urgency
                utterance.pitch = 1.0;
                utterance.volume = 1.0;

                // Adjust rate based on alert level
                if (level === 'CRITICAL') {{
                    utterance.rate = 1.3;
                    utterance.volume = 1.0;
                }} else if (level === 'WARNING') {{
                    utterance.rate = 1.2;
                }} else {{
                    utterance.rate = 1.0;
                }}

                synth.speak(utterance);
            }}

            // Poll server for alerts
            function checkForAlerts() {{
                fetch('/get_alert')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.alert && data.message) {{
                            // Always show visual toast
                            showAlertToast(data.message, data.level);
                            // Speak ONLY for danger levels (amber/red)
                            if (data.level === 'CRITICAL' || data.level === 'WARNING') {{
                                speak(data.voice_message, data.level);
                            }}
                        }}
                    }})
                    .catch(err => console.log('Alert check error:', err));
            }}

            // Check for alerts every 500ms
            setInterval(checkForAlerts, 500);

            // Ensure speech synthesis is ready
            if ('speechSynthesis' in window) {{
                console.log('Voice alerts enabled on mobile');
            }} else {{
                console.warn('Speech synthesis not supported on this browser');
                voiceEnabled = false;
                toggleVoice();
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_alert')
def get_alert():
    """Return current alert for mobile voice"""
    global current_alert, alert_lock
    
    with alert_lock:
        alert_data = current_alert.copy()
    
    return jsonify({
        'alert': alert_data['has_alert'],
        'message': alert_data['message'],
        'voice_message': alert_data['voice_message'],
        'level': alert_data['level']
    })


def run_flask_server():
    """Run Flask server in background thread"""
    app.run(host='0.0.0.0', port=MOBILE_STREAM_PORT, debug=False, threaded=True, use_reloader=False)


def main():
    global latest_frame, frame_lock, current_alert, alert_lock
    
    local_ip = get_local_ip()
    
    print("="*70)
    print("🤖 YOLO OBJECT DETECTION - Desktop + Mobile View")
    print("="*70)
    print(f"Camera: {CAMERA_URL}")
    print("\n📱 MOBILE ACCESS:")
    print("   Open browser on your mobile and go to:")
    print(f"   http://{local_ip}:{MOBILE_STREAM_PORT}/")
    print("\n💡 Make sure mobile and PC are on same WiFi network")
    print("\n🎯 This system can identify specific objects!")
    print("🔊 Voice assistance enabled for hands-free operation")
    print("\nDetectable objects include:")
    print("- People & Animals: person, dog, cat, bird, etc.")
    print("- Vehicles: car, truck, bus, bicycle, motorcycle")
    print("- Furniture: chair, couch, bed, table, etc.")
    print("- Kitchen items: bottle, cup, bowl, etc.")
    print("- Electronics: TV, laptop, phone, etc.")
    print("- And 80+ more object classes!")
    print("="*70)

    # Initialize detector and voice assistant
    detector = YOLOObjectDetector()
    voice_assistant = VoiceAssistant()

    # Start Flask server in background
    print("\nStarting mobile streaming server...")
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    time.sleep(2)  # Give server time to start
    print(f"✅ Mobile server running at http://{local_ip}:{MOBILE_STREAM_PORT}/")

    # Show a placeholder immediately so /video_feed has content on mobile
    with frame_lock:
        latest_frame = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(latest_frame, "Connecting to camera...", (30, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

    print("\nConnecting to camera...")
    cap = cv2.VideoCapture(CAMERA_URL)

    use_placeholder = False
    if not cap.isOpened():
        print(f"❌ Could not open network camera at {CAMERA_URL}")
        print("🔁 Trying default webcam (index 0)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ No camera available. Falling back to placeholder feed.")
            use_placeholder = True
        else:
            print("✅ Connected to default webcam!")
    else:
        print("✅ Connected to network camera!")

    print("✅ Connected! Detecting objects...")
    print("="*70)

    frame_count = 0
    last_alert_time = datetime.now()
    last_voice_time = datetime.now()
    # previous_alert_level removed (unused)
    fps = 0
    fps_start_time = datetime.now()

    try:
        while True:
            if use_placeholder:
                # Generate a placeholder frame and update stream
                frame = np.zeros((480, 854, 3), dtype=np.uint8)
                cv2.putText(frame, "No camera connected", (40, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                cv2.putText(frame, "Set CAMERA_URL env var to your DroidCam URL", (40, 250),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, f"Current: {CAMERA_URL}", (40, 285),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                # Update global frame for mobile streaming
                with frame_lock:
                    latest_frame = frame.copy()

                # Also show on desktop
                cv2.imshow(WINDOW_NAME, frame)

                # Throttle a bit
                time.sleep(0.1)
            else:
                ret, frame = cap.read()

                if ret and frame is not None:
                    frame_count += 1

                    # Calculate FPS every 10 frames
                    if frame_count % 10 == 0:
                        fps_end_time = datetime.now()
                        time_diff = (fps_end_time - fps_start_time).total_seconds()
                        if time_diff > 0:
                            fps = 10 / time_diff
                        fps_start_time = fps_end_time

                    # Detect objects
                    detections = detector.detect_objects(frame)

                    # Generate alert
                    alert_msg, alert_level, color, priority_objs = detector.generate_alert(
                        detections, frame.shape
                    )

                    # Voice instructions - TRUE CONTINUOUS ALERTS
                    now = datetime.now()
                    voice_msg = None
                    if alert_level in ["CRITICAL", "WARNING"]:
                        # Get most critical object
                        if detections:
                            critical_obj = max(detections, key=lambda x: x['size'])
                            obj_class = critical_obj['class']
                            direction = detector.get_direction(
                                critical_obj['center_x'],
                                frame.shape[1]
                            )
                            distance, _, _ = detector.calculate_distance(critical_obj['size'])

                            # Generate voice instruction
                            voice_msg = voice_assistant.generate_voice_instruction(
                                alert_level, obj_class, direction, distance
                            )

                        if voice_msg:
                            # TRUE CONTINUOUS ALERTING - ALWAYS SPEAK ON EVERY FRAME
                            # For CRITICAL (red box), speak EVERY frame (no delay)
                            # For WARNING (orange box), speak every other frame

                            should_speak = False
                            if alert_level == "CRITICAL":
                                # CRITICAL: Speak continuously, no waiting
                                should_speak = True
                            elif alert_level == "WARNING":
                                # WARNING: Speak every 1 second
                                time_since_voice = (now - last_voice_time).total_seconds()
                                should_speak = time_since_voice >= 1.0

                            if should_speak:
                                # Speak in background thread (PC speakers)
                                voice_assistant.speak_async(voice_msg)
                                print(f"🔊 Speaking: {voice_msg} (Alert: {alert_level})")
                                last_voice_time = now
                                
                                # Update alert for mobile voice
                                with alert_lock:
                                    current_alert['has_alert'] = True
                                    current_alert['message'] = alert_msg
                                    current_alert['voice_message'] = voice_msg
                                    current_alert['level'] = alert_level
                                    current_alert['timestamp'] = time.time()

                        # Announce if many objects detected (less frequent)
                        if len(detections) > 5:
                            multi_msg = voice_assistant.announce_detection(len(detections))
                            time_since_multi = (now - last_alert_time).total_seconds()
                            if multi_msg and time_since_multi > 5.0:
                                voice_assistant.speak_async(multi_msg)
                                last_alert_time = now

                    elif alert_level == "SAFE" or alert_level == "CAUTION":
                        # No voice or mobile voice for SAFE/CAUTION; clear any active mobile voice alert
                        with alert_lock:
                            current_alert['has_alert'] = False
                            current_alert['message'] = ''
                            current_alert['voice_message'] = ''
                            current_alert['level'] = alert_level
                            current_alert['timestamp'] = time.time()

                    # Draw on frame
                    frame = draw_detections(frame, detections, alert_msg, alert_level, color,
                                           voice_active=voice_assistant.enabled, detector=detector)

                    # Add FPS counter
                    cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 150, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

                    # Update global frame for mobile streaming (every frame)
                    with frame_lock:
                        latest_frame = frame.copy()

                    # Display on desktop
                    cv2.imshow(WINDOW_NAME, frame)

                    # Print alerts periodically
                    if alert_level in ["CRITICAL", "WARNING"]:
                        time_since_print = (now - last_alert_time).total_seconds()
                        if time_since_print >= 2.0:
                            timestamp = now.strftime("%H:%M:%S")
                            print(f"[{timestamp}] {alert_msg}")
                            last_alert_time = now
                else:
                    # Read failed; brief pause and continue to next loop
                    time.sleep(0.01)

            # Check for quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nStopping detection...")
                break

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    finally:
        print("\nShutting down...")
        cap.release()
        cv2.destroyAllWindows()
        voice_assistant.stop()

        print("="*70)
        print(f"Test complete! Processed {frame_count} frames")
        print("="*70)


if __name__ == "__main__":
    main()
