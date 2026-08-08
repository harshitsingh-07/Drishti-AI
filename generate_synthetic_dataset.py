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
    seat_w = max(10, int(36 * scale))
    seat_h = max(3, int(8 * scale))
    back_h = max(8, int(26 * scale))
    leg_w = max(2, int(4 * scale))
    y0 = y
    draw.rectangle([x - seat_w // 2, y0, x + seat_w // 2, y0 + seat_h], fill=color)
    draw.rectangle([x - seat_w // 2, y0 - back_h, x - seat_w // 2 + leg_w, y0], fill=color)
    draw.rectangle([x + seat_w // 2 - leg_w, y0 - back_h, x + seat_w // 2, y0], fill=color)


def draw_bus(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    body_w = max(30, int(100 * scale))
    body_h = max(15, int(50 * scale))
    win_off_x = int(12 * scale)
    win_off_y = int(8 * scale)
    wheel_r = max(3, int(10 * scale))

    x1, y1 = x - body_w // 2, y - body_h // 2
    x2, y2 = x + body_w // 2, y + body_h // 2

    draw.rectangle([x1, y1, x2, y2], fill=color)
    if (x2 - win_off_x) > (x1 + win_off_x) and (y1 + body_h // 2) > (y1 + win_off_y):
        draw.rectangle([x1 + win_off_x, y1 + win_off_y, x2 - win_off_x, y1 + body_h // 2], fill=(220, 220, 220))

    draw.ellipse([x1 + win_off_x, y2 - wheel_r, x1 + win_off_x + 2 * wheel_r, y2 + wheel_r], fill=(0, 0, 0))
    draw.ellipse([x2 - win_off_x - 2 * wheel_r, y2 - wheel_r, x2 - win_off_x, y2 + wheel_r], fill=(0, 0, 0))


def draw_bike(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    r = max(4, int(18 * scale))
    gap = max(10, int(40 * scale))
    stroke = max(2, int(3 * scale))
    draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=stroke)
    draw.ellipse([x + gap - r, y - r, x + gap + r, y + r], outline=color, width=stroke)
    draw.line([x, y, x + gap, y], fill=color, width=stroke)
    draw.line([x + gap // 2, y, x + gap // 4, y - int(24 * scale)], fill=color, width=stroke)


def draw_dog(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    body_w = max(12, int(40 * scale))
    body_h = max(8, int(24 * scale))
    head_r = max(4, int(10 * scale))
    draw.ellipse([x - body_w // 2, y - body_h // 2, x + body_w // 2, y + body_h // 2], fill=color)
    draw.ellipse([x - body_w // 4 - head_r, y - body_h // 2 - head_r, x - body_w // 4 + head_r, y - body_h // 2 + head_r], fill=color)


def draw_bicycle(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    r = max(4, int(18 * scale))
    gap = max(10, int(40 * scale))
    stroke = max(2, int(3 * scale))
    draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=stroke)
    draw.ellipse([x + gap - r, y - r, x + gap + r, y + r], outline=color, width=stroke)
    draw.line([x, y, x + gap, y], fill=color, width=stroke)
    draw.line([x + gap // 2, y, x + gap // 4, y - int(25 * scale)], fill=color, width=stroke)
    draw.line([x + gap, y, x + gap + int(16 * scale), y - int(20 * scale)], fill=color, width=stroke)


def draw_wall(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    w = max(20, int(140 * scale))
    h = max(15, int(90 * scale))
    border = max(2, int(10 * scale))
    x1, y1 = x - w // 2, y - h // 2
    x2, y2 = x + w // 2, y + h // 2
    draw.rectangle([x1, y1, x2, y2], fill=color)
    if (x2 - border) > (x1 + border) and (y2 - border) > (y1 + border):
        draw.rectangle([x1 + border, y1 + border, x2 - border, y2 - border], fill=(210, 210, 210))


def draw_pole(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: tuple[int, int, int]) -> None:
    h = max(20, int(80 * scale))
    stroke = max(2, int(5 * scale))
    head_r = max(3, int(8 * scale))
    draw.line([x, y - h, x, y + h], fill=color, width=stroke)
    draw.ellipse([x - head_r, y - h - head_r, x + head_r, y - h + head_r], fill=color)



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


def generate_dataset(
    output_dir: str | Path,
    classes: list[str] | None = None,
    distances: list[float] | None = None,
    images_per_distance: int = 5,
    min_distance: float = 0.5,
    max_distance: float = 6.0,
    continuous: bool = True,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if classes is None:
        classes = ["chair", "bus", "bike", "dog", "bicycle", "wall", "pole"]

    generated_count = 0
    if not continuous and distances is not None:
        target_distances = distances
    else:
        # Default discrete landmarks combined with continuous random sampling
        target_distances = distances if distances is not None else [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

    for object_name in classes:
        sample_idx = 1
        for dist_base in target_distances:
            for _ in range(images_per_distance):
                if continuous:
                    # Continuous variation around dist_base or uniform random in range
                    distance = round(random.uniform(max(min_distance, dist_base - 0.3), min(max_distance, dist_base + 0.3)), 2)
                else:
                    distance = float(dist_base)

                img = create_background(640, 480)
                draw = ImageDraw.Draw(img)

                scale = max(0.2, 1.0 / max(distance, 0.5))
                x = random.randint(120, 520)
                y = random.randint(140, 420)
                body_color = (random.randint(30, 220), random.randint(30, 220), random.randint(30, 220))
                draw_object(draw, object_name, x, y, scale, body_color)

                filename = f"{object_name}_{distance:.2f}m_{sample_idx:03d}.jpg"
                img.save(output_dir / filename)
                generated_count += 1
                sample_idx += 1

    print(f"Generated {generated_count} synthetic images in {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate simple synthetic images for multiple object classes")
    parser.add_argument("--output-dir", default="synthetic_multi_class_dataset", help="Folder where synthetic images will be saved")
    parser.add_argument("--classes", nargs="+", default=["chair", "bus", "bike", "dog", "bicycle", "wall", "pole"], help="Object classes to generate")
    parser.add_argument("--distances", nargs="+", type=float, default=None, help="Specific target distances to simulate in meters")
    parser.add_argument("--images-per-distance", type=int, default=5, help="How many images to generate per class per distance landmark")
    parser.add_argument("--min-distance", type=float, default=0.5, help="Minimum distance in meters for continuous sampling")
    parser.add_argument("--max-distance", type=float, default=6.0, help="Maximum distance in meters for continuous sampling")
    parser.add_argument("--discrete", action="store_true", help="Force discrete distances instead of continuous sampling")
    args = parser.parse_args()

    generate_dataset(
        args.output_dir,
        classes=args.classes,
        distances=args.distances,
        images_per_distance=args.images_per_distance,
        min_distance=args.min_distance,
        max_distance=args.max_distance,
        continuous=not args.discrete,
    )


if __name__ == "__main__":
    main()

