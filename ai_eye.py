"""
AI Eye - Real-time object detection with voice feedback
Optimized for performance and reliability
"""

import time
import os
import threading
import subprocess
import concurrent.futures
from typing import Dict, Tuple, Optional, List
from queue import Queue, Empty
from dataclasses import dataclass

import cv2
import ollama
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
    IOU_THRESHOLD: float = 0.45
    INFERENCE_INTERVAL: float = 0.1  # 10 FPS inference
    MIN_CONSECUTIVE_FRAMES: int = 3

    # Speech settings
    SPEECH_RATE: int = 160
    SPEECH_REPEAT_COOLDOWN: float = 2.5  # Seconds before repeating same object
    DISTANCE_CHANGE_THRESHOLD: float = 0.4  # Meters

    # LLM narration
    USE_LLM_NARRATION: bool = True
    LLM_MODEL: str = "qwen2.5:0.5b"
    LLM_TIMEOUT_SECONDS: float = 12.0
    LLM_MAX_TOKENS: int = 35
    LLM_SPEECH_PREFIX: str = "AI says:"
    TEMPLATE_SPEECH_PREFIX: str = "Template:"

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
# OLLAMA HELPERS
# ============================================================================

OLLAMA_EXE_CANDIDATES = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
    os.path.join(os.environ.get("ProgramFiles", ""), "Ollama", "ollama.exe"),
)


def _find_ollama_exe() -> Optional[str]:
    """Return path to ollama.exe if installed."""
    for path in OLLAMA_EXE_CANDIDATES:
        if path and os.path.isfile(path):
            return path
    return None


def _is_ollama_running() -> bool:
    """Return True when the local Ollama API responds."""
    try:
        ollama.list()
        return True
    except Exception:
        return False


