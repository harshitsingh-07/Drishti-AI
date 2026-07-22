"""
AI Eye - Real-time object detection with voice feedback
Optimized for performance and reliability
"""

import time
import threading
import subprocess
from typing import Dict, Tuple, Optional
from queue import Queue, Empty
from dataclasses import dataclass, field
from datetime import datetime

import cv2
from ultralytics import YOLO

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Configuration settings for AI Eye"""
    MODEL_PATH: str = "yolov8n.pt"
    CAMERA_INDEX: int = 0
    
    # Detection settings
    CONFIDENCE_THRESHOLD: float = 0.35
    INFERENCE_INTERVAL: float = 0.1  # 10 FPS inference
    
    # Speech settings
    SPEECH_RATE: int = 160
    SPEECH_REPEAT_COOLDOWN: float = 2.5  # Seconds before repeating same object
    DISTANCE_CHANGE_THRESHOLD: float = 0.4  # Meters
    
    # Display settings
    WINDOW_NAME: str = "AI Eye Detection"
    DISPLAY_FPS: bool = True
    
    # Threading
    SPEECH_THREAD_TIMEOUT: float = 3.0
    THREAD_INIT_WAIT: float = 1.0


# Import optional dependencies
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import win32com.client as wincl
    WINCL_AVAILABLE = True
except Exception:
    WINCL_AVAILABLE = False
    wincl = None


# ============================================================================
# SPEECH SYNTHESIS
# ============================================================================

class SpeechSynthesizer:
    """Handles text-to-speech with multiple fallback methods"""
    
    def __init__(self):
        self.config = Config()
        self._log("Initializing speech synthesis")
        self._log(f"Available: pyttsx3={PYTTSX3_AVAILABLE}, SAPI={WINCL_AVAILABLE}")
    
    def _log(self, message: str) -> None:
        """Log with timestamp"""
        print(f"[Speech] {message}")
    
    def speak_windows_sapi(self, text: str) -> bool:
        """Use Windows SAPI COM interface (most reliable)"""
        if not WINCL_AVAILABLE:
            return False
        try:
            speaker = wincl.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
            return True
        except Exception as e:
            self._log(f"SAPI failed: {e}")
            return False
    
    def speak_powershell(self, text: str) -> bool:
        """Use PowerShell System.Speech (reliable fallback)"""
        try:
            ps_script = f'''
[System.Reflection.Assembly]::LoadWithPartialName('System.Speech') | Out-Null
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Speak("{text}")
'''
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=10
            )
            return True
        except Exception as e:
            self._log(f"PowerShell failed: {e}")
            return False
    
    def speak_pyttsx3(self, text: str) -> bool:
        """Use pyttsx3 library (if available)"""
        if not PYTTSX3_AVAILABLE:
            return False
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", self.config.SPEECH_RATE)
            voices = engine.getProperty("voices")
            if voices:
                engine.setProperty("voice", voices[0].id)
            engine.say(text)
            engine.runAndWait()
            return True
        except Exception as e:
            self._log(f"pyttsx3 failed: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """Speak text using best available method"""
        # Try methods in priority order
        if self.speak_windows_sapi(text):
            return True
        if self.speak_powershell(text):
            return True
        if self.speak_pyttsx3(text):
            return True
        return False


class SpeechWorker(threading.Thread):
    """Background thread for non-blocking speech synthesis"""
    
    def __init__(self, queue: Queue, stop_event: threading.Event):
        super().__init__(name="SpeechWorker", daemon=False)
        self.queue = queue
        self.stop_event = stop_event
        self.synthesizer = SpeechSynthesizer()
    
    def run(self) -> None:
        """Worker thread main loop"""
        print("[Speech] Worker started")
        
        while not self.stop_event.is_set():
            try:
                text = self.queue.get(timeout=0.5)
                if text is None:
                    break
                
                # Speak the text
                if self.synthesizer.speak(text):
                    print(f"[Speech] ✓ Spoke: {text}")
                else:
                    print(f"[Speech] ✗ Failed to speak: {text}")
                    
            except Empty:
                # Queue timeout - this is normal, just continue waiting
                continue
            except Exception as e:
                print(f"[Speech] Unexpected error: {e}")
                break
        
        print("[Speech] Worker stopped")


# ============================================================================
# OBJECT DETECTION
# ============================================================================

@dataclass
class Detection:
    """Represents a detected object"""
    class_name: str
    center_x: float
    center_y: float
    width: float
    height: float
    confidence: float
    
    @property
    def area(self) -> float:
        return self.width * self.height


class ObjectTracker:
    """Tracks detected objects and manages speech announcements"""
    
    def __init__(self, config: Config):
        self.config = config
        self.tracked_objects: Dict[Tuple[str, str], Dict] = {}
    
    def get_position_label(self, center_x: float, frame_width: int) -> Tuple[str, str]:
        """Get position (left/center/right) and navigation guidance"""
        if center_x < frame_width * 0.35:
            return "left", "move right"
        elif center_x > frame_width * 0.65:
            return "right", "move left"
        return "center", "stay centered"
    
    def get_object_key(self, class_name: str, position: str) -> Tuple[str, str]:
        """Create unique key for tracking objects"""
        return (class_name.lower(), position)
    
    def should_announce(self, detection: Detection, distance: float, 
                       frame_width: int) -> bool:
        """Check if object should trigger speech announcement"""
        position, _ = self.get_position_label(detection.center_x, frame_width)
        key = self.get_object_key(detection.class_name, position)
        
        now = time.time()
        tracked = self.tracked_objects.get(key)
        
        # First detection of this object
        if tracked is None:
            return True
        
        # Too soon since last announcement
        if now - tracked["last_seen"] < self.config.SPEECH_REPEAT_COOLDOWN:
            return False
        
        # Distance and position unchanged
        distance_unchanged = abs(distance - tracked["distance"]) < self.config.DISTANCE_CHANGE_THRESHOLD
        position_unchanged = tracked["position"] == position
        if distance_unchanged and position_unchanged:
            return False
        
        return True
    
    def update_tracking(self, detection: Detection, distance: float, 
                       position: str) -> None:
        """Update tracking information after announcement"""
        key = self.get_object_key(detection.class_name, position)
        self.tracked_objects[key] = {
            "last_seen": time.time(),
            "distance": distance,
            "position": position,
            "class_name": detection.class_name.lower(),
        }


class DistanceEstimator:
    """Estimates distance to object based on bounding box size"""
    
    @staticmethod
    def estimate(detection: Detection, frame_width: int, frame_height: int) -> float:
        """Estimate distance using simple heuristic (will be replaced by ML model)"""
        frame_area = frame_width * frame_height
        ratio = detection.area / max(frame_area, 1)
        
        if ratio > 0.20:
            return 0.6
        elif ratio > 0.10:
            return 1.2
        elif ratio > 0.05:
            return 2.0
        elif ratio > 0.02:
            return 3.0
        return 4.5


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class AIEye:
    """Main AI Eye application"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.model = None
        self.cap = None
        self.speech_queue = Queue()
        self.stop_event = threading.Event()
        self.speech_thread = None
        self.tracker = ObjectTracker(self.config)
        self.distance_estimator = DistanceEstimator()
        
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
    
    def _log(self, message: str) -> None:
        """Log with timestamp"""
        print(f"[Main] {message}")
    
    def _speak(self, text: str) -> None:
        """Queue text for speech (non-blocking)"""
        self.speech_queue.put(text)
    
    def initialize(self) -> bool:
        """Initialize the application"""
        self._log("Initializing AI Eye...")
        
        # Load YOLO model
        try:
            self._log(f"Loading YOLO model: {self.config.MODEL_PATH}")
            self.model = YOLO(self.config.MODEL_PATH)
            self._log("YOLO model loaded ✓")
        except Exception as e:
            self._log(f"Failed to load model: {e}")
            return False
        
        # Initialize camera
        try:
            self._log(f"Opening camera {self.config.CAMERA_INDEX}")
            self.cap = cv2.VideoCapture(self.config.CAMERA_INDEX)
            if not self.cap.isOpened():
                self._log("Failed to open camera")
                return False
            self._log("Camera opened ✓")
        except Exception as e:
            self._log(f"Failed to open camera: {e}")
            return False
        
        # Start speech worker thread
        self.stop_event.clear()
        self.speech_thread = SpeechWorker(self.speech_queue, self.stop_event)
        self.speech_thread.start()
        self._log("Speech worker started ✓")
        
        # Give speech thread time to initialize
        time.sleep(self.config.THREAD_INIT_WAIT)
        
        return True
    
    def detect_objects(self, frame) -> list:
        """Run YOLO detection on frame"""
        results = self.model(frame, stream=False, conf=self.config.CONFIDENCE_THRESHOLD)
        detections = []
        
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                confidence = float(box.conf[0])
                if confidence < self.config.CONFIDENCE_THRESHOLD:
                    continue
                
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                x_center, y_center, width, height = box.xywh[0].tolist()
                
                detection = Detection(
                    class_name=class_name,
                    center_x=x_center,
                    center_y=y_center,
                    width=width,
                    height=height,
                    confidence=confidence
                )
                detections.append(detection)
        
        return detections
    
    def process_detections(self, detections: list, frame_width: int, frame_height: int) -> None:
        """Process detections and generate speech/visualizations"""
        if not detections:
            return
        
        # Get largest detection
        best_detection = max(detections, key=lambda d: d.area)
        
        # Estimate distance
        distance = self.distance_estimator.estimate(best_detection, frame_width, frame_height)
        
        # Get position info
        position, guidance = self.tracker.get_position_label(best_detection.center_x, frame_width)
        
        # Check if we should announce
        if self.tracker.should_announce(best_detection, distance, frame_width):
            message = f"{best_detection.class_name}, {distance:.1f} meters, {guidance}."
            self._speak(message)
            self.tracker.update_tracking(best_detection, distance, position)
    
    def draw_detections(self, frame, detections: list) -> None:
        """Draw bounding boxes and labels"""
        if not detections:
            cv2.putText(frame, "No object detected", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return
        
        # Get largest for distance display
        best_detection = max(detections, key=lambda d: d.area)
        distance = self.distance_estimator.estimate(best_detection, frame.shape[1], frame.shape[0])
        
        # Draw all detections
        for det in detections:
            x1 = int(det.center_x - det.width / 2)
            y1 = int(det.center_y - det.height / 2)
            x2 = int(det.center_x + det.width / 2)
            y2 = int(det.center_y + det.height / 2)
            
            color = (0, 255, 0) if det == best_detection else (200, 200, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{det.class_name} {det.confidence:.2f}", 
                       (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    def draw_ui(self, frame) -> None:
        """Draw UI elements"""
        # Title
        cv2.putText(frame, "AI Eye Detection System", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # FPS
        if self.config.DISPLAY_FPS:
            fps_text = f"FPS: {self.current_fps:.1f}"
            cv2.putText(frame, fps_text, (frame.shape[1] - 150, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Instructions
        cv2.putText(frame, "Press 'Q' to quit", (10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def update_fps(self) -> None:
        """Update FPS counter"""
        self.frame_count += 1
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_start_time = time.time()
    
    def run(self) -> None:
        """Main application loop"""
        if not self.initialize():
            self._log("Initialization failed")
            return
        
        self._log("Starting detection loop...")
        last_inference_time = 0.0
        
        try:
            while True:
                success, frame = self.cap.read()
                if not success:
                    self._log("Failed to read frame")
                    break
                
                height, width = frame.shape[:2]
                now = time.time()
                
                # Run inference at specified interval
                if now - last_inference_time >= self.config.INFERENCE_INTERVAL:
                    detections = self.detect_objects(frame)
                    self.process_detections(detections, width, height)
                    last_inference_time = now
                
                # Draw visualization
                if detections:
                    self.draw_detections(frame, detections)
                self.draw_ui(frame)
                
                # Display frame
                cv2.imshow(self.config.WINDOW_NAME, frame)
                self.update_fps()
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self._log("Quit requested by user")
                    break
                    
        except KeyboardInterrupt:
            self._log("Interrupted by user")
        except Exception as e:
            self._log(f"Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources"""
        self._log("Cleaning up...")
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        
        # Stop speech thread
        self.stop_event.set()
        self.speech_queue.put(None)
        if self.speech_thread:
            self.speech_thread.join(timeout=self.config.SPEECH_THREAD_TIMEOUT)
        
        self._log("Cleanup complete ✓")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    config = Config()
    app = AIEye(config)
    app.run()
