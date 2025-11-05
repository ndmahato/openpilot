#!/usr/bin/env python3
"""
YOLO-Based Object Detection with Driver Alerts + Voice Assistance
Detects specific objects (person, chair, table, etc.) and provides distance alerts
Includes NLP-based voice assistance for hands-free operation

Requirements:
- pip install opencv-python numpy ultralytics pyttsx3

Objects it can detect (80+ classes):
- People & Animals: person, dog, cat, bird, horse, cow, etc.
- Vehicles: car, truck, bus, motorcycle, bicycle
- Furniture: chair, couch, bed, dining table, desk
- Kitchen: bottle, cup, bowl, knife, fork, refrigerator
- Electronics: TV, laptop, keyboard, mouse, cell phone
- And many more!
"""

import cv2
import numpy as np
from datetime import datetime
from ultralytics import YOLO
import pyttsx3
import threading
import queue
import time

# Configuration
CAMERA_URL = "http://192.168.1.7:4747/video"
WINDOW_NAME = "YOLO Object Detection - Driver Alerts"

# Alert thresholds based on object size in frame (percentage)
CRITICAL_SIZE = 0.20    # 20% of frame - very close
WARNING_SIZE = 0.10     # 10% of frame - close
CAUTION_SIZE = 0.04     # 4% of frame - moderate distance

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

        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)

                # Get class and confidence
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = self.model.names[cls_id]

                # Calculate size as percentage of frame
                obj_area = w * h
                size_percent = obj_area / frame_area

                detections.append({
                    'class': class_name,
                    'confidence': conf,
                    'box': (x, y, w, h),
                    'size': size_percent,
                    'center_x': x + w // 2,
                    'center_y': y + h // 2
                })

        return detections

    def calculate_distance(self, size_percent):
        """
        Estimate distance based on object size in frame
        Returns: (distance_meters, level, color)
        """
        if size_percent > CRITICAL_SIZE:
            return (0.5, "CRITICAL", COLOR_CRITICAL)
        elif size_percent > WARNING_SIZE:
            return (1.5, "WARNING", COLOR_WARNING)
        elif size_percent > CAUTION_SIZE:
            return (3.0, "CAUTION", COLOR_CAUTION)
        else:
            return (5.0, "MONITOR", COLOR_SAFE)

    def get_direction(self, center_x, frame_width):
        """Determine if object is left, center, or right"""
        left_third = frame_width // 3
        right_third = 2 * frame_width // 3

        if center_x < left_third:
            return "LEFT"
        elif center_x > right_third:
            return "RIGHT"
        else:
            return "AHEAD"

    def generate_alert(self, detections, frame_shape):
        """
        Generate alert based on detected objects
        Returns: (alert_message, alert_level, color, priority_objects)
        """
        if not detections:
            return ("✓ Clear - No objects detected", "SAFE", COLOR_SAFE, [])

        frame_height, frame_width = frame_shape[:2]

        # Separate high priority objects
        priority_objs = [d for d in detections if d['class'] in HIGH_PRIORITY_OBJECTS]
        furniture_objs = [d for d in detections if d['class'] in FURNITURE_OBJECTS]
        other_objs = [d for d in detections if d not in priority_objs and d not in furniture_objs]

        # Find most critical object
        all_objs = priority_objs + furniture_objs + other_objs
        critical_obj = max(all_objs, key=lambda x: x['size'])

        # Get details
        obj_class = critical_obj['class']
        distance, level, color = self.calculate_distance(critical_obj['size'])
        direction = self.get_direction(critical_obj['center_x'], frame_width)

        # Build alert message
        if level == "CRITICAL":
            msg = f"🚨 STOP! {obj_class.upper()} {direction} - {distance:.1f}m"
        elif level == "WARNING":
            msg = f"⚠️ SLOW DOWN! {obj_class} {direction} - {distance:.1f}m"
        elif level == "CAUTION":
            msg = f"⚠️ {obj_class.title()} detected {direction} - {distance:.1f}m"
        else:
            msg = f"👁️ Monitoring: {obj_class} {direction} - {distance:.1f}m"

        # Add count if multiple objects
        if len(detections) > 1:
            msg += f" | {len(detections)} objects total"

        return (msg, level, color, priority_objs)


