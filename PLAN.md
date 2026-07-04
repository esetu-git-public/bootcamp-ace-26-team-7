# Technical Plan: Surface Crack Detection

This document outlines the pipeline, models, and training strategy for detecting defects on road and bridge surfaces using computer vision.

## Objectives
1. Implement a data preparation script to split images into stratified subsets (train/val/test).
2. Establish a PyTorch dataset and image transform pipeline.
3. Train a ResNet-50 or Custom 3-Layer CNN model using transfer learning.
4. Evaluate performance using F1-Score, accuracy, and confusion matrices.
5. Save model weights and check progress under `models/` and `reports/`.

## Pipeline Architecture
- **Data Prep**: `src/prepare_data.py` splits dataset.
- **Dataset Loading**: `src/dataset.py` wraps PyTorch transforms.
- **Model Definition**: `src/model.py` exposes ResNet-50 backbone or standard CNN.
- **Training Pipeline**: `src/train.py` implements the warmup & fine-tuning loop.
- **Evaluation Loop**: `src/evaluate.py` generates final classification reports.
