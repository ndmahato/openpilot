#!/usr/bin/env python3
"""
Simple test to verify voice assistant is working
"""
import pyttsx3
import threading
import queue
import time

class VoiceAssistant:
    """Queue-based voice assistant"""
    def __init__(self):
        self.engine = None
        self.enabled = False
        self.speech_queue = queue.Queue()
        self.speech_thread = None
        self.running = False

        try:
            print("Initializing voice assistant...")
            self.engine = pyttsx3.init()

            # Configure voice
            self.engine.setProperty('rate', 190)
            self.engine.setProperty('volume', 1.0)

            # Try to use Zira voice
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'zira' in voice.name.lower():
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
            self.enabled = False

    def _speech_worker(self):
        """Worker thread that processes speech queue"""
        while self.running:
            try:
                message = self.speech_queue.get(timeout=0.1)
                if message and self.engine:
                    print(f"Speaking: {message}")
                    self.engine.say(message)
                    self.engine.runAndWait()
                    print(f"Finished speaking: {message}")
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech worker error: {e}")
                time.sleep(0.1)

    def speak(self, message):
        """Add message to speech queue"""
        if not self.enabled or not message:
            return False

        if self.speech_queue.qsize() < 3:
            self.speech_queue.put(message)
            return True
        return False

    def stop(self):
        """Stop the voice assistant"""
        self.running = False
        if self.speech_thread:
            self.speech_thread.join(timeout=1.0)


def main():
    print("="*60)
    print("🔊 Voice Assistant Test")
    print("="*60)

    voice = VoiceAssistant()

    if not voice.enabled:
        print("❌ Voice assistant failed to initialize!")
        return

    print("\nTesting voice with multiple messages...")
    print("-"*60)

    # Test messages
    messages = [
        "Stop now! Person ahead",
        "Slow down! Car on left",
        "Caution! Bicycle on right",
        "Stop! Obstacle ahead",
        "Path clear, proceed safely"
    ]

    for i, msg in enumerate(messages, 1):
        print(f"\n[{i}] Queuing: {msg}")
        voice.speak(msg)
        time.sleep(2)  # Wait 2 seconds between messages

    print("\n-"*60)
    print("Waiting for speech to complete...")
    time.sleep(5)  # Wait for remaining speech to finish

    voice.stop()
    print("\n✅ Test complete!")
    print("="*60)


if __name__ == "__main__":
    main()
