---
title: Surface Crack Detection
emoji: 🚀
colorFrom: red
colorTo: red
sdk: gradio
sdk_version: "5.20.1"
app_file: app.py
pinned: false
---

<div align="center">

# 🛣️ Surface Crack Detection

**AI-powered detection of road & bridge surface defects using Deep Learning**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.12-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Gradio](https://img.shields.io/badge/Gradio-5.20-FF6B6B?logo=gradio&logoColor=white)](https://gradio.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![HuggingFace](https://img.shields.io/badge/🤗%20Spaces-Live-yellow)](https://huggingface.co/spaces/amruthjakku/surface-crack-detection)
[![wandb](https://img.shields.io/badge/wandb-Dashboard-blue?logo=weightsandbiases)](https://wandb.ai/amruthjakku/surface-crack-detection)

**Live:** [huggingface.co/spaces/amruthjakku/surface-crack-detection](https://huggingface.co/spaces/amruthjakku/surface-crack-detection)

</div>

---

## 📋 Overview

A multi-class classifier that detects **4 types of surface defects** from images using transfer learning (ResNet50, EfficientNet-B0, ViT-B/16) with optional ensemble inference.

| Defect Class        | Samples | % of Dataset |
| :------------------ | ------: | :----------: |
| **Cracks**          |      73 |    23.9%     |
| **Patch**           |      42 |    13.7%     |
| **Potholes**        |      91 |    29.7%     |
| **Surface Defects** |     100 |    32.7%     |
| **Total**           | **306** |   **100%**   |

**Domain:** Manufacturing & Computer Vision  
**Framework:** PyTorch  
**Bootcamp:** ACE — Team 7

---

## 🧠 Architecture

```mermaid
graph TB
    Input["Input (3×224×224)"] --> Backbone["Pretrained Backbone<br/>(ResNet50 / EfficientNet / ViT)"]
    Backbone --> Frozen["Phase 1: Frozen Backbone"]
    Backbone --> Finetune["Phase 2: Unfreeze Last Stage"]
    Frozen & Finetune --> Head["FC (2048→256) → ReLU → Dropout(0.3) → FC (256→4)"]
    Head --> Output["Cracks / Patch / Potholes /<br/>Surface Defects"]
```

---

## 🔬 Pipeline

```mermaid
flowchart LR
    A["Raw Images<br/>(306, varied res)"] --> B["Resize (224×224)"]
    B --> C["Normalize<br/>(ImageNet μ, σ)"]
    C --> D["Stratified Split<br/>(70/15/15)"]
    D --> E["Train Set<br/>(~214 images)"]
    D --> F["Val Set<br/>(~46 images)"]
    D --> G["Test Set<br/>(~46 images)"]
    E --> H["Augmentation<br/>RandResizedCrop / HFlip / Rotate /<br/>Affine / GaussianBlur / Erasing"]
    H --> I["Train Model"]
    F --> I
    I --> J["Evaluate → Metrics"]
    G --> J
```

---

## 🏋️ Training Strategy

| Phase             | Backbone             | Epochs |   LR   | Optimizer |
| :---------------- | :------------------- | :----: | :----: | :-------: |
| **1 — Warmup**    | Frozen               |   5    | 1×10⁻³ |   AdamW   |
| **2 — Fine-tune** | Unfreeze last stage  |   15   | 1×10⁻⁵ |   AdamW   |

| Detail               | Value                                           |
| :------------------- | :---------------------------------------------- |
| **Loss Function**    | Weighted CrossEntropy + label smoothing (ε=0.1) |
| **LR Scheduler**     | ReduceLROnPlateau (factor=0.5, patience=3)      |
| **Early Stopping**   | Patience = 7 epochs                             |
| **Model Checkpoint** | Monitor validation loss                          |
| **Regularization**   | Mixup (α=0.2, prob=0.5)                         |

---

## 🏋️ Training Environment

**Platform:** Google Colab (free T4 GPU) — [Open Notebook](notebooks/04_train_wandb.ipynb)
**Tracking:** [Weights & Biases Dashboard](https://wandb.ai/amruthjakku/surface-crack-detection)

### Model Performance Comparison

| Run | Model | Accuracy | Weighted F1 | Date | wandb Link |
|:----|:------|:--------:|:-----------:|:----:|:----------:|
| 1 | ResNet50 | 79.6% | 79.6% | Jul 2026 | — |
| 2 | EfficientNet-B0 | — | — | — | — |
| 3 | ViT-B/16 | — | — | — | — |
| 4 | **Ensemble** (R50+Eff) | — | — | — | — |

> Rows populate after each training session. Click wandb links for live charts & confusion matrices.

---

## 🏛️ Project Structure

```
bootcamp/
├── app.py                        # Gradio entry point
├── backend/                      # Application logic
│   ├── auth.py                   #   Hardcoded admin auth
│   ├── prediction.py             #   Model inference + severity
│   ├── database.py               #   Supabase client (optional)
│   └── main.py                   #   FastAPI wrappers
├── src/                          # Training pipeline
│   ├── config.py                 #   Hyperparameters
│   ├── dataset.py                #   Dataset + transforms
│   ├── model.py                  #   ResNet50 / EfficientNet / ViT
│   ├── train.py                  #   Training loop
│   ├── evaluate.py               #   Evaluation + metrics
│   └── prepare_data.py           #   Data splitting
├── data/                         # Processed dataset
├── notebooks/                    # EDA & results
├── models/                       # Trained checkpoints
├── migrations/                   # Database schemas
├── Dockerfile                    # Container support
├── requirements.txt              # Dependencies
├── PLAN.md                       # Technical plan
├── TEAM_ROADMAP.md               # Sprint roadmap
└── README.md                     # ← You are here
```

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run Gradio app
gradio app.py

# 3. (Optional) Prepare dataset & train model
python src/prepare_data.py
python src/train.py
python src/evaluate.py
```
---

## 📊 Results

See **Model Performance Comparison** table above for all training runs tracked via wandb.

### Session 1 — ResNet50 (Baseline)

**Test Set — 49 images** | Accuracy: **79.6%** | Weighted F1: **79.6%** | Macro F1: **78.3%**

| Class | Precision | Recall | F1 | Support |
|:------|:--------:|:------:|:--:|:-------:|
| Cracks | 1.00 | 0.67 | 0.80 | 12 |
| Patch | 0.71 | 0.71 | 0.71 | 7 |
| **Potholes** ⭐ | 0.68 | **1.00** | **0.81** | 15 |
| Surface Defects | 0.92 | 0.73 | 0.81 | 15 |

> **Potholes achieve 100% recall** — every pothole image is correctly identified.
> Weighted loss with a 1.5× Pothole priority multiplier emphasizes this class during training.

---

## 🌐 Deployment

| Platform                |    SDK    |     Sleep?      | Setup                                                                          |
| :---------------------- | :-------: | :-------------: | :----------------------------------------------------------------------------- |
| **Hugging Face Spaces** | Gradio |   ❌ No sleep   | `git push hf main`                                                             |
| **Docker (any host)**   |  Docker   | Depends on host | `docker build -t crack-detection . && docker run -p 8501:8501 crack-detection` |

**Live:** [huggingface.co/spaces/amruthjakku/surface-crack-detection](https://huggingface.co/spaces/amruthjakku/surface-crack-detection)

---

<div align="center">

Built with ❤️ by **Team 7 — ACE Bootcamp**

</div>
```