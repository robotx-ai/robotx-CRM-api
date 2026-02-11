from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def _load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _candidate_env_files() -> Iterable[Path]:
    root = Path(__file__).resolve().parents[1]
    yield root / ".env"
    yield root / ".env.local"
    yield root.parent / "robotx-CRM" / "demo" / ".env.local"


for candidate in _candidate_env_files():
    _load_env_file(candidate)


class Settings:
    supabase_url: str
    supabase_service_role_key: str
    api_prefix: str

    def __init__(self) -> None:
        self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
        self.supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.api_prefix = os.getenv("API_PREFIX", "/api/v1")

        if not self.supabase_url:
            raise RuntimeError("Missing NEXT_PUBLIC_SUPABASE_URL.")
        if not self.supabase_service_role_key:
            raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY.")


settings = Settings()
