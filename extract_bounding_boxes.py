import argparse
import csv
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
from ultralytics import YOLO

from dataset_utils import parse_filename


def detect_object_bbox(image_path: str | Path, model: YOLO, target_class: Optional[str] = None) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[str]]:
    """Run YOLO on a single image and return width, height, area, y_center, y_bottom and class name."""
    results = model(str(image_path), stream=False, conf=0.25)
    result = results[0]

    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return None, None, None, None, None, None

    model_names = model.names
    best_box = None
    best_score = -1.0

    for box in boxes:
        confidence = float(box.conf[0])
        class_id = int(box.cls[0])
        class_name = model_names[class_id].lower()

        if target_class is not None:
            target_name = target_class.lower()
            if class_name == target_name:
                if confidence > best_score:
                    best_score = confidence
                    best_box = box
            continue

        if confidence > best_score:
            best_score = confidence
            best_box = box

    if best_box is None and target_class is not None:
        for box in boxes:
            confidence = float(box.conf[0])
            if confidence > best_score:
                best_score = confidence
                best_box = box

    if best_box is None:
        return None, None, None, None, None, None

    x_center, y_center, width, height = best_box.xywh[0].tolist()
    width = float(width)
    height = float(height)
    y_center = float(y_center)
    y_bottom = float(y_center + height / 2.0)
    area = width * height
    class_name = model_names[int(best_box.cls[0])]
    return width, height, area, y_center, y_bottom, class_name


def build_dataset(input_dir: str | Path, output_csv: str | Path, model_path: str = "yolov8n.pt") -> None:
    """Create a CSV dataset from a folder of labelled images."""
    input_dir = Path(input_dir)
    output_csv = Path(output_csv)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    model = YOLO(model_path)

    image_files = sorted(input_dir.glob("*"))
    image_files = [path for path in image_files if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}]

    if not image_files:
        print(f"No image files found in {input_dir}. Add images such as chair_1m_01.jpg and make sure they are JPG/PNG files.")
        return

    rows: List[dict] = []
    for image_path in image_files:
        object_name, distance = parse_filename(image_path)
        if object_name is None or distance is None:
            print(f"Skipped {image_path.name}: filename does not match the expected pattern")
            continue

        width, height, area, y_center, y_bottom, class_name = detect_object_bbox(image_path, model, target_class=object_name)
        if width is None or height is None or area is None:
            print(f"Skipped {image_path.name}: YOLO did not detect any object. Make sure the object is clearly visible in the image and the image is not blank.")
            continue

        rows.append(
            {
                "width": width,
                "height": height,
                "area": area,
                "y_center": y_center,
                "y_bottom": y_bottom,
                "object_class": class_name,
                "distance": distance,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["width", "height", "area", "y_center", "y_bottom", "object_class", "distance"]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {output_csv}")



def main() -> None:
    parser = argparse.ArgumentParser(description="Extract YOLO bounding boxes from labelled images")
    parser.add_argument("--input-dir", required=True, help="Folder containing labelled images")
    parser.add_argument("--output-csv", required=True, help="CSV file to save the bounding box features")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO model weights to use")
    args = parser.parse_args()

    build_dataset(args.input_dir, args.output_csv, model_path=args.model)


if __name__ == "__main__":
    main()
