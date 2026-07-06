---
title: Surface Crack Detection
emoji: 🚀
colorFrom: red
colorTo: red
sdk: streamlit
sdk_version: "1.58.0"
app_file: app.py
pinned: false
---

<div align="center">

# 🛣️ Surface Crack Detection

**AI-powered detection of road & bridge surface defects using Deep Learning**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.12-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![HuggingFace](https://img.shields.io/badge/🤗%20Spaces-Live-yellow)](https://huggingface.co/spaces/amruthjakku/surface-crack-detection)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Live:** [huggingface.co/spaces/amruthjakku/surface-crack-detection](https://huggingface.co/spaces/amruthjakku/surface-crack-detection)

</div>

---

## 📋 Overview

A multi-class classifier that detects **4 types of surface defects** from images using transfer learning on ResNet50 / EfficientNet-B0.

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
    Input["Input (3×224×224)"] --> Backbone["Pretrained ResNet50<br/>(ImageNet weights)"]
    Backbone --> Frozen["Phase 1: Frozen Backbone"]
    Backbone --> Finetune["Phase 2: Unfreeze Last 2 Blocks"]
    Frozen & Finetune --> GAP["Global Average Pooling"]
    GAP --> Drop1["Dropout (p=0.5)"]
    Drop1 --> FC1["Fully Connected (256)"]
    FC1 --> ReLU["ReLU"]
    ReLU --> Drop2["Dropout (p=0.3)"]
    Drop2 --> FC2["Fully Connected (4)"]
    FC2 --> Output["Cracks / Patch / Potholes /<br/>Surface Defects"]
```

---

## 🔬 Pipeline

```mermaid
flowchart LR
    A["Raw Images<br/>(306, varied res)"] --> B["Resize (256)"]
    B --> C["CenterCrop (224)"]
    C --> D["Normalize<br/>(ImageNet μ, σ)"]
    D --> E["Stratified Split<br/>(70/15/15)"]
    E --> F["Train Set<br/>(~214 images)"]
    E --> G["Val Set<br/>(~46 images)"]
    E --> H["Test Set<br/>(~46 images)"]
    F --> I["Augmentation<br/>HFlip / Rotate / ColorJitter"]
    I --> J["Train Model"]
    G --> J
    J --> K["Evaluate → Metrics"]
    H --> K
```

---

## 🏋️ Training Strategy

| Phase             | Backbone               | Epochs |   LR   | Optimizer |
| :---------------- | :--------------------- | :----: | :----: | :-------: |
| **1 — Warmup**    | Frozen                 |  5–10  | 1×10⁻³ |   AdamW   |
| **2 — Fine-tune** | Unfreeze last 2 blocks | 15–25  | 1×10⁻⁵ |   AdamW   |

| Detail               | Value                                           |
| :------------------- | :---------------------------------------------- |
| **Loss Function**    | Weighted CrossEntropy (inverse class frequency) |
| **LR Scheduler**     | CosineAnnealingLR                               |
| **Early Stopping**   | Patience = 7 epochs                             |
| **Model Checkpoint** | Monitor validation F1                           |
| **Mixed Precision**  | `torch.cuda.amp` (if GPU available)             |

---

## 🏛️ Project Structure

```
bootcamp/
├── app.py                        # Streamlit entry point
├── pages/                        # Streamlit pages (login, home)
├── backend/                      # Application logic
│   ├── auth.py                   #   Hardcoded admin auth
│   ├── prediction.py             #   Model inference + severity
│   ├── database.py               #   Supabase client (optional)
│   └── main.py                   #   FastAPI wrappers
├── src/                          # Training pipeline
│   ├── config.py                 #   Hyperparameters
│   ├── dataset.py                #   Dataset + transforms
│   ├── model.py                  #   ResNet50 / baseline CNN
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

# 2. Run Streamlit app (direct imports — no separate server needed)
streamlit run app.py

# 3. (Optional) Prepare dataset & train model
python src/prepare_data.py
python src/train.py
python src/evaluate.py
```

**Login Credentials (hardcoded):**  
`Email:` admin@surfacedetect.com  
`Password:` Admin@123

---

## 🌐 Deployment

| Platform                |    SDK    |     Sleep?      | Setup                                                                          |
| :---------------------- | :-------: | :-------------: | :----------------------------------------------------------------------------- |
| **Hugging Face Spaces** | Streamlit |   ❌ No sleep   | `git push hf main`                                                             |
| **Docker (any host)**   |  Docker   | Depends on host | `docker build -t crack-detection . && docker run -p 8501:8501 crack-detection` |

**Live:** [huggingface.co/spaces/amruthjakku/surface-crack-detection](https://huggingface.co/spaces/amruthjakku/surface-crack-detection)

---

<div align="center">

Built with ❤️ by **Team 7 — ACE Bootcamp**

</div>
