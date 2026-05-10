from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.odoo_client import load_env


if __name__ == "__main__":
    import uvicorn

    load_env(ROOT / ".env")
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("src.api:app", host=host, port=port, reload=False)
