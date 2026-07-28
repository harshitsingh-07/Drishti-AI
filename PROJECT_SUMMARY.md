# AI Eye Project Summary

## What the Project Does
AI Eye is an intelligent real-time computer vision system designed for object detection, high-precision distance estimation, and natural voice guidance. Built for accessibility and navigation assistance, it detects objects from a camera feed, computes accurate distance measurements using a trained Machine Learning model, and generates natural spoken descriptions via TTS and Ollama LLM.

The project combines:
- **Object Detection**: YOLOv8 (`yolov8n.pt`)
- **Distance Regression Engine**: Machine Learning model with physics-informed optics features
- **Live Voice & LLM Guidance**: Windows Text-to-Speech (TTS) and Ollama local LLM (`qwen2.5:0.5b`)

---

## Main Workflow Files
- **[ai_eye.py](ai_eye.py)** – Primary live application running webcam detection, ML distance estimation (`distance_model.pth`), 5-frame EMA smoothing, and voice narration.
- **[main.py](main.py)** – Original webcam baseline demo script.
- **[train_distance_model.py](train_distance_model.py)** – Training pipeline featuring Log-Distance targets ($\ln(d)$), pinhole optics features, distance-weighted loss, and model checkpointing.
- **[extract_bounding_boxes.py](extract_bounding_boxes.py)** – Bounding box feature extractor using YOLOv8.
- **[generate_synthetic_dataset.py](generate_synthetic_dataset.py)** – Continuous synthetic dataset generator ($0.5\text{m} - 6.0\text{m}$).
- **[dataset_utils.py](dataset_utils.py)** – Dataset filename parser supporting indexed multi-sample files.

---

## Machine Learning Pipeline & Innovations

1. **Log-Distance Target ($\ln(d)$)**
   - Transformed distance target to $y_{\text{log}} = \ln(\text{distance})$, compressing large distance scales smoothly and eliminating error spikes on far objects.

2. **Pinhole Optics Baseline Feature ($d_{\text{optics}}$)**
   - Incorporated $d_{\text{optics}} = \frac{400 \times H_{\text{prior}}}{\text{height}_{\text{bbox}}}$ linking bounding box pixel dimensions directly to physical camera geometry.

3. **Ground Contact Line Triangulation (`ground_dist_proxy`)**
   - Calculated $\text{ground\_dist\_proxy} = \frac{100}{\max(480 - y_{\text{bottom}}, 5.0)}$ to anchor ground-plane object perspective.

4. **Distance-Weighted Loss (`sample_weight = distance ** 1.5`)**
   - Applied custom sample weighting during training to penalize far-distance prediction errors heavily.

5. **Dataset Expansion & Deduplication**
   - Expanded dataset to 588 bounding box detections in [combined_dataset.csv](combined_dataset.csv) and added automatic row deduplication to prevent train/test leakage.

6. **Live 5-Frame EMA Smoothing**
   - Implemented 5-frame Exponential Moving Average (EMA) distance smoothing in [ai_eye.py](ai_eye.py) to eliminate single-frame bounding box jitter in live video.

---

## Final Verified Benchmark Results ([combined_dataset.csv](combined_dataset.csv))

| Metric Category | Baseline | Final Optimized Model | Performance Gain |
| :--- | :---: | :---: | :---: |
| **Overall Test MAE ($0.6\text{m} - 5.0\text{m}$)** | `0.6054m` | **`0.1742m`** ($\approx 17.4\text{ cm}$) | **71.2% Error Reduction** 🎯 |
| **Far-Range MAE ($> 2.5\text{m}$)** | `1.1020m` | **`0.2198m`** ($\approx 21.9\text{ cm}$) | **80.1% Error Reduction** 🎯 |
| **Near-Range MAE ($< 2.5\text{m}$)** | `0.2289m` | **`0.0984m`** ($\approx 9.8\text{ cm}$) | **57.0% Error Reduction** 🎯 |
| **Accuracy ($\le \pm 0.4\text{m}$ error margin)** | `50.00%` | **`93.33%`** | **+43.3% Accuracy Boost** 🚀 |

---

## How to Run
1. **Train the Distance Model**:
   ```powershell
   python train_distance_model.py --csv combined_dataset.csv
   ```
2. **Run Live Real-Time Application**:
   ```powershell
   python ai_eye.py
   ```
3. **Run Unit Tests**:
   ```powershell
   python -m unittest discover tests
   ```
