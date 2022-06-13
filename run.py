# Convenience entry point at the repository root: "python run.py" opens the main
# window without installing the package; it adds src/ to the import path first.

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from music_player.app import main  # noqa: E402  (import after the path is ready)

if __name__ == "__main__":
    main()
