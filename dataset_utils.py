import re
from pathlib import Path
from typing import Optional, Tuple


_FILENAME_PATTERN = re.compile(
    r"^(?P<object>.+)_(?P<distance>\d+(?:\.\d+)?)m_(?P<index>[\d_]+)\.(?P<ext>jpe?g|png)$",
    re.IGNORECASE,
)



def parse_filename(image_path: str | Path) -> Tuple[Optional[str], Optional[float]]:
    """Parse a dataset filename like chair_1m_01.jpg into object class and distance.

    The expected pattern is:
        <object_name>_<distance>m_<index>.<ext>

    Example:
        chair_1m_01.jpg -> ("chair", 1.0)
        water_bottle_2_5m_03.jpg -> ("water_bottle", 2.5)
    """
    path = Path(image_path)
    match = _FILENAME_PATTERN.match(path.name)
    if not match:
        return None, None

    object_name = match.group("object").strip().replace("_", " ")
    distance = float(match.group("distance"))
    return object_name, distance
