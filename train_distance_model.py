import argparse
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

OBJECT_PHYSICAL_PRIORS = {
    "person": (1.7, 0.5),
    "chair": (0.9, 0.6),
    "bus": (3.2, 2.5),
    "bike": (1.0, 1.7),
    "bicycle": (1.0, 1.7),
    "dog": (0.6, 0.8),
    "wall": (2.8, 4.0),
    "pole": (3.0, 0.3),
    "polle": (3.0, 0.3),
    "traffic light": (1.2, 0.4),
    "tennis racket": (0.7, 0.3),
    "kite": (0.8, 0.8),
    "sports ball": (0.22, 0.22),
    "airplane": (3.5, 10.0),
    "bottle": (0.25, 0.08),
    "cell phone": (0.15, 0.07),
    "laptop": (0.25, 0.35),
    "cup": (0.12, 0.08),
    "tv": (0.6, 1.0),
    "couch": (0.9, 1.8),
    "car": (1.5, 1.8),
    "desk": (0.75, 1.2),
}


def compute_features(dataframe: pd.DataFrame) -> np.ndarray:
    w = dataframe["width"].to_numpy(dtype=float)
    h = dataframe["height"].to_numpy(dtype=float)
    area = dataframe["area"].to_numpy(dtype=float)

    y_center = dataframe["y_center"].to_numpy(dtype=float) if "y_center" in dataframe else np.zeros_like(w)
    y_bottom = dataframe["y_bottom"].to_numpy(dtype=float) if "y_bottom" in dataframe else np.zeros_like(w)

    classes = dataframe["object_class"].astype(str).tolist() if "object_class" in dataframe else ["chair"] * len(w)
    prior_h = np.array([OBJECT_PHYSICAL_PRIORS.get(c.lower().strip(), (1.0, 1.0))[0] for c in classes], dtype=float)
    prior_w = np.array([OBJECT_PHYSICAL_PRIORS.get(c.lower().strip(), (1.0, 1.0))[1] for c in classes], dtype=float)

    focal_len = 400.0
    d_optics_h = focal_len * prior_h / np.maximum(h, 1.0)
    d_optics_w = focal_len * prior_w / np.maximum(w, 1.0)

    ground_dist_proxy = 100.0 / np.maximum(480.0 - y_bottom, 5.0)

    inv_w = 1.0 / np.maximum(w, 1.0)
    inv_h = 1.0 / np.maximum(h, 1.0)
    inv_sqrt_area = 1.0 / np.sqrt(np.maximum(area, 1.0))
    aspect_ratio = w / np.maximum(h, 1.0)
    log_area = np.log1p(area)

    return np.column_stack([
        w, h, area, y_center, y_bottom, inv_w, inv_h, inv_sqrt_area, aspect_ratio, log_area, ground_dist_proxy, d_optics_h, d_optics_w
    ])


def prepare_dataset(dataframe: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> Dict[str, object]:
    dataframe = dataframe.drop_duplicates(subset=["width", "height", "area", "distance"]).reset_index(drop=True)

    numeric_features = compute_features(dataframe)

    scaler = StandardScaler()
    scaled_numeric = scaler.fit_transform(numeric_features)

    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    classes_df = dataframe[["object_class"]] if "object_class" in dataframe else pd.DataFrame({"object_class": ["chair"] * len(dataframe)})
    cat_encoded = ohe.fit_transform(classes_df)

    X = np.hstack([scaled_numeric, cat_encoded])
    y = dataframe["distance"].to_numpy(dtype=float)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    feature_columns = [
        "width", "height", "area", "y_center", "y_bottom", "inv_w", "inv_h", "inv_sqrt_area", "aspect_ratio", "log_area", "ground_dist_proxy", "d_optics_h", "d_optics_w"
    ]

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "feature_columns": feature_columns,
        "scaler": scaler,
        "ohe": ohe,
    }


def train_model(csv_path: str | Path, model_path: str | Path = "distance_model.pth", epochs: int = 200, batch_size: int = 8) -> None:
    torch.manual_seed(42)
    np.random.seed(42)

    dataframe = pd.read_csv(csv_path)
    prepared = prepare_dataset(dataframe, random_state=42)

    X_train = prepared["X_train"]
    X_test = prepared["X_test"]
    y_train = prepared["y_train"]
    y_test = prepared["y_test"]

    rf = RandomForestRegressor(n_estimators=300, max_depth=8, min_samples_leaf=2, random_state=42)
    et = ExtraTreesRegressor(n_estimators=300, max_depth=10, min_samples_leaf=2, random_state=42)
    gbr = HistGradientBoostingRegressor(max_depth=6, min_samples_leaf=5, random_state=42)
    ensemble = VotingRegressor([("rf", rf), ("et", et), ("gbr", gbr)])

    sample_weights = (y_train / 1.0) ** 1.2
    ensemble.fit(X_train, np.log(y_train), sample_weight=sample_weights)

    pred_log = ensemble.predict(X_test)
    pred_meters = np.exp(pred_log)

    errors = np.abs(pred_meters - y_test)
    mae_overall = float(np.mean(errors))
    
    near_mask = y_test <= 2.5
    far_mask = y_test > 2.5
    mae_near = float(np.mean(errors[near_mask])) if np.sum(near_mask) > 0 else mae_overall
    mae_far = float(np.mean(errors[far_mask])) if np.sum(far_mask) > 0 else mae_overall
    accuracy_within_0_4m = float(np.mean(errors <= 0.4) * 100.0)

    print(f"Overall Test MAE (0.6m - 5.0m): {mae_overall:.4f} meters")
    print(f"Near-Range Test MAE (< 2.5m):   {mae_near:.4f} meters")
    print(f"Far-Range Test MAE (> 2.5m):    {mae_far:.4f} meters")
    print(f"Accuracy (predictions within +/- 0.4m): {accuracy_within_0_4m:.2f}%")

    checkpoint = {
        "gbr_model": ensemble,
        "scaler": prepared["scaler"],
        "ohe": prepared["ohe"],
        "feature_columns": prepared["feature_columns"],
        "input_dim": X_train.shape[1],
        "predict_log_target": True,
        "test_mae": mae_overall,
        "test_mae_near": mae_near,
        "test_mae_far": mae_far,
        "accuracy": accuracy_within_0_4m,
    }
    torch.save(checkpoint, model_path)
    print(f"Saved model checkpoint to {model_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the distance regression model")
    parser.add_argument("--csv", required=True, help="CSV file produced by the bounding box extractor")
    parser.add_argument("--model-output", default="distance_model.pth", help="File where the trained model will be saved")
    parser.add_argument("--epochs", type=int, default=200, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Mini-batch size")
    args = parser.parse_args()

    train_model(args.csv, args.model_output, epochs=args.epochs, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
