"""
AI Eye — real-time object detection with voice guidance
Designed to help visually impaired users navigate their surroundings.

How it works:
  1. Captures video from a webcam.
  2. Runs YOLOv8 on each frame to detect objects.
  3. Stabilizes detections across a few frames so random flickers don't trigger speech.
  4. Sends confirmed detections to a small local LLM (via Ollama) that writes a
     natural spoken sentence, e.g. "A person is approaching on your right side."
  5. Speaks the sentence aloud through Windows TTS.
  6. Falls back to a plain template sentence if the LLM is too slow or unavailable.

Requirements:
  pip install ultralytics opencv-python ollama pyttsx3 pywin32
  Ollama installed with:  ollama pull qwen2.5:0.5b
"""

import os
import time
import threading
import subprocess
import concurrent.futures
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Dict, List, Optional, Tuple

import cv2
import ollama
from ultralytics import YOLO


# ---------------------------------------------------------------------------
# Settings — change these to tweak behaviour without touching the rest
# ---------------------------------------------------------------------------

@dataclass
class Config:
    # Camera & model
    model_path:          str   = "yolov8n.pt"
    camera_index:        int   = 0

    # Detection
    confidence:          float = 0.35   # minimum YOLO confidence to keep a box
    iou_threshold:       float = 0.45   # overlap threshold for NMS
    inference_fps:       float = 10.0   # how many times per second we run YOLO
    stable_frames:       int   = 3      # frames an object must appear before we announce it

    # Voice
    speech_rate:         int   = 160    # words per minute
    repeat_cooldown:     float = 2.5    # seconds before we'll say the same thing again
    distance_threshold:  float = 0.4    # metres of change needed to re-announce

    # LLM
    use_llm:             bool  = True
    llm_model:           str   = "qwen2.5:0.5b"
    llm_timeout:         float = 12.0   # seconds to wait for a response
    llm_max_tokens:      int   = 35

    # UI
    window_title:        str   = "AI Eye"
    show_fps:            bool  = True

    # Internal
    speech_join_timeout: float = 3.0
    startup_wait:        float = 1.0    # give the speech thread a moment to start up

    @property
    def inference_interval(self) -> float:
        return 1.0 / max(self.inference_fps, 1.0)


# ---------------------------------------------------------------------------
# Optional libraries — graceful degradation if not installed
# ---------------------------------------------------------------------------

try:
    import pyttsx3
    _PYTTSX3 = True
except ImportError:
    _PYTTSX3 = False

try:
    import win32com.client as _wincl
    _WINCL = True
except Exception:
    _wincl = None
    _WINCL = False


# ---------------------------------------------------------------------------
# Ollama helpers — auto-start the server and pull the model if needed
# ---------------------------------------------------------------------------

_OLLAMA_PATHS = (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
    os.path.join(os.environ.get("ProgramFiles",  ""), "Ollama", "ollama.exe"),
)


def _ollama_running() -> bool:
    try:
        ollama.list()
        return True
    except Exception:
        return False


def _start_ollama() -> bool:
    """Try to launch the Ollama server silently in the background."""
    exe = next((p for p in _OLLAMA_PATHS if p and os.path.isfile(p)), None)
    if not exe:
        return False
    try:
        subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return False

    # Poll for up to 10 seconds
    for _ in range(20):
        if _ollama_running():
            return True
        time.sleep(0.5)
    return False


def ensure_ollama(model: str, log) -> bool:
    """Make sure Ollama is running and the model is downloaded."""
    if not _ollama_running():
        log("Ollama not running — trying to start it automatically...")
        if not _start_ollama():
            log("Could not start Ollama. Install it from https://ollama.com and run:")
            log(f"  ollama pull {model}")
            return False
        log("Ollama started ✓")

    try:
        available = {m.model.split(":")[0] for m in ollama.list().models}
        if model.split(":")[0] not in available:
            log(f"Downloading model: {model}  (this only happens once)")
            ollama.pull(model)
        return True
    except Exception as err:
        log(f"Ollama model check failed: {err}")
        return False


# ---------------------------------------------------------------------------
# Text-to-speech — tries three methods in order of reliability
# ---------------------------------------------------------------------------

