from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import base64
import io
import sys
import subprocess
import threading
import time
from typing import Dict, List, Optional
from queue import Queue, Empty
import numpy as np
import concurrent.futures
from PIL import Image
from ultralytics import YOLO

FRONTEND_DIR = os.path.abspath(os.path.join(ROOT_DIR, "frontend-dist"))
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
MODEL_PATH = os.path.abspath(os.path.join(ROOT_DIR, "yolov8n.pt"))
DISTANCE_MODEL_PATH = os.path.abspath(os.path.join(ROOT_DIR, "distance_model.pth"))

try:
    MODEL = YOLO(MODEL_PATH)
    MODEL_ERROR = None
except Exception as exc:
    MODEL = None
    MODEL_ERROR = str(exc)

try:
    import torch
    from train_distance_model import OBJECT_PHYSICAL_PRIORS

    DISTANCE_MODEL = None
    DISTANCE_SCALER = None
    DISTANCE_GBR_MODEL = None
    DISTANCE_RF_MODEL = None
    DISTANCE_MODEL_ERROR = None

    if os.path.exists(DISTANCE_MODEL_PATH):
        checkpoint = torch.load(DISTANCE_MODEL_PATH, map_location="cpu", weights_only=False)
        if isinstance(checkpoint, dict):
            DISTANCE_MODEL = checkpoint
            DISTANCE_SCALER = checkpoint.get("scaler")
            DISTANCE_GBR_MODEL = checkpoint.get("gbr_model")
            DISTANCE_RF_MODEL = checkpoint.get("rf_model")
    else:
        DISTANCE_MODEL_ERROR = "distance_model.pth not found"
except Exception as exc:
    print(f"[Model Load Error] {exc}")
    DISTANCE_MODEL = None
    DISTANCE_SCALER = None
    DISTANCE_GBR_MODEL = None
    DISTANCE_RF_MODEL = None
    DISTANCE_MODEL_ERROR = str(exc)

EMA_HISTORY: Dict[str, float] = {}


def create_navigation_message(detections, frame_width):
    if not detections:
        return "No important obstacle detected."

    def extract_distance(item):
        val = item.get("distance", "999")
        if isinstance(val, str):
            val = val.replace(' m', '').replace('m', '')
        try:
            return float(val)
        except ValueError:
            return 999.0

    nearest = min(detections, key=extract_distance)

    label = nearest.get("label", "object")
    distance = extract_distance(nearest)

    bbox = nearest.get("bbox", {})
    center_x = bbox.get("x", frame_width / 2) + bbox.get("width", 0) / 2
    relative_position = center_x / max(frame_width, 1)

    if relative_position < 0.33:
        position = "on your left"
    elif relative_position > 0.66:
        position = "on your right"
    else:
        position = "ahead"

    if distance <= 1:
        warning = "Warning. "
    elif distance <= 2:
        warning = "Caution. "
    else:
        warning = ""

    return (
        f"{warning}{label} {position}, "
        f"approximately {distance} metres away."
    )

class AnnouncementTracker:
    def __init__(self, cooldown: float = 3.0, distance_threshold: float = 0.4):
        self.cooldown = cooldown
        self.distance_threshold = distance_threshold
        self._log: Dict[str, dict] = {}

    def should_announce(self, class_name: str, distance_str: str, side: str) -> bool:
        try:
            dist = float(distance_str.replace("m", "").strip())
        except Exception:
            dist = 0.0

        key = class_name.lower()
        entry = self._log.get(key)
        now = time.time()

        if entry is None:
            return True

        if now - entry["t"] < self.cooldown:
            return False

        if abs(dist - entry["dist"]) >= self.distance_threshold:
            return True

        if entry["side"] != side:
            return True

        return False

    def mark_announced(self, class_name: str, distance_str: str, side: str) -> None:
        try:
            dist = float(distance_str.replace("m", "").strip())
        except Exception:
            dist = 0.0
        self._log[class_name.lower()] = {"t": time.time(), "dist": dist, "side": side}

    def clear_active(self) -> None:
        self._log.clear()

ANNOUNCEMENT_TRACKER = AnnouncementTracker()


