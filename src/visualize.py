import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.session import SessionTracker
from src.config import Config

MODEL_COLORS = {
    "resnet50": "#2196F3",
    "efficientnet_b0": "#4CAF50",
    "vit_b_16": "#FF9800",
    "ensemble": "#9C27B0",
}
MODEL_LABELS = {
    "resnet50": "ResNet50",
    "efficientnet_b0": "EfficientNet",
    "vit_b_16": "ViT-B/16",
    "ensemble": "Ensemble",
}
CLASS_COLORS = ["#e74c3c", "#3498db", "#f39c12", "#2ecc71"]


def _fmt_delta(current, previous):
    if previous is None or previous == 0:
        return ""
    diff = current - previous
    sign = "+" if diff >= 0 else ""
    color = "green" if diff >= 0 else "red"
    return diff, f"{sign}{diff*100:.1f}%", color


def _gather_metrics(data):
    models_order = ["resnet50", "efficientnet_b0", "vit_b_16", "ensemble"]
    timestamps = [s["timestamp"] for s in data["sessions"]]
    n_sessions = len(timestamps)

    model_accs = {m: [] for m in models_order}
    model_f1s = {m: [] for m in models_order}

    for session in data["sessions"]:
        for m in models_order:
            md = session.get("models", {}).get(m, {})
            if md.get("status") == "ok":
                model_accs[m].append(md.get("accuracy", None))
                model_f1s[m].append(md.get("weighted_f1", None))
            else:
                model_accs[m].append(None)
                model_f1s[m].append(None)

    return timestamps, model_accs, model_f1s, n_sessions


def _gather_per_class(data):
    models_order = ["resnet50", "efficientnet_b0", "vit_b_16"]
    classes = Config.CLASSES
    timestamps = [s["timestamp"] for s in data["sessions"]]
    n_sessions = len(timestamps)

    per_class = {}
    for model_name in models_order:
        per_class[model_name] = {}
        for cls in classes:
            per_class[model_name][cls] = []
            for session in data["sessions"]:
                md = session.get("models", {}).get(model_name, {})
                pc = md.get("per_class", {}).get(cls, {})
                per_class[model_name][cls].append(pc.get("f1", None))
    return timestamps, per_class, n_sessions


def plot_session_comparison(save_path=None):
    if save_path is None:
        save_path = os.path.join(Config.REPORTS_DIR, "session_comparison.png")

    data = SessionTracker.load()
    if not data["sessions"]:
        return None

    timestamps, model_accs, model_f1s, n = _gather_metrics(data)
    short_ts = [t.split("_")[-1][:5] if "_" in t else t for t in timestamps]

    models_order = ["resnet50", "efficientnet_b0", "vit_b_16", "ensemble"]
    x = np.arange(n)
    bar_width = 0.18
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), gridspec_kw={"height_ratios": [1, 1]})

    def _plot_grouped_bars(ax, metric_dict, title, ylabel):
        for i, m in enumerate(models_order):
            vals = metric_dict[m]
            if all(v is None for v in vals):
                continue
            bars = ax.bar(
                x + i * bar_width,
                [v * 100 if v is not None else 0 for v in vals],
                bar_width,
                label=MODEL_LABELS.get(m, m),
                color=MODEL_COLORS.get(m, "#888"),
                alpha=0.85,
            )
            # Delta annotation
            prev_val = None
            for j, (val, bar) in enumerate(zip(vals, bars)):
                if val is not None:
                    val_pct = val * 100
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        val_pct + 0.5,
                        f"{val_pct:.1f}%",
                        ha="center", va="bottom", fontsize=7,
                    )
                    if prev_val is not None:
                        diff = val - prev_val
                        sign = "+" if diff >= 0 else ""
                        color = "green" if diff >= 0 else "red"
                        ax.annotate(
                            f"{sign}{diff*100:.1f}%",
                            (bar.get_x() + bar.get_width() / 2, val_pct + 4.5),
                            ha="center", va="bottom", fontsize=7, color=color,
                            fontweight="bold",
                        )
                    prev_val = val

        ax.set_xticks(x + bar_width * 1.5)
        ax.set_xticklabels(short_ts, rotation=30, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=8, loc="upper left")
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)

    def _plot_per_class_trends(ax):
        _, pc, _ = _gather_per_class(data)
        classes = Config.CLASSES

        for ci, cls in enumerate(classes):
            all_vals = []
            for mi, m in enumerate(["resnet50", "efficientnet_b0", "vit_b_16"]):
                for v in pc[m][cls]:
                    if v is not None:
                        all_vals.append(v)
            if not all_vals:
                continue
            # Average per-class F1 across all models per session
            avg_f1_per_session = []
            for si in range(n):
                model_vals = []
                for m in ["resnet50", "efficientnet_b0", "vit_b_16"]:
                    v = pc[m][cls][si]
                    if v is not None:
                        model_vals.append(v)
                avg_f1_per_session.append(np.mean(model_vals) if model_vals else None)

            valid = [(i, v * 100) for i, v in enumerate(avg_f1_per_session) if v is not None]
            if valid:
                xs, ys = zip(*valid)
                ax.plot(xs, ys, marker="o", label=cls, color=CLASS_COLORS[ci], linewidth=2)
                for xi, yi in zip(xs, ys):
                    ax.annotate(f"{yi:.1f}%", (xi, yi), textcoords="offset points",
                                xytext=(0, 10), ha="center", fontsize=7, color=CLASS_COLORS[ci])

        ax.set_xticks(range(n))
        ax.set_xticklabels(short_ts, rotation=30, ha="right")
        ax.set_ylabel("Avg F1 Across Models (%)")
        ax.set_title("Per-Class Accuracy Trend (averaged across models)")
        ax.legend(fontsize=8)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)

    _plot_grouped_bars(axes[0, 0], model_accs, "Test Accuracy by Model (%)", "Accuracy (%)")
    _plot_grouped_bars(axes[0, 1], model_f1s, "Weighted F1 by Model (%)", "Weighted F1 (%)")
    _plot_per_class_trends(axes[1, 0])

    # Bottom-right: summary stats text
    axes[1, 1].axis("off")
    last = data["sessions"][-1]
    prev = data["sessions"][-2] if n >= 2 else None
    text_lines = ["Session Comparison Summary", "", f"Current session: #{n}", f"Date: {last['timestamp']}"]
    if prev:
        for m in models_order:
            cur = last.get("models", {}).get(m, {}).get("accuracy")
            prv = prev.get("models", {}).get(m, {}).get("accuracy")
            if cur is not None and prv is not None:
                diff = cur - prv
                sign = "+" if diff >= 0 else ""
                text_lines.append(f"{MODEL_LABELS.get(m, m)}: {sign}{diff*100:.2f}% vs prev")
    axes[1, 1].text(0.05, 0.95, "\n".join(text_lines), transform=axes[1, 1].transAxes,
                    fontsize=10, verticalalignment="top", family="monospace")

    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    return save_path
