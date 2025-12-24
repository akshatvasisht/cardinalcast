"""ML service config: DB URL and model paths from environment."""

import os
from pathlib import Path

def get_db_url() -> str:
    url = os.environ.get("DB_URL")
    if not url:
        raise ValueError("DB_URL environment variable is required")
    return url


def get_model_dir() -> Path:
    """Directory containing .pkl model files (e.g. high_temp_p10_model.pkl)."""
    default = Path(__file__).parent / "models"
    return Path(os.environ.get("ML_MODEL_DIR", str(default)))
