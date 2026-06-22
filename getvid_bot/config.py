from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    bot_token: str
    api_root: str
    download_dir: Path
    max_concurrent_downloads: int
    request_timeout_seconds: int
    ytdlp_cookies: Path | None
    allowed_user_ids: set[int] | None


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def _get_ids(name: str) -> set[int] | None:
    value = os.getenv(name)
    if not value:
        return None
    return {int(item.strip()) for item in value.split(",") if item.strip()}


def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    api_root = os.getenv("TELEGRAM_API_ROOT", "http://127.0.0.1:8081").rstrip("/")
    download_dir = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
    cookies = os.getenv("YTDLP_COOKIES")

    return Config(
        bot_token=token,
        api_root=api_root,
        download_dir=download_dir,
        max_concurrent_downloads=_get_int("MAX_CONCURRENT_DOWNLOADS", 2),
        request_timeout_seconds=_get_int("REQUEST_TIMEOUT_SECONDS", 3600),
        ytdlp_cookies=Path(cookies).expanduser().resolve() if cookies else None,
        allowed_user_ids=_get_ids("ALLOWED_USER_IDS"),
    )