class Speaker:
    """Wraps Windows TTS so the rest of the code doesn't care about the details."""

    def __init__(self, rate: int = 160):
        self.rate = rate

    def say(self, text: str) -> bool:
        return (
            self._sapi(text)
            or self._powershell(text)
            or self._pyttsx3(text)
        )

    def _sapi(self, text: str) -> bool:
        if not _WINCL:
            return False
        try:
            voice = _wincl.Dispatch("SAPI.SpVoice")
            voice.Speak(text)
            return True
        except Exception:
            return False

    def _powershell(self, text: str) -> bool:
        script = (
            "[System.Reflection.Assembly]::LoadWithPartialName('System.Speech') | Out-Null\n"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
            f'$s.Speak("{text}")'
        )
        try:
            subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                timeout=10,
            )
            return True
        except Exception:
            return False

    def _pyttsx3(self, text: str) -> bool:
        if not _PYTTSX3:
            return False
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", self.rate)
            voices = engine.getProperty("voices")
            if voices:
                engine.setProperty("voice", voices[0].id)
            engine.say(text)
            engine.runAndWait()
            return True
        except Exception:
            return False


class SpeechThread(threading.Thread):
    """Dedicated thread that drains a queue and speaks each item in order."""

    def __init__(self, queue: Queue, stop: threading.Event, rate: int):
        super().__init__(name="SpeechThread", daemon=False)
        self.queue = queue
        self.stop = stop
        self.speaker = Speaker(rate)

    def run(self):
        print("[voice] ready")
        while not self.stop.is_set():
            try:
                text = self.queue.get(timeout=0.5)
                if text is None:   # sentinel — time to quit
                    break
                ok = self.speaker.say(text)
                print(f"[voice] {'✓' if ok else '✗'} {text}")
            except Empty:
                continue
            except Exception as err:
                print(f"[voice] error: {err}")
                break
        print("[voice] stopped")


# ---------------------------------------------------------------------------
# Detection data model
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    label:      str
    cx:         float   # centre-x in pixels
    cy:         float   # centre-y in pixels
    w:          float   # bounding box width
    h:          float   # bounding box height
    confidence: float

    @property
    def area(self) -> float:
        return self.w * self.h


# ---------------------------------------------------------------------------
# Position helpers
# ---------------------------------------------------------------------------

def position_of(cx: float, frame_w: int) -> Tuple[str, str]:
    """Return (side, navigation_hint) based on where the object sits in frame."""
    if cx < frame_w * 0.35:
        return "left", "move right"
    if cx > frame_w * 0.65:
        return "right", "move left"
    return "center", "stay on course"


def tracking_key(label: str, cx: float, frame_w: int) -> Tuple[str, str]:
    side, _ = position_of(cx, frame_w)
    return label.lower(), side


# ---------------------------------------------------------------------------
# Stabilizer — only surface objects seen across several consecutive frames
# ---------------------------------------------------------------------------

class Stabilizer:
    """
    Filters out single-frame ghost detections.
    An object has to appear in `min_frames` consecutive frames before we treat it
    as real and pass it on to the announcement logic.
    """

    def __init__(self, min_frames: int):
        self.min_frames = min_frames
        self._counts:  Dict[Tuple[str, str], int] = {}
        self._objects: Dict[Tuple[str, str], Detection] = {}

    def update(self, detections: List[Detection], frame_w: int) -> List[Detection]:
        seen = set()
        confirmed = []

        for det in detections:
            key = tracking_key(det.label, det.cx, frame_w)
            seen.add(key)
            self._counts[key] = self._counts.get(key, 0) + 1
            self._objects[key] = det
            if self._counts[key] >= self.min_frames:
                confirmed.append(det)

        # Remove objects that disappeared this frame
        for key in list(self._counts):
            if key not in seen:
                del self._counts[key]
                self._objects.pop(key, None)

        return confirmed


# ---------------------------------------------------------------------------
# Cooldown tracker — avoids repeating the same announcement endlessly
# ---------------------------------------------------------------------------

class AnnouncementLog:
    """Remembers what we last said about each object so we don't repeat ourselves."""

    def __init__(self, cooldown: float, distance_threshold: float):
        self.cooldown = cooldown
        self.distance_threshold = distance_threshold
        self._log: Dict[Tuple[str, str], dict] = {}

    def should_speak(self, label: str, side: str, dist: float) -> bool:
        key = (label.lower(), side)
        entry = self._log.get(key)

        if entry is None:
            return True  # never seen before

        if time.time() - entry["t"] < self.cooldown:
            return False  # too soon

        # Re-announce if the object moved noticeably closer or farther away
        if abs(dist - entry["dist"]) >= self.distance_threshold:
            return True

        # Or if it switched sides (left / center / right)
        if entry["side"] != side:
            return True

        return False

    def record(self, label: str, side: str, dist: float):
        self._log[(label.lower(), side)] = {"t": time.time(), "dist": dist, "side": side}


# ---------------------------------------------------------------------------
# Distance estimation (rough heuristic until the real depth model is ready)
# ---------------------------------------------------------------------------

