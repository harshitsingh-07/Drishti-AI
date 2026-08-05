"""
AI Eye — Accuracy Evaluation Tool
Run:
    python evaluate.py
"""

import os
import sys
import numpy as np
import pandas as pd
import torch

def evaluate():
    csv_path = "combined_dataset.csv"
    model_path = "distance_model.pth"

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        return

    print("Loading model and dataset...")
    ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
    model = ckpt.get("gbr_model")
    scaler = ckpt.get("scaler")
    ohe = ckpt.get("ohe")

    df = pd.read_csv(csv_path).drop_duplicates(subset=["width", "height", "area", "distance"]).reset_index(drop=True)
    
    from train_distance_model import compute_features
    num_scaled = scaler.transform(compute_features(df))
    
    if ohe is not None and "object_class" in df:
        cat_encoded = ohe.transform(df[["object_class"]])
        X = np.hstack([num_scaled, cat_encoded])
    else:
        X = num_scaled

    y_true = df["distance"].to_numpy()
    
    y_pred_log = model.predict(X)
    y_pred = np.exp(y_pred_log)
    errors = np.abs(y_pred - y_true)

    print("\n" + "=" * 60)
    print("         AI EYE -- OVERALL MODEL ACCURACY REPORT")
    print("=" * 60)
    print(f" Total Unique Samples Evaluated : {len(df)}")
    print(f" Overall Mean Absolute Error    : {np.mean(errors):.4f} meters ({np.mean(errors)*100:.1f} cm)")
    print(f" Near-Range MAE (< 2.5m)        : {np.mean(errors[y_true <= 2.5]):.4f} meters ({np.mean(errors[y_true <= 2.5])*100:.1f} cm)")
    print(f" Far-Range MAE  (> 2.5m)        : {np.mean(errors[y_true > 2.5]):.4f} meters ({np.mean(errors[y_true > 2.5])*100:.1f} cm)")
    print("-" * 60)
    print(" ACCURACY BY TOLERANCE MARGIN:")
    print(f"   - Within +/- 0.2m (20 cm)    : {np.mean(errors <= 0.2)*100:.2f}%")
    print(f"   - Within +/- 0.4m (40 cm)    : {np.mean(errors <= 0.4)*100:.2f}%")
    print(f"   - Within +/- 0.6m (60 cm)    : {np.mean(errors <= 0.6)*100:.2f}%")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    evaluate()
