import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
HARNESS_DIR = ROOT_DIR.parent / "LanguageModelHarness"


def configure_language_model_harness() -> None:
    os.environ.setdefault("LANGUAGE_MODEL_HARNESS_CONFIG_DIR", str(ROOT_DIR / "config" / "model"))
    os.environ.setdefault("LANGUAGE_MODEL_HARNESS_DATA_DIR", str(ROOT_DIR / "data"))
    if str(HARNESS_DIR) not in sys.path:
        sys.path.insert(0, str(HARNESS_DIR))