def estimate_distance(det: Detection, frame_w: int, frame_h: int) -> float:
    ratio = det.area / max(frame_w * frame_h, 1)
    if ratio > 0.20: return 0.6
    if ratio > 0.10: return 1.2
    if ratio > 0.05: return 2.0
    if ratio > 0.02: return 3.0
    return 4.5


# ---------------------------------------------------------------------------
# LLM narrator — turns detection data into a natural spoken sentence
# ---------------------------------------------------------------------------

class Narrator:
    """
    Asks a local LLM to write one short sentence describing what's in front of the user.
    The call runs in a thread with a hard timeout so it never blocks the camera loop.
    If it times out or fails, the caller should fall back to a plain template string.
    """

    def __init__(self, model: str, timeout: float, max_tokens: int):
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def describe(
        self,
        detections: List[Detection],
        distances: Dict[str, float],
        frame_w: int,
    ) -> Optional[str]:

        if not detections:
            return None

        # Build a short fact list sorted by distance (closest first)
        sorted_dets = sorted(detections, key=lambda d: distances.get(d.label, 99))
        facts = []
        for det in sorted_dets[:3]:
            dist = distances.get(det.label)
            if dist is None:
                continue
            side, _ = position_of(det.cx, frame_w)
            facts.append(f"{det.label}, {dist:.1f} m, on the {side}")

        if not facts:
            return None

        prompt = (
            "You are a navigation assistant for a blind person. "
            "Write ONE short spoken sentence (max 20 words) describing what is ahead. "
            "Mention the closest object first. No punctuation tricks, no quotes, no labels.\n\n"
            "Scene:\n" + "\n".join(facts) + "\n\nSentence:"
        )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    ollama.chat,
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"num_predict": self.max_tokens, "temperature": 0.3},
                )
                response = future.result(timeout=self.timeout)

            text = getattr(getattr(response, "message", None), "content", None)
            return text.strip() if text else None

        except concurrent.futures.TimeoutError:
            print(f"[llm] timed out after {self.timeout}s")
            return None
        except Exception as err:
            print(f"[llm] error: {err}")
            return None


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class AIEye:

    def __init__(self, cfg: Config = None):
        self.cfg = cfg or Config()

        # Core components (set up in initialize())
        self.model:    Optional[YOLO] = None
        self.cap:      Optional[cv2.VideoCapture] = None

        # Speech pipeline
        self.speech_queue  = Queue()
        self._stop         = threading.Event()
        self.speech_thread: Optional[SpeechThread] = None

        # Detection helpers
        self.stabilizer  = Stabilizer(self.cfg.stable_frames)
        self.log         = AnnouncementLog(self.cfg.repeat_cooldown, self.cfg.distance_threshold)
        self.narrator    = Narrator(self.cfg.llm_model, self.cfg.llm_timeout, self.cfg.llm_max_tokens)
        self.llm_ready   = False

        # FPS counter
        self._fps_frames = 0
        self._fps_t      = time.time()
        self.fps         = 0.0

    # ------------------------------------------------------------------
    # Logging shorthand
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        print(f"[main] {msg}")

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        self._log("Starting up AI Eye...")

        # Load YOLO
        try:
            self._log(f"Loading detection model: {self.cfg.model_path}")
            self.model = YOLO(self.cfg.model_path)
            self._log("Model ready ✓")
        except Exception as err:
            self._log(f"Could not load model: {err}")
            return False

        # Open camera
        try:
            self._log(f"Opening camera #{self.cfg.camera_index}")
            self.cap = cv2.VideoCapture(self.cfg.camera_index)
            if not self.cap.isOpened():
                self._log("Camera not found. Plug in a webcam and try again.")
                return False
            self._log("Camera ready ✓")
        except Exception as err:
            self._log(f"Camera error: {err}")
            return False

        # Start speech thread
        self._stop.clear()
        self.speech_thread = SpeechThread(self.speech_queue, self._stop, self.cfg.speech_rate)
        self.speech_thread.start()
        time.sleep(self.cfg.startup_wait)   # let it warm up
        self._log("Voice ready ✓")

        # Connect to Ollama if LLM narration is on
        if self.cfg.use_llm:
            self.llm_ready = ensure_ollama(self.cfg.llm_model, self._log)
            if self.llm_ready:
                self._warmup_llm()
            else:
                self._log("LLM unavailable — will use plain template messages instead.")

        return True

    def _warmup_llm(self):
        """Send a tiny request at startup so the model is already loaded when we need it."""
        self._log(f"Warming up {self.cfg.llm_model}...")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                f = pool.submit(
                    ollama.chat,
                    model=self.cfg.llm_model,
                    messages=[{"role": "user", "content": "Say the word: ready"}],
                    options={"num_predict": 3},
                )
                f.result(timeout=self.cfg.llm_timeout)
            self._log("LLM warm ✓")
        except Exception as err:
            self.llm_ready = False
            self._log(f"LLM warmup failed ({err}) — switching to template mode.")

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, frame) -> List[Detection]:
        results = self.model(
            frame,
            stream=False,
            conf=self.cfg.confidence,
            iou=self.cfg.iou_threshold,
            verbose=False,
        )
        detections = []
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for box in boxes:
            conf = float(box.conf[0])
            if conf < self.cfg.confidence:
                continue
            cls  = int(box.cls[0])
            name = self.model.names[cls]
            cx, cy, w, h = box.xywh[0].tolist()
            detections.append(Detection(name, cx, cy, w, h, conf))

        return detections

    # ------------------------------------------------------------------
    # Announcement logic
    # ------------------------------------------------------------------

    def maybe_announce(self, confirmed: List[Detection], frame_w: int, frame_h: int):
        if not confirmed:
            return

        # Focus on the largest (closest-looking) object
        best  = max(confirmed, key=lambda d: d.area)
        dist  = estimate_distance(best, frame_w, frame_h)
        side, hint = position_of(best.cx, frame_w)

        if not self.log.should_speak(best.label, side, dist):
            return

        # Build the plain fallback message now so we always have something to say
        fallback = f"{best.label}, {dist:.1f} metres, {hint}."
        self.log.record(best.label, side, dist)

        if self.cfg.use_llm and self.llm_ready:
            # Fire off LLM call in a daemon thread — camera loop keeps running
            distances = {
                d.label: estimate_distance(d, frame_w, frame_h)
                for d in confirmed
            }
            threading.Thread(
                target=self._llm_then_speak,
                args=(confirmed, distances, frame_w, fallback),
                daemon=True,
            ).start()
        else:
            self.speech_queue.put(fallback)

    def _llm_then_speak(
        self,
        detections: List[Detection],
        distances: Dict[str, float],
        frame_w: int,
        fallback: str,
    ):
        sentence = self.narrator.describe(detections, distances, frame_w)
        self.speech_queue.put(sentence if sentence else fallback)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, frame, detections: List[Detection], frame_w: int, frame_h: int):
        if not detections:
            cv2.putText(frame, "Nothing detected", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (60, 60, 255), 2)
            return

        best = max(detections, key=lambda d: d.area)
        dist = estimate_distance(best, frame_w, frame_h)

        for det in detections:
            x1 = int(det.cx - det.w / 2)
            y1 = int(det.cy - det.h / 2)
            x2 = int(det.cx + det.w / 2)
            y2 = int(det.cy + det.h / 2)
            color = (0, 220, 0) if det is best else (180, 180, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label_text = f"{det.label}  {dist:.1f}m" if det is best else det.label
            cv2.putText(frame, label_text, (x1, max(18, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def draw_hud(self, frame):
        h, w = frame.shape[:2]
        cv2.putText(frame, "AI Eye", (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if self.cfg.show_fps:
            cv2.putText(frame, f"{self.fps:.0f} fps", (w - 100, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2)
        cv2.putText(frame, "Q — quit", (12, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    def _tick_fps(self):
        self._fps_frames += 1
        elapsed = time.time() - self._fps_t
        if elapsed >= 1.0:
            self.fps = self._fps_frames / elapsed
            self._fps_frames = 0
            self._fps_t = time.time()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        if not self.initialize():
            return

        self._log("Detection loop running — press Q in the video window to quit.")
        last_inference = 0.0
        detections: List[Detection] = []

        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    self._log("Lost camera feed.")
                    break

                h, w = frame.shape[:2]
                now = time.time()

                # Run YOLO at the configured rate (not every single frame)
                if now - last_inference >= self.cfg.inference_interval:
                    raw         = self.detect(frame)
                    confirmed   = self.stabilizer.update(raw, w)
                    self.maybe_announce(confirmed, w, h)
                    detections  = raw          # draw raw boxes (less laggy feel)
                    last_inference = now

                self.draw(frame, detections, w, h)
                self.draw_hud(frame)
                self._tick_fps()

                cv2.imshow(self.cfg.window_title, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        except KeyboardInterrupt:
            pass
        except Exception as err:
            self._log(f"Unexpected error: {err}")
        finally:
            self.shutdown()

    # ------------------------------------------------------------------
    # Clean shutdown
    # ------------------------------------------------------------------

    def shutdown(self):
        self._log("Shutting down...")
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

        # Signal the speech thread to finish and wait for it
        self._stop.set()
        self.speech_queue.put(None)
        if self.speech_thread:
            self.speech_thread.join(timeout=self.cfg.speech_join_timeout)

        self._log("Done.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    AIEye().run()
