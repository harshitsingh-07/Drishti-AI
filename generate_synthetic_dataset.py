import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def create_background(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), (30, 120, 180))
    draw = ImageDraw.Draw(img)

    for _ in range(16):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        x1 = x0 + random.randint(20, 140)
        y1 = y0 + random.randint(20, 140)
        color = (
            random.randint(40, 220),
            random.randint(40, 220),
            random.randint(40, 220),
        )
        draw.rectangle([x0, y0, x1, y1], fill=color)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    return img


def draw_chair(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    seat_w = int(36 * scale)
    seat_h = int(8 * scale)
    back_h = int(26 * scale)
    leg_w = max(3, int(4 * scale))
    y0 = y
    draw.rectangle([x - seat_w // 2, y0, x + seat_w // 2, y0 + seat_h], fill=color)
    draw.rectangle([x - seat_w // 2, y0 - back_h, x - seat_w // 2 + leg_w, y0], fill=color)
    draw.rectangle([x + seat_w // 2 - leg_w, y0 - back_h, x + seat_w // 2, y0], fill=color)
    draw.rectangle([x - seat_w // 2, y0 - back_h, x + seat_w // 2, y0 - back_h + leg_w], fill=color)
    draw.rectangle([x - seat_w // 2, y0 - back_h + leg_w, x - seat_w // 2 + leg_w, y0], fill=color)
    draw.rectangle([x + seat_w // 2 - leg_w, y0 - back_h + leg_w, x + seat_w // 2, y0], fill=color)


def draw_bus(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    body_w = int(90 * scale)
    body_h = int(45 * scale)
    draw.rectangle([x - body_w // 2, y - body_h // 2, x + body_w // 2, y + body_h // 2], fill=color)
    draw.rectangle([x - body_w // 2 + 16, y - body_h // 2 - 18, x + body_w // 2 - 16, y - body_h // 2], fill=(220, 220, 220))
    draw.ellipse([x - body_w // 2 + 18, y + body_h // 2 - 12, x - body_w // 2 + 42, y + body_h // 2 + 12], fill=(0, 0, 0))
    draw.ellipse([x + body_w // 2 - 42, y + body_h // 2 - 12, x + body_w // 2 - 18, y + body_h // 2 + 12], fill=(0, 0, 0))


def draw_bike(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    r = int(18 * scale)
    draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=max(2, int(3 * scale)))
    draw.ellipse([x + 40 * scale - r, y - r, x + 40 * scale + r, y + r], outline=color, width=max(2, int(3 * scale)))
    draw.line([x, y, x + 40 * scale, y], fill=color, width=max(2, int(3 * scale)))
    draw.line([x + 20 * scale, y, x + 10 * scale, y - 24 * scale], fill=color, width=max(2, int(3 * scale)))


def draw_dog(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    body_w = int(40 * scale)
    body_h = int(24 * scale)
    draw.ellipse([x - body_w // 2, y - body_h // 2, x + body_w // 2, y + body_h // 2], fill=color)
    draw.ellipse([x - 14 * scale, y - 20 * scale, x + 8 * scale, y - 4 * scale], fill=color)
    draw.ellipse([x - 18 * scale, y + 4 * scale, x - 8 * scale, y + 18 * scale], fill=(255, 255, 255))


def draw_bicycle(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    r = int(18 * scale)
    draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=max(2, int(3 * scale)))
    draw.ellipse([x + 40 * scale - r, y - r, x + 40 * scale + r, y + r], outline=color, width=max(2, int(3 * scale)))
    draw.line([x, y, x + 40 * scale, y], fill=color, width=max(2, int(3 * scale)))
    draw.line([x + 20 * scale, y, x + 12 * scale, y - 25 * scale], fill=color, width=max(2, int(3 * scale)))
    draw.line([x + 40 * scale, y, x + 56 * scale, y - 20 * scale], fill=color, width=max(2, int(3 * scale)))


def draw_wall(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    w = int(140 * scale)
    h = int(90 * scale)
    draw.rectangle([x - w // 2, y - h // 2, x + w // 2, y + h // 2], fill=color)
    draw.rectangle([x - w // 2 + 10, y - h // 2 + 10, x + w // 2 - 10, y + h // 2 - 10], fill=(210, 210, 210))


def draw_pole(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    draw.line([x, y - 80 * scale, x, y + 80 * scale], fill=color, width=max(3, int(5 * scale)))
    draw.ellipse([x - 8 * scale, y - 90 * scale, x + 8 * scale, y - 74 * scale], fill=color)


def draw_object(draw: ImageDraw.ImageDraw, object_name: str, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    object_name = object_name.lower()
    if object_name == "chair":
        draw_chair(draw, x, y, scale, color)
    elif object_name == "bus":
        draw_bus(draw, x, y, scale, color)
    elif object_name == "bike":
        draw_bike(draw, x, y, scale, color)
    elif object_name == "dog":
        draw_dog(draw, x, y, scale, color)
    elif object_name == "bicycle":
        draw_bicycle(draw, x, y, scale, color)
    elif object_name == "wall":
        draw_wall(draw, x, y, scale, color)
    elif object_name in {"pole", "polle"}:
        draw_pole(draw, x, y, scale, color)
    else:
        draw_chair(draw, x, y, scale, color)


def generate_dataset(output_dir: str | Path, classes: list[str] | None = None, distances: list[float] | None = None, images_per_distance: int = 3) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if classes is None:
        classes = ["chair", "bus", "bike", "dog", "bicycle", "wall", "pole"]

    if distances is None:
        distances = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

    generated_count = 0
    for object_name in classes:
        for distance in distances:
            for index in range(1, images_per_distance + 1):
                img = create_background(640, 480)
                draw = ImageDraw.Draw(img)

                scale = max(0.6, 1.0 / max(distance, 1.0))
                x = random.randint(120, 520)
                y = random.randint(140, 420)
                body_color = (random.randint(30, 220), random.randint(30, 220), random.randint(30, 220))
                draw_object(draw, object_name, x, y, scale, body_color)

                filename = f"{object_name}_{distance:.1f}m_{index:02d}.jpg"
                img.save(output_dir / filename)
                generated_count += 1

    print(f"Generated {generated_count} images in {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate simple synthetic images for multiple object classes")
    parser.add_argument("--output-dir", default="synthetic_multi_class_dataset", help="Folder where synthetic images will be saved")
    parser.add_argument("--classes", nargs="+", default=["chair", "bus", "bike", "dog", "bicycle", "wall", "pole"], help="Object classes to generate")
    parser.add_argument("--distances", nargs="+", type=float, default=[1.0, 1.5, 2.0, 2.5, 3.0, 4.0], help="Distances to simulate in meters")
    parser.add_argument("--images-per-distance", type=int, default=3, help="How many images to generate per class per distance")
    args = parser.parse_args()

    generate_dataset(args.output_dir, classes=args.classes, distances=args.distances, images_per_distance=args.images_per_distance)


if __name__ == "__main__":
    main()
