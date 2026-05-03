from __future__ import annotations

import sys
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = V2_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
