"""Add the repo root to sys.path for `from src...` imports during tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