def _start_ollama_server() -> bool:
    """Start Ollama in the background and wait briefly for the API."""
    ollama_exe = _find_ollama_exe()
    if not ollama_exe:
        return False

    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [ollama_exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception:
        return False

    for _ in range(20):
        if _is_ollama_running():
            return True
        time.sleep(0.5)
    return False


def ensure_ollama_ready(model: str, log_fn=print) -> bool:
    """Ensure Ollama is running and the requested model is available."""
    if not _is_ollama_running():
        log_fn("[Main] Ollama not running — trying to start...")
        if not _start_ollama_server():
            log_fn("[Main] Ollama not installed or could not start.")
            log_fn("[Main] Run OllamaSetup.exe, then: ollama pull " + model)
            return False
        log_fn("[Main] Ollama started ✓")

    try:
        listed = ollama.list()
        model_names = {m.model.split(":")[0] for m in listed.models}
        requested = model.split(":")[0]
        if requested not in model_names:
            log_fn(f"[Main] Pulling model: {model}")
            ollama.pull(model)
        return True
    except Exception as exc:
        log_fn(f"[Main] Ollama model check failed: {exc}")
        return False


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

                if self.synthesizer.speak(text):
                    print(f"[Speech] ✓ Spoke: {text}")
                else:
                    print(f"[Speech] ✗ Failed to speak: {text}")

            except Empty:
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


def get_position(center_x: float, frame_width: int) -> Tuple[str, str]:
    """Classify object position and return navigation guidance."""
    if center_x < frame_width * 0.35:
        return "left", "move right"
    if center_x > frame_width * 0.65:
        return "right", "move left"
    return "center", "stay centered"


def _object_key(class_name: str, center_x: float, frame_width: int) -> Tuple[str, str]:
    """Create a stable tracking key from class name and horizontal position."""
    position, _ = get_position(center_x, frame_width)
    return class_name.lower(), position


class DetectionStabilizer:
    """Confirm detections only after consecutive frame agreement."""

    def __init__(self, config: Config):
        self.config = config
        self._frame_counts: Dict[Tuple[str, str], int] = {}
        self._latest_detections: Dict[Tuple[str, str], Detection] = {}

    def update(self, detections: List[Detection], frame_width: int) -> List[Detection]:
        """Return detections confirmed across MIN_CONSECUTIVE_FRAMES."""
        seen_keys = set()
        confirmed: List[Detection] = []

        for detection in detections:
            key = _object_key(detection.class_name, detection.center_x, frame_width)
            seen_keys.add(key)
            count = self._frame_counts.get(key, 0) + 1
            self._frame_counts[key] = count
            self._latest_detections[key] = detection

            if count >= self.config.MIN_CONSECUTIVE_FRAMES:
                confirmed.append(detection)

        for key in list(self._frame_counts.keys()):
            if key not in seen_keys:
                del self._frame_counts[key]
                self._latest_detections.pop(key, None)

        return confirmed


class AnnouncementTracker:
    """Decide when a confirmed object should be spoken again."""

    def __init__(self, config: Config):
        self.config = config
        self._announced: Dict[Tuple[str, str], Dict[str, float]] = {}

    def should_announce(self, class_name: str, position: str, distance: float) -> bool:
        """Return True when cooldown and distance/position changes allow speech."""
        key = (class_name.lower(), position)
        now = time.time()
        entry = self._announced.get(key)

        if entry is None:
            return True

        if now - entry["last_seen"] < self.config.SPEECH_REPEAT_COOLDOWN:
            return False

        distance_unchanged = abs(distance - entry["distance"]) < self.config.DISTANCE_CHANGE_THRESHOLD
        position_unchanged = entry["position"] == position
        if distance_unchanged and position_unchanged:
            return False

        return True

    def mark_announced(self, class_name: str, position: str, distance: float) -> None:
        """Record that an object was just announced."""
        key = (class_name.lower(), position)
        self._announced[key] = {
            "last_seen": time.time(),
            "distance": distance,
            "position": position,
        }


class DistanceEstimator:
    """Estimates distance to object using trained model with EMA smoothing"""

    def __init__(self, model_path: str = "distance_model.pth"):
        self.model_path = model_path
        self.checkpoint = None
        self.scaler = None
        self.gbr_model = None
        self.rf_model = None
        self.ema_history: Dict[str, float] = {}
        self._load_model()

    def _load_model(self) -> None:
        if not os.path.exists(self.model_path):
            return
        try:
            import torch
            ckpt = torch.load(self.model_path, map_location="cpu", weights_only=False)
            if isinstance(ckpt, dict):
                self.checkpoint = ckpt
                self.scaler = ckpt.get("scaler", None)
                self.gbr_model = ckpt.get("gbr_model", None)
                self.rf_model = ckpt.get("rf_model", None)
                print("[DistanceEstimator] Trained distance model loaded ✓")
        except Exception as err:
            print(f"[DistanceEstimator] Failed to load {self.model_path}: {err}. Using heuristic.")

    def estimate(self, detection: Detection, frame_width: int, frame_height: int) -> float:
        """Estimate distance using trained model or fallback heuristic with EMA smoothing"""
        raw_distance = None

        if (self.gbr_model is not None or self.rf_model is not None) and self.scaler is not None:
            try:
                import numpy as np

                w = float(detection.width)
                h = float(detection.height)
                area = float(detection.area)
                y_center = float(detection.center_y)
                y_bottom = float(detection.center_y + h / 2.0)

                cls_name = detection.class_name.lower().strip()
                from train_distance_model import OBJECT_PHYSICAL_PRIORS
                prior_h = OBJECT_PHYSICAL_PRIORS.get(cls_name, (1.0, 1.0))[0]
                d_optics = 400.0 * prior_h / max(h, 1.0)

                ground_dist_proxy = 100.0 / max(float(frame_height) - y_bottom, 5.0)

                inv_w = 1.0 / max(w, 1.0)
                inv_h = 1.0 / max(h, 1.0)
                inv_sqrt_area = 1.0 / np.sqrt(max(area, 1.0))
                aspect_ratio = w / max(h, 1.0)
                log_area = np.log1p(area)

                numeric = np.array([[
                    w, h, area, y_center, y_bottom, inv_w, inv_h, inv_sqrt_area, aspect_ratio, log_area, ground_dist_proxy, d_optics
                ]], dtype=float)


                X = self.scaler.transform(numeric)

                if self.gbr_model is not None:
                    pred_log = self.gbr_model.predict(X)[0]
                    raw_distance = float(np.clip(np.exp(pred_log), 0.3, 10.0))
                elif self.rf_model is not None:
                    pred_log = self.rf_model.predict(X)[0]
                    raw_distance = float(np.clip(np.exp(pred_log), 0.3, 10.0))
            except Exception as exc:
                pass

        if raw_distance is None:
            frame_area = frame_width * frame_height
            ratio = detection.area / max(frame_area, 1)
            if ratio > 0.20: raw_distance = 0.6
            elif ratio > 0.10: raw_distance = 1.2
            elif ratio > 0.05: raw_distance = 2.0
            elif ratio > 0.02: raw_distance = 3.0
            else: raw_distance = 4.5

        # Apply 5-frame Exponential Moving Average (EMA) smoothing per object class
        cls_key = detection.class_name
        if cls_key in self.ema_history:
            smoothed = 0.7 * raw_distance + 0.3 * self.ema_history[cls_key]
        else:
            smoothed = raw_distance
        self.ema_history[cls_key] = smoothed
        return smoothed




# LLM narration runs in a bounded worker thread; on timeout or error the caller
# falls back to the plain template string so the camera loop never blocks.
class LLMNarrator:
    """Generate a short spoken sentence from detections using Ollama."""

    def __init__(self, config: Config):
        self.config = config

    def generate_description(
        self,
        detections: List[Detection],
        frame_width: int,
        frame_height: int,
        distances: Dict[str, float],
    ) -> Optional[str]:
        """Generate one short natural spoken sentence for confirmed detections."""
        if not detections:
            return None

        sorted_detections = sorted(
            detections,
            key=lambda d: distances.get(d.class_name, float("inf")),
        )
        parts: List[str] = []

        for detection in sorted_detections[:3]:
            distance = distances.get(detection.class_name)
            if distance is None:
                continue
            position, _ = get_position(detection.center_x, frame_width)
            parts.append(
                f"{detection.class_name} at about {distance:.1f} meters on the {position}"
            )

        if not parts:
            return None

        prompt = (
            "You are an AI navigation assistant for a visually impaired user. "
            "Based on these detected objects, reply with ONE short natural spoken sentence. "
            "Prioritize the closest object. Use 15-20 words maximum. "
            "No quotes, labels, or extra text.\n\n"
            f"Objects:\n" + "\n".join(parts) + "\n\n"
            "Sentence:"
        )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    ollama.chat,
                    model=self.config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "num_predict": self.config.LLM_MAX_TOKENS,
                        "temperature": 0.3,
                    },
                )
                response = future.result(timeout=self.config.LLM_TIMEOUT_SECONDS)

            content = getattr(getattr(response, "message", None), "content", None)
            if not content:
                return None

            sentence = content.strip()
            return sentence or None
        except concurrent.futures.TimeoutError:
            print(f"[Main] LLM narration timed out after {self.config.LLM_TIMEOUT_SECONDS}s")
            return None
        except Exception as exc:
            print(f"[Main] LLM narration error: {exc}")
            return None


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
        self.stabilizer = DetectionStabilizer(self.config)
        self.announcer = AnnouncementTracker(self.config)
        self.distance_estimator = DistanceEstimator()
        self.llm_narrator = LLMNarrator(self.config)
        self.llm_available = False

        self.frame_count = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0

    def _log(self, message: str) -> None:
        """Log with timestamp"""
        print(f"[Main] {message}")

    def _speak(self, text: str) -> None:
        """Queue text for speech (non-blocking)"""
        self.speech_queue.put(text)

    def _enqueue_llm_narration(
        self,
        detections: List[Detection],
        frame_width: int,
        frame_height: int,
        distances: Dict[str, float],
        fallback: str,
    ) -> None:
        """Generate LLM narration in the background and enqueue when ready."""
        def worker() -> None:
            message = self.llm_narrator.generate_description(
                detections,
                frame_width,
                frame_height,
                distances,
            )
            if message:
                spoken = f"{self.config.LLM_SPEECH_PREFIX} {message}"
                self._log(f"LLM narration ready: {spoken}")
                self.speech_queue.put(spoken)
            else:
                spoken = f"{self.config.TEMPLATE_SPEECH_PREFIX} {fallback}"
                self._log(f"LLM narration unavailable, using template fallback: {spoken}")
                self.speech_queue.put(spoken)

        threading.Thread(
            target=worker,
            name="LLMNarration",
            daemon=True,
        ).start()

    def initialize(self) -> bool:
        """Initialize the application"""
        self._log("Initializing AI Eye...")

        try:
            self._log(f"Loading YOLO model: {self.config.MODEL_PATH}")
            self.model = YOLO(self.config.MODEL_PATH)
            self._log("YOLO model loaded ✓")
        except Exception as e:
            self._log(f"Failed to load model: {e}")
            return False

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

        self.stop_event.clear()
        self.speech_thread = SpeechWorker(self.speech_queue, self.stop_event)
        self.speech_thread.start()
        self._log("Speech worker started ✓")

        time.sleep(self.config.THREAD_INIT_WAIT)

        if self.config.USE_LLM_NARRATION:
            self.llm_available = ensure_ollama_ready(self.config.LLM_MODEL, self._log)
            if self.llm_available:
                self._warmup_llm()
            else:
                self._log("LLM disabled for this session — using Template fallback.")

        return True

    def _warmup_llm(self) -> None:
        """Load the Ollama model once at startup so later calls respond faster."""
        try:
            self._log(f"Warming up LLM: {self.config.LLM_MODEL}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    ollama.chat,
                    model=self.config.LLM_MODEL,
                    messages=[{"role": "user", "content": "Reply with the word ready."}],
                    options={"num_predict": 5},
                )
                future.result(timeout=self.config.LLM_TIMEOUT_SECONDS)
            self._log("LLM warmup complete ✓")
        except Exception as exc:
            self.llm_available = False
            self._log(f"LLM warmup failed (template fallback will be used): {exc}")

    def detect_objects(self, frame) -> list:
        """Run YOLO detection on frame"""
        results = self.model(
            frame,
            stream=False,
            conf=self.config.CONFIDENCE_THRESHOLD,
            iou=self.config.IOU_THRESHOLD,
        )
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
                    confidence=confidence,
                )
                detections.append(detection)

        return detections

    def process_detections(
        self,
        detections: list,
        frame_width: int,
        frame_height: int,
    ) -> None:
        """Process detections and generate speech announcements."""
        if not detections:
            return

        confirmed = self.stabilizer.update(detections, frame_width)
        if not confirmed:
            return

        best = max(confirmed, key=lambda d: d.area)
        distance = self.distance_estimator.estimate(best, frame_width, frame_height)
        position, guidance = get_position(best.center_x, frame_width)

        if not self.announcer.should_announce(best.class_name, position, distance):
            return

        fallback = f"{best.class_name}, {distance:.1f} meters, {guidance}."
        self.announcer.mark_announced(best.class_name, position, distance)

        if self.config.USE_LLM_NARRATION and self.llm_available:
            distances = {
                detection.class_name: self.distance_estimator.estimate(
                    detection,
                    frame_width,
                    frame_height,
                )
                for detection in confirmed
            }
            self._enqueue_llm_narration(
                confirmed,
                frame_width,
                frame_height,
                distances,
                fallback,
            )
        else:
            spoken = f"{self.config.TEMPLATE_SPEECH_PREFIX} {fallback}"
            self.speech_queue.put(spoken)

    def draw_detections(self, frame, detections: list) -> None:
        """Draw bounding boxes and labels"""
        if not detections:
            cv2.putText(
                frame,
                "No object detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2,
            )
            return

        best_detection = max(detections, key=lambda d: d.area)
        distance = self.distance_estimator.estimate(
            best_detection,
            frame.shape[1],
            frame.shape[0],
        )

        for det in detections:
            x1 = int(det.center_x - det.width / 2)
            y1 = int(det.center_y - det.height / 2)
            x2 = int(det.center_x + det.width / 2)
            y2 = int(det.center_y + det.height / 2)

            color = (0, 255, 0) if det == best_detection else (200, 200, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                f"{det.class_name} {distance:.1f}m",
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

    def draw_ui(self, frame) -> None:
        """Draw UI elements"""
        cv2.putText(
            frame,
            "AI Eye Detection System",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        if self.config.DISPLAY_FPS:
            fps_text = f"FPS: {self.current_fps:.1f}"
            cv2.putText(
                frame,
                fps_text,
                (frame.shape[1] - 150, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        cv2.putText(
            frame,
            "Press 'Q' to quit",
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
        )

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
        detections: List[Detection] = []

        try:
            while True:
                success, frame = self.cap.read()
                if not success:
                    self._log("Failed to read frame")
                    break

                height, width = frame.shape[:2]
                now = time.time()

                if now - last_inference_time >= self.config.INFERENCE_INTERVAL:
                    detections = self.detect_objects(frame)
                    self.process_detections(detections, width, height)
                    last_inference_time = now

                if detections:
                    self.draw_detections(frame, detections)
                self.draw_ui(frame)

                cv2.imshow(self.config.WINDOW_NAME, frame)
                self.update_fps()

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
