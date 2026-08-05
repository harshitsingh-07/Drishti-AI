---
title: DrishtiAI
emoji: 👁️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# DrishtiAI

DrishtiAI is an intelligent navigation-assistance system for visually impaired users. It uses YOLOv8 object detection, distance estimation and voice guidance.
Points a webcam at the world and speaks natural sentences like:

> *"A person is approaching on your right side, about 1.2 metres away."*

---

## 📋 Requirements

### System requirements
| What | Why |
|---|---|
| Windows 10 / 11 | TTS uses Windows SAPI |
| Python 3.10+ | type hints syntax used throughout |
| Webcam | video input for detection |
| ~2 GB free RAM | YOLO + LLM loaded together |

### Python packages
Install everything with one command:
```bash
pip install -r requirements.txt
```

What gets installed:

| Package | Used for |
|---|---|
| `ultralytics` | YOLOv8 real-time object detection |
| `opencv-python` | webcam capture, drawing bounding boxes |
| `ollama` | Python client for the local LLM server |
| `pyttsx3` | text-to-speech fallback |
| `pywin32` | Windows SAPI voice engine (primary) |
| `torch` | neural network for distance regression model |
| `pandas` | reading/writing training CSV files |
| `scikit-learn` | train/test split, feature scaling |
| `Pillow` | generating synthetic training images |

### Ollama (local LLM server)

> ⚠️ **This is NOT a Python package — it must be installed separately.**

**Option A** — Use the installer already in this repo:
```
OllamaSetup.exe
```

**Option B** — Download from the official site:  
👉 https://ollama.com/download

After installing, pull the model (one-time, ~400 MB):
```bash
ollama pull qwen2.5:0.5b
```

> **No GPU? No problem.** `qwen2.5:0.5b` runs fine on CPU.  
> If Ollama is missing or slow, the app automatically falls back to plain template messages — it still works.

---

## ▶️ Quick start — one command does everything

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd AI-Eye

# 2. Run the setup script — installs packages, Ollama, and the AI model automatically
python setup.py

# 3. Start the app
python main.py
```

Press **Q** in the video window to quit.

> `setup.py` will:
> - Install all Python packages via pip
> - Run `OllamaSetup.exe` (already included in the repo) if Ollama isn't installed
> - Download the `qwen2.5:0.5b` language model automatically

---

## 📁 Project files

| File | Purpose |
|---|---|
| `main.py` | **Main app** — run this to start AI Eye |
| `ai_eye.py` | Older version kept as reference |
| `extract_bounding_boxes.py` | Build a training CSV from labelled photos |
| `generate_synthetic_dataset.py` | Generate synthetic images for training |
| `train_distance_model.py` | Train the distance regression neural network |
| `dataset_utils.py` | Shared filename parsing helpers |
| `distance_model.pth` | Pre-trained distance model weights |
| `requirements.txt` | All Python dependencies |
| `OllamaSetup.exe` | Ollama installer for Windows |

---

## 🔧 Training your own distance model (optional)

The current distance estimation is a simple heuristic (bounding box size → distance).  
You can replace it with a trained neural network using your own photos:

```bash
# Step 1 — take photos named like:  chair_1m_01.jpg  person_2.5m_03.jpg
# Step 2 — extract features
python extract_bounding_boxes.py --input-dir ./my_photos --output-csv dataset.csv

# Step 3 — train the model
python train_distance_model.py --csv dataset.csv --model-output distance_model.pth
```

Or generate synthetic data to experiment:
```bash
python generate_synthetic_dataset.py --output-dir ./synthetic
python extract_bounding_boxes.py --input-dir ./synthetic --output-csv synthetic.csv
python train_distance_model.py --csv synthetic.csv
```

---

## 💡 Tips

- **Slow speech?** The LLM runs locally — first announcement may take a second or two. Subsequent ones are faster after warmup.
- **No speech at all?** Make sure `pywin32` is installed and you are on Windows.
- **Model not found?** `yolov8n.pt` downloads automatically (~6 MB) on first run.
