from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Pharmaceutical Product Search"
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openfda_api_key: str = os.getenv("OPENFDA_API_KEY", "")


settings = Settings()
