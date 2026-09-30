"""
services/bootstrap_model.py
---------------------------
Auto-trains the model if model.pkl is missing.
Called at app startup — cheap if model exists, ~30s if training needed.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

MODEL_PATH = BASE_DIR / "ml" / "model.pkl"
ENCODERS_PATH = BASE_DIR / "ml" / "encoders.pkl"
FEATURE_COLS_PATH = BASE_DIR / "ml" / "feature_columns.pkl"
TRAIN_SCRIPT = BASE_DIR / "ml" / "train_model.py"


def ensure_model():
    """Train model if not present. Safe to call multiple times."""
    if MODEL_PATH.exists() and ENCODERS_PATH.exists() and FEATURE_COLS_PATH.exists():
        return True

    if not TRAIN_SCRIPT.exists():
        print("[bootstrap] train_model.py not found — skip")
        return False

    try:
        print("[bootstrap] Model missing — training now...")
        import runpy
        runpy.run_path(str(TRAIN_SCRIPT), run_name="__main__")
        print("[bootstrap] Model trained successfully")
        return True
    except Exception as e:
        print(f"[bootstrap] Training failed: {e}")
        return False


if __name__ == "__main__":
    ensure_model()