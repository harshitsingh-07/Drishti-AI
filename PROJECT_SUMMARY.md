# AI Eye Project Summary

## What the project does
AI Eye is a prototype system for real-time object detection, distance estimation, and voice feedback. The current goal is to detect objects from a camera feed, estimate how far they are, and provide spoken feedback about the object and its distance.

The project combines:
- object detection using YOLO
- distance prediction from bounding-box features
- speech output for demo or accessibility purposes

## Main workflow files
The main workflow files are:
- [main.py](main.py) – webcam demo and real-time object detection flow
- [extract_bounding_boxes.py](extract_bounding_boxes.py) – extracts bounding-box features from images
- [train_distance_model.py](train_distance_model.py) – trains the distance regression model
- [dataset_utils.py](dataset_utils.py) – parses dataset filenames into object and distance labels
- [generate_synthetic_dataset.py](generate_synthetic_dataset.py) – creates synthetic training images
- [merge_datasets.py](merge_datasets.py) – merges multiple datasets into one folder and CSV

## How the pipeline works
1. Dataset preparation
   - Images are stored in a folder and named using the format object_distance_index.jpg.
   - Synthetic images can also be generated automatically when real data is limited.

2. Feature extraction
   - The bounding-box extractor runs YOLO on each image.
   - It extracts features such as width, height, area, and object class.
   - These values are stored in a CSV file for training.

3. Model training
   - The training script reads the CSV file.
   - It converts the object class into numeric features and trains a small neural network to predict distance.
   - The trained model is saved as [distance_model.pth](distance_model.pth).

4. Demo and inference
   - The camera demo in [main.py](main.py) uses YOLO detections and the trained model logic to estimate distance in real time.
   - It also displays the detected object and gives voice feedback.

## What has been built so far
The project already includes:
- a webcam-based demo in [main.py](main.py)
- a dataset filename parser in [dataset_utils.py](dataset_utils.py)
- a YOLO-based bounding-box feature extraction pipeline in [extract_bounding_boxes.py](extract_bounding_boxes.py)
- a distance regression training pipeline in [train_distance_model.py](train_distance_model.py)
- a synthetic image generator in [generate_synthetic_dataset.py](generate_synthetic_dataset.py)
- a dataset-merging helper in [merge_datasets.py](merge_datasets.py)
- a combined dataset folder at [combined_dataset](combined_dataset)
- a combined training CSV at [combined_dataset.csv](combined_dataset.csv)
- a trained model artifact at [distance_model.pth](distance_model.pth)
- test files in [tests](tests)

## Current status
The project is currently in a working prototype stage. The core building blocks are now in place for:
- synthetic data generation
- feature extraction from images
- model training for distance prediction
- real-time demo output

## Dataset and training progress
Several dataset versions were created and tested during development:
- an earlier merged dataset was used for initial experiments
- a larger and more balanced synthetic dataset was also generated
- the two datasets were later combined into one final dataset in [combined_dataset](combined_dataset) and [combined_dataset.csv](combined_dataset.csv)

## Training improvements implemented
The distance prediction model was improved by updating the training pipeline in [train_distance_model.py](train_distance_model.py).

### What was changed
- Added richer input features such as:
  - width/height ratio
  - log area
  - size sum
  - object-class encoding
- Switched to a stronger neural network with batch normalization
- Improved the optimizer and loss function for better stability
- Added input noise and learning-rate scheduling to reduce overfitting

## Verified training result
The model was trained successfully using the combined dataset.

Latest verified outcome:
- Test MAE: 0.5222 meters
- Model saved to [distance_model.pth](distance_model.pth)

This shows that the updated training setup is learning distance prediction much more effectively than the earlier version.

## Suggested next steps
- collect more real-world images to improve accuracy further
- use more realistic object placements and backgrounds in the dataset
- test the model on real camera images and compare predicted vs actual distance
- replace the simple heuristic distance estimate in the demo with the trained model output more fully
- add more evaluation metrics and visual comparisons for model performance
