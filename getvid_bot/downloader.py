from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yt_dlp


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
        if self.cookies:
            if self.cookies.is_file():
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
