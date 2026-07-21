from pathlib import Path

_LANGUAGE_MODEL_DIR = Path(__file__).resolve().parents[1] / "language_model"
__path__ = [str(_LANGUAGE_MODEL_DIR)]
