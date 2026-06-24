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
- Automatic Twitter/X fallback extraction through `graphql`, `syndication`, then `legacy` APIs.

## Requirements

- Python 3.10+ (`python3` on Debian/Ubuntu)
- `python3-venv` installed for virtual environments
- `ffmpeg` available in `PATH` for merging separate video/audio streams
- A bot token from BotFather
- Your local Telegram Bot API server already running

## Install

```bash
python3 -m venv .venv
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

For Twitter/X links, the bot first uses the default `yt-dlp` extractor API. If Twitter reports a
video as unavailable, the bot automatically retries with the `syndication` and `legacy` extractor
APIs before returning an error. Some Twitter/X videos still require cookies from a logged-in
browser; export them in Netscape format and set `YTDLP_COOKIES=/path/to/cookies.txt` in `.env`.

## systemd setup

The example below assumes the project lives in `/opt/getvid`. If you keep it somewhere else,
replace `/opt/getvid` in the commands and unit file with your actual path.

1. Copy the project to `/opt/getvid` and install it:

   ```bash
   sudo mkdir -p /opt/getvid
   sudo rsync -a --delete ./ /opt/getvid/
   cd /opt/getvid
   python3 -m venv .venv
   . .venv/bin/activate
   pip install -e .
   cp .env.example .env
   nano .env
   ```

2. Create the systemd unit:

   ```bash
   sudo tee /etc/systemd/system/getvid.service >/dev/null <<'EOF'
   [Unit]
   Description=getvid Telegram downloader bot
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   WorkingDirectory=/opt/getvid
   EnvironmentFile=/opt/getvid/.env
   ExecStart=/opt/getvid/.venv/bin/getvid-bot
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   EOF
   ```

3. Enable autostart and start the bot now:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now getvid.service
   ```

4. Check status and logs:

   ```bash
   systemctl status getvid.service
   journalctl -u getvid.service -f
   ```

Useful maintenance commands:

```bash
sudo systemctl restart getvid.service
sudo systemctl stop getvid.service
sudo systemctl disable getvid.service
```

## Notes

Respect copyright, site terms, and local law. For private or age-gated sites, provide a cookies file with
`YTDLP_COOKIES`; the file path must exist, otherwise the bot ignores it and logs a warning.
Without valid cookies those downloads may fail.
