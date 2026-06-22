# getvid

Telegram bot that accepts a video URL, downloads the best quality available through
[`yt-dlp`](https://github.com/yt-dlp/yt-dlp), and sends the resulting video back to Telegram.
It is configured for a self-hosted Telegram Bot API server, which avoids the usual public Bot API
upload limits when the local server is started with an adequate `--max-webhook-connections`/storage setup.

## Features

- Supports any site supported by `yt-dlp`, including YouTube and many adult-video sites.
- Chooses `bestvideo*+bestaudio/best` and merges to MP4 when needed.
- Uses the local Telegram Bot API endpoint via `TELEGRAM_API_ROOT`.
- Optional private allow-list with `ALLOWED_USER_IDS`.
- Optional `yt-dlp` cookies file for sites that require authentication, age checks, or consent.

## Requirements

- Python 3.11+
- `ffmpeg` available in `PATH` for merging separate video/audio streams
- A bot token from BotFather
- Your local Telegram Bot API server already running

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
cp .env.example .env
```

Edit `.env` and set at least `TELEGRAM_BOT_TOKEN` and `TELEGRAM_API_ROOT`.

## Run

```bash
set -a
. ./.env
set +a
getvid-bot
```

Send `/start` to the bot, then send a direct video URL.

## systemd example

```ini
[Unit]
Description=getvid Telegram downloader bot
After=network-online.target

[Service]
WorkingDirectory=/opt/getvid
EnvironmentFile=/opt/getvid/.env
ExecStart=/opt/getvid/.venv/bin/getvid-bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Notes

Respect copyright, site terms, and local law. For private or age-gated sites, provide a cookies file with
`YTDLP_COOKIES`; without valid cookies those downloads may fail.
