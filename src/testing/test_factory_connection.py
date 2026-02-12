import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from src.providers.factory import create_llm  # type: ignore

try:
    llm = create_llm(model_name="deepseek-v3")
except Exception:
    pass
