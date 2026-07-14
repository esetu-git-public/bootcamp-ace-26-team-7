import os
import json
import time
from datetime import datetime
from src.config import Config

RESULTS_FILE = os.path.join(Config.REPORTS_DIR, "session_results.json")


class SessionTracker:

    @staticmethod
    def load():
        if not os.path.exists(RESULTS_FILE):
            return {"sessions": []}
        with open(RESULTS_FILE, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_entry(entry):
        os.makedirs(Config.REPORTS_DIR, exist_ok=True)
        data = SessionTracker.load()
        data["sessions"].append(entry)
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def past_models():
        found = {}
        for name in ["resnet50", "efficientnet_b0", "vit_b_16"]:
            path = Config.get_model_path(name)
            if os.path.exists(path):
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                found[name] = {
                    "path": path,
                    "size_mb": round(os.path.getsize(path) / (1024 * 1024), 1),
                    "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                }
        return found

    @staticmethod
    def last_session():
        data = SessionTracker.load()
        if data["sessions"]:
            return data["sessions"][-1]
        return None

    @staticmethod
    def summary():
        data = SessionTracker.load()
        if not data["sessions"]:
            return "No past sessions found."

        lines = []
        lines.append("Past training sessions:")
        lines.append(f"  {'Session':<8} {'Date':<18} {'Device':<8} {'Mode':<10} Models")
        lines.append(f"  {'-'*8} {'-'*18} {'-'*8} {'-'*10} {'-'*30}")
        for i, s in enumerate(data["sessions"]):
            models_str = ", ".join(
                f"{m}={v.get('acc', '?')*100:.1f}%" if v.get("status") == "ok" and v.get("acc")
                else f"{m}=FAIL"
                for m, v in s.get("models", {}).items()
                if m != "ensemble"
            )
            lines.append(
                f"  #{i:<6} {s.get('timestamp','?'):<18} {s.get('device','?'):<8} "
                f"{s.get('mode','?'):<10} {models_str}"
            )
        return "\n".join(lines)

    @staticmethod
    def build_entry(model_name, metrics=None, status="ok", error=None, resumed_from=None):
        entry = {
            "status": status,
        }
        if metrics:
            entry.update(metrics)
        if error:
            entry["error"] = str(error)[:200]
        if resumed_from:
            entry["resumed_from"] = resumed_from
        model_path = Config.get_model_path(model_name)
        if os.path.exists(model_path):
            entry["size_mb"] = round(os.path.getsize(model_path) / (1024 * 1024), 1)
        return entry

    @staticmethod
    def new_session(device, mode, model_results, kfold_summary=None):
        entry = {
            "timestamp": time.strftime("%Y-%m-%d_%H-%M"),
            "device": str(device),
            "mode": mode,
            "models": model_results,
        }
        if kfold_summary:
            entry["kfold"] = {
                "n_folds": kfold_summary["n_folds"],
                "avg_val_loss": round(kfold_summary["avg_val_loss"], 4),
                "avg_val_acc": round(kfold_summary["avg_val_acc"], 4),
                "std_val_acc": round(kfold_summary["std_val_acc"], 4),
            }
        SessionTracker.save_entry(entry)
        return entry