def draw_detections(frame, detections, alert_msg, alert_level, color, voice_active=True, detector=None):
    """Draw bounding boxes and labels on frame"""
    height, width = frame.shape[:2]
    # detector passed as parameter to avoid re-initialization

    # Draw each detection
    for det in detections:
        x, y, w, h = det['box']
        class_name = det['class']
        confidence = det['confidence']
        size = det['size']

        # Get distance and color for this object
        distance, level, box_color = detector.calculate_distance(size)

        # Use special colors for people and furniture
        if class_name == 'person':
            box_color = COLOR_PERSON
        elif class_name in FURNITURE_OBJECTS:
            box_color = COLOR_FURNITURE

        # Draw semi-transparent filled box
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), box_color, -1)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

        # Draw border
        cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 3)

        # Prepare label
        label = f"{class_name} {distance:.1f}m"
        conf_label = f"{confidence:.0%}"

        # Draw label background
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(frame, (x, y - 50), (x + label_size[0] + 10, y - 5), box_color, -1)

        # Draw label text
        cv2.putText(frame, label, (x + 5, y - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)
        cv2.putText(frame, conf_label, (x + 5, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)

    # Draw center line
    cv2.line(frame, (width // 2, 0), (width // 2, height), COLOR_TEXT, 2, cv2.LINE_AA)

    # Draw alert banner
    banner_height = 120
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, banner_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Alert text
    cv2.putText(frame, alert_msg, (15, 50),
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)

    # Status
    status = f"Objects: {len(detections)} | Level: {alert_level} | AI: YOLOv8"
    cv2.putText(frame, status, (15, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

    # Voice assistant indicator
    voice_status = "🔊 Voice: ON" if voice_active else "🔇 Voice: OFF"
    voice_color = COLOR_SAFE if voice_active else (128, 128, 128)
    cv2.putText(frame, voice_status, (width - 200, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, voice_color, 2)

    # Instructions
    cv2.putText(frame, "Move camera to test | Press 'q' to quit",
               (15, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

    return frame


def main():
    print("="*70)
    print("🤖 YOLO OBJECT DETECTION - Smart Driver Alerts + Voice Assistant")
    print("="*70)
    print(f"Camera: {CAMERA_URL}")
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

    print("\nConnecting to camera...")
    cap = cv2.VideoCapture(CAMERA_URL)

    if not cap.isOpened():
        print("❌ ERROR: Could not connect to camera!")
        return

    print("✅ Connected! Detecting objects...")
    print("="*70)

    frame_count = 0
    last_alert_time = datetime.now()
    last_voice_time = datetime.now()
    fps_start_time = datetime.now()
    fps = 0
    previous_alert_level = None

    try:
        while True:
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
                                # Speak in background thread
                                voice_assistant.speak_async(voice_msg)
                                print(f"🔊 Speaking: {voice_msg} (Alert: {alert_level})")
                                last_voice_time = now
                                previous_alert_level = alert_level

                    # Optional: multi-object announcement only during danger
                    if alert_level in ["CRITICAL", "WARNING"] and len(detections) > 5:
                        multi_msg = voice_assistant.announce_detection(len(detections))
                        if multi_msg and (now - last_voice_time).total_seconds() > 6.0:
                            voice_assistant.speak_async(multi_msg)
                            print(f"🔊 Speaking: {multi_msg}")

                elif alert_level == "SAFE":
                    # No voice for SAFE; just reset previous alert state
                    previous_alert_level = None

                # Draw on frame
                frame = draw_detections(frame, detections, alert_msg, alert_level, color,
                                       voice_active=voice_assistant.enabled, detector=detector)

                # Add FPS counter
                cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 150, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)

                # Display
                cv2.imshow(WINDOW_NAME, frame)

                # Console alerts for critical/warning (throttled)
                if alert_level in ["CRITICAL", "WARNING"]:
                    now = datetime.now()
                    if (now - last_alert_time).total_seconds() > 2.0:
                        timestamp = now.strftime("%H:%M:%S")
                        print(f"[{timestamp}] {alert_msg}")
                        last_alert_time = now

                # Quit on 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nQuitting...")
                    break
            else:
                print("Warning: Could not read frame")
                break

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down...")
        voice_assistant.stop()
        cap.release()
        cv2.destroyAllWindows()
        print("\n" + "="*70)
        print(f"Test complete! Processed {frame_count} frames")
        print("="*70)


if __name__ == "__main__":
    main()
