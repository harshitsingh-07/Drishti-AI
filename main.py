import time
from typing import Dict, Tuple

import cv2
import pyttsx3
from ultralytics import YOLO


try:
    import win32com.client as wincl
except Exception:
    wincl = None


def estimate_distance_from_box(width: float, height: float, frame_width: int, frame_height: int) -> float:
    """Temporary heuristic for distance. This is intentionally simple and will be replaced later by the custom trained model."""
    frame_area = frame_width * frame_height
    box_area = width * height
    ratio = box_area / max(frame_area, 1)

    if ratio > 0.20:
        return 0.6
    if ratio > 0.10:
        return 1.2
    if ratio > 0.05:
        return 2.0
    if ratio > 0.02:
        return 3.0
    return 4.5


def get_direction(center_x: float, frame_width: int) -> Tuple[str, str]:
    """Classify the object position and return a direction hint."""
    if center_x < frame_width * 0.35:
        return "left", "move right"
    if center_x > frame_width * 0.65:
        return "right", "move left"
    return "center", "stay centered"


def build_object_key(class_name: str, center_x: float, frame_width: int) -> Tuple[str, str]:
    if center_x < frame_width * 0.35:
        region = "left"
    elif center_x > frame_width * 0.65:
        region = "right"
    else:
        region = "center"
    return class_name.lower(), region


def speak(engine: pyttsx3.Engine, text: str) -> None:
    print(f"Speaking: {text}")
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as exc:
        print(f"Speech failed with pyttsx3: {exc}")

    if wincl is not None:
        try:
            speaker = wincl.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except Exception as exc:
            print(f"Windows speech fallback failed: {exc}")


def run_camera_demo(model_path: str = "yolov8n.pt", camera_index: int = 0) -> None:
    model = YOLO(model_path)
    engine = pyttsx3.init("sapi5")
    engine.setProperty("rate", 160)
    voices = engine.getProperty("voices")
    if voices:
        engine.setProperty("voice", voices[0].id)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Camera could not be opened. Please connect a webcam and try again.")
        return

    last_announced: Dict[Tuple[str, str], Dict[str, float]] = {}
    last_inference_time = 0.0
    inference_interval = 0.5
    last_boxes = []
    last_distance = None

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from camera.")
            break

        height, width = frame.shape[:2]
        now = time.time()
        do_inference = now - last_inference_time >= inference_interval

        detections = last_boxes
        if do_inference:
            results = model(frame, stream=False, conf=0.35)
            result = results[0]
            last_inference_time = now
            detections = []
            if result is not None and result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    confidence = float(box.conf[0])
                    if confidence < 0.35:
                        continue
                    class_id = int(box.cls[0])
                    class_name = model.names[class_id]
                    x_center, y_center, box_width, box_height = box.xywh[0].tolist()
                    detections.append((class_name, x_center, box_width, box_height))
            last_boxes = detections

        if detections:
            detections.sort(key=lambda item: item[2] * item[3], reverse=True)
            best_class, best_x, best_width, best_height = detections[0]
            distance = estimate_distance_from_box(best_width, best_height, width, height)
            position, guidance = get_direction(best_x, width)

            object_key = build_object_key(best_class, best_x, width)
            now = time.time()
            entry = last_announced.get(object_key)
            should_speak = True
            if entry is not None:
                if now - entry["last_seen"] < 2.5:
                    should_speak = False
                elif abs(distance - entry["last_distance"]) < 0.4 and entry.get("last_position") == position:
                    should_speak = False

            if should_speak:
                message = f"{best_class}, {distance:.1f} meters, {guidance}."
                speak(engine, message)
                last_announced[object_key] = {
                    "last_seen": now,
                    "last_distance": distance,
                    "last_position": position,
                    "class_name": best_class.lower(),
                }

            for class_name, x_center, box_width, box_height in detections:
                x1 = int(x_center - box_width / 2)
                y1 = int(0)
                x2 = int(x_center + box_width / 2)
                y2 = int(y1 + box_height)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{class_name} {distance:.1f}m", (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        else:
            cv2.putText(frame, "No object detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        cv2.putText(frame, "AI Eye Demo", (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("AI Eye Demo", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    engine.stop()


if __name__ == "__main__":
    run_camera_demo()
