from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yt_dlp

TWITTER_URL_RE = re.compile(r"https?://(?:[^/]+\.)?(?:twitter|x)\.com/", re.IGNORECASE)


@dataclass(frozen=True)
class DownloadedVideo:
    path: Path
    title: str
    source_url: str


class DownloadError(RuntimeError):
    pass


class VideoDownloader:
    def __init__(self, download_dir: Path, cookies: Path | None = None) -> None:
        self.download_dir = download_dir
        self.cookies = cookies
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, url: str) -> DownloadedVideo:
        job_dir = self.download_dir / uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)
        return await asyncio.to_thread(self._download_sync, url, job_dir)

    def _download_sync(self, url: str, job_dir: Path) -> DownloadedVideo:
        api_attempts: list[str | None] = [None]
        if TWITTER_URL_RE.search(url):
            api_attempts.extend(["syndication", "legacy"])

        last_error: DownloadError | None = None
        for twitter_api in api_attempts:
            try:
                return self._download_with_options(url, job_dir, twitter_api)
            except DownloadError as exc:
                last_error = exc
                if twitter_api is None and len(api_attempts) > 1:
                    logging.info("Twitter download failed with default API; trying fallback APIs")
                    continue
                if twitter_api == "syndication":
                    logging.info("Twitter download failed with syndication API; trying legacy API")
                    continue
                raise

        if last_error is None:
            raise DownloadError("yt-dlp did not run any download attempts")
        if TWITTER_URL_RE.search(url) and not self._has_cookiefile():
            raise DownloadError(
                f"{last_error}\n\n"
                "Twitter/X often hides playable media from unauthenticated requests. "
                "Export cookies from a logged-in browser in Netscape format and set "
                "YTDLP_COOKIES=/path/to/cookies.txt in .env, then restart the service."
            ) from last_error
        raise last_error

    def _has_cookiefile(self) -> bool:
        return self.cookies is not None and self.cookies.is_file()

    def _download_with_options(
        self,
        url: str,
        job_dir: Path,
        twitter_api: str | None,
    ) -> DownloadedVideo:
        output_template = str(job_dir / "%(title).180B [%(id)s].%(ext)s")
        options: dict[str, object] = {
            "format": "bestvideo*+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": output_template,
            "noplaylist": True,
            "retries": 10,
            "fragment_retries": 10,
            "continuedl": True,
            "quiet": True,
            "no_warnings": True,
        }
        if twitter_api:
            options["extractor_args"] = {"twitter": {"api": [twitter_api]}}
        if self.cookies:
            if self._has_cookiefile():
                options["cookiefile"] = str(self.cookies)
            else:
                logging.warning("Ignoring missing YTDLP_COOKIES file: %s", self.cookies)

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = Path(ydl.prepare_filename(info))
                requested = info.get("requested_downloads") or []
                if requested:
                    filename = Path(requested[0].get("filepath") or filename)
                if not filename.exists():
                    merged = filename.with_suffix(".mp4")
                    if merged.exists():
                        filename = merged
                if not filename.exists():
                    candidates = [path for path in job_dir.iterdir() if path.is_file()]
                    if not candidates:
                        raise DownloadError("yt-dlp did not produce a video file")
                    filename = max(candidates, key=lambda path: path.stat().st_size)
                title = str(info.get("title") or filename.stem)
                return DownloadedVideo(path=filename, title=title, source_url=url)
        except yt_dlp.utils.DownloadError as exc:
            raise DownloadError(str(exc)) from exc
        except OSError as exc:
            raise DownloadError(str(exc)) from exc
