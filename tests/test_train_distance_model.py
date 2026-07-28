import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from train_distance_model import prepare_dataset


def test_prepare_dataset_returns_expected_shapes() -> None:
    frame = pd.DataFrame(
        {
            "width": [100.0, 120.0, 140.0, 160.0],
            "height": [80.0, 90.0, 100.0, 110.0],
            "area": [8000.0, 10800.0, 14000.0, 17600.0],
            "object_class": ["chair", "chair", "bottle", "bottle"],
            "distance": [1.0, 2.0, 1.5, 3.0],
        }
    )

    result = prepare_dataset(frame, test_size=0.25, random_state=42)

    # 14 numeric features + 2 one-hot class columns = 16 total features
    assert result["X_train"].shape[1] == 16
    assert result["X_test"].shape[1] == 16
    assert result["y_train"].shape[0] == 3
    assert result["y_test"].shape[0] == 1
    assert "focal_ratio_h" in result["feature_columns"]
    assert "prior_h" in result["feature_columns"]