class DetectionStabilizer:
    def __init__(self, min_frames: int = 2, stale_timeout: float = 1.2):
        self.min_frames = min_frames
        self.stale_timeout = stale_timeout
        self.last_good_detections: List[Dict] = []
        self.last_good_time = 0.0
        self._counts: Dict[str, int] = {}
        self._last_seen: Dict[str, float] = {}

    def update(self, detections: List[Dict]) -> tuple[List[Dict], bool]:
        now = time.time()
        seen = set()
        confirmed = []

        for det in detections:
            key = det.get("label", "object").lower()
            seen.add(key)
            self._counts[key] = self._counts.get(key, 0) + 1
            self._last_seen[key] = now
            if self._counts[key] >= self.min_frames:
                confirmed.append(det)

        for key in list(self._counts.keys()):
            if now - self._last_seen.get(key, 0) > self.stale_timeout:
                del self._counts[key]
                if key in self._last_seen:
                    del self._last_seen[key]

        if confirmed:
            self.last_good_detections = confirmed
            self.last_good_time = now
            return confirmed, False

        if self.last_good_detections and (now - self.last_good_time) < self.stale_timeout:
            return self.last_good_detections, True

        return [], False


DETECTION_STABILIZER = DetectionStabilizer()


def estimate_distance(class_name: str, width: float, height: float, frame_width: int, frame_height: int, y_center_px: float) -> str:
    class_key = class_name.lower().strip()
    cls_name = class_key
    if DISTANCE_SCALER is not None and (DISTANCE_GBR_MODEL is not None or DISTANCE_RF_MODEL is not None):
        try:
            area = float(width * height)
            y_center = float(y_center_px)
            y_bottom = float(y_center_px + height / 2.0)
            prior_h = OBJECT_PHYSICAL_PRIORS.get(cls_name, (1.0, 1.0))[0]
            d_optics = 400.0 * prior_h / max(height, 1.0)
            ground_dist_proxy = 100.0 / max(float(frame_height) - y_bottom, 5.0)
            inv_w = 1.0 / max(width, 1.0)
            inv_h = 1.0 / max(height, 1.0)
            inv_sqrt_area = 1.0 / np.sqrt(max(area, 1.0))
            aspect_ratio = width / max(height, 1.0)
            log_area = np.log1p(area)
            numeric = np.array([[
                width,
                height,
                area,
                y_center,
                y_bottom,
                inv_w,
                inv_h,
                inv_sqrt_area,
                aspect_ratio,
                log_area,
                ground_dist_proxy,
                d_optics,
            ]], dtype=float)
            X = DISTANCE_SCALER.transform(numeric)
            if DISTANCE_GBR_MODEL is not None:
                pred_log = DISTANCE_GBR_MODEL.predict(X)[0]
                raw_distance = float(np.clip(np.exp(pred_log), 0.3, 10.0))
            else:
                pred_log = DISTANCE_RF_MODEL.predict(X)[0]
                raw_distance = float(np.clip(np.exp(pred_log), 0.3, 10.0))
        except Exception as exc:
            print(f"[Distance Calc Error] {exc}")
            raw_distance = None
    else:
        raw_distance = None

    if raw_distance is None:
        frame_area = max(frame_width * frame_height, 1)
        ratio = (width * height) / frame_area
        if ratio > 0.20:
            raw_distance = 0.6
        elif ratio > 0.10:
            raw_distance = 1.2
        elif ratio > 0.05:
            raw_distance = 2.0
        elif ratio > 0.02:
            raw_distance = 3.0
        else:
            raw_distance = 4.5

    if class_key in EMA_HISTORY:
        smoothed = 0.7 * raw_distance + 0.3 * EMA_HISTORY[class_key]
    else:
        smoothed = raw_distance
    EMA_HISTORY[class_key] = smoothed
    return f"{smoothed:.1f} m"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL,
            age TEXT,
            gender TEXT,
            contact_no TEXT,
            email TEXT,
            address TEXT,
            visual_impairment_type TEXT,
            assistance_preference TEXT,
            preferred_language TEXT,
            emergency_contact_name TEXT,
            emergency_contact_no TEXT,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS detection_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            confidence REAL,
            distance TEXT,
            bbox_x INTEGER,
            bbox_y INTEGER,
            bbox_width INTEGER,
            bbox_height INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "AI Eye backend is running"})


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, password),
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({
        "id": user['id'],
        "email": user['email'],
        "username": user['username'],
        "fullName": user['full_name'],
        "token": "stub_token"
    })


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get('fullName') or '').strip()
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not full_name or not username or not email or not password:
        return jsonify({"message": "Full name, username, email and password are required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"message": "User already exists"}), 409

    conn.execute(
        """
        INSERT INTO users (
            full_name, username, age, gender, contact_no, email, address,
            visual_impairment_type, assistance_preference, preferred_language,
            emergency_contact_name, emergency_contact_no, password
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            full_name,
            username,
            data.get('age'),
            data.get('gender'),
            data.get('contactNo'),
            email,
            data.get('address'),
            data.get('visualImpairmentType'),
            data.get('assistancePreference'),
            data.get('preferredLanguage'),
            data.get('emergencyContactName'),
            data.get('emergencyContactNo'),
            password,
        ),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "id": None,
        "email": email,
        "username": username,
        "fullName": full_name,
        "token": "stub_token"
    })


@app.route('/api/detect', methods=['POST'])
def detect():
    try:
        data = request.get_json(silent=True) or {}
        image_b64 = data.get('image')
        if not image_b64:
            return jsonify({"message": "No image provided"}), 400

        image_data = base64.b64decode(image_b64.split(',')[-1])
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        width, height = image.size
        frame_area = width * height

        if MODEL is None:
            return jsonify({
                "message": "Model unavailable",
                "error": MODEL_ERROR,
                "detections": [],
            }), 500

        results = MODEL.predict(
            source=image,
            imgsz=416,
            conf=0.45,
            device="cpu",
            verbose=False
        )
        detections = []
        if results and getattr(results[0], 'boxes', None) is not None:
            for box in results[0].boxes:
                confidence = float(box.conf[0])
                if confidence < 0.45:
                    continue
                class_id = int(box.cls[0])
                class_name = MODEL.names.get(class_id, 'object')
                x_center, y_center, box_width, box_height = box.xywh[0].tolist()
                bbox = {
                    "x": int(x_center - box_width / 2),
                    "y": int(y_center - box_height / 2),
                    "width": int(box_width),
                    "height": int(box_height),
                }
                detections.append({
                    "label": class_name,
                    "confidence": round(confidence, 2),
                    "distance": estimate_distance(class_name, box_width, box_height, width, height, y_center),
                    "bbox": bbox,
                })

        stable_detections, stale_frame = DETECTION_STABILIZER.update(detections)

        if stable_detections:
            best_det = stable_detections[0]
            narration = create_navigation_message(stable_detections, width)
            bbox = best_det.get("bbox", {})
            center_x = bbox.get("x", 0) + bbox.get("width", 0) / 2
            if center_x < width * 0.40:
                side = "left"
            elif center_x > width * 0.60:
                side = "right"
            else:
                side = "center"

            should_speak = ANNOUNCEMENT_TRACKER.should_announce(best_det["label"], best_det["distance"], side)
            if should_speak:
                ANNOUNCEMENT_TRACKER.mark_announced(best_det["label"], best_det["distance"], side)
                print(f"[Detect] Narration generated: {narration}")
            else:
                print(f"[Detect] Suppressed speech for {best_det['label']} at {best_det['distance']}")
        else:
            narration = "No object detected"
            ANNOUNCEMENT_TRACKER.clear_active()

        # Save detection results to the database for later review
        if stable_detections:
            db_conn = get_db()
            for det in detections:
                bbox = det.get("bbox", {})
                db_conn.execute(
                    "INSERT INTO detection_results (label, confidence, distance, bbox_x, bbox_y, bbox_width, bbox_height) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        det.get("label"),
                        det.get("confidence"),
                        det.get("distance"),
                        bbox.get("x"),
                        bbox.get("y"),
                        bbox.get("width"),
                        bbox.get("height"),
                    ),
                )
            db_conn.commit()
            db_conn.close()

        return jsonify({
            "message": "Detection received",
            "detections": stable_detections,
            "narration": narration,
            "stale": stale_frame,
        })
    except Exception as exc:
        return jsonify({"message": f"Detection failed: {exc}"}), 500


@app.route('/api/detections', methods=['GET'])
def get_detections():
    conn = get_db()
    rows = conn.execute("SELECT * FROM detection_results ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route('/api/detections', methods=['DELETE'])
def clear_detections():
    conn = get_db()
    conn.execute("DELETE FROM detection_results")
    conn.commit()
    conn.close()
    return jsonify({"message": "All detection results cleared."})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    requested_file = os.path.join(FRONTEND_DIR, path)

    if path and os.path.isfile(requested_file):
        return send_from_directory(FRONTEND_DIR, path)

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "7860"))
    app.run(host="0.0.0.0", port=port, debug=False)
