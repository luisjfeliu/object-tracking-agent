import sys
from pathlib import Path


# Ensure repository root is on sys.path so `src` package imports work.
repo_root = Path(__file__).resolve().parents[1]
if repo_root.as_posix() not in sys.path:
    sys.path.insert(0, repo_root.as_posix())
