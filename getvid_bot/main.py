from __future__ import annotations

import asyncio
import html
import logging
import re
import shutil
from contextlib import suppress

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from .config import load_config
from .downloader import DownloadError, VideoDownloader

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
router = Router()


def _allowed(message: Message, allowed_user_ids: set[int] | None) -> bool:
    return allowed_user_ids is None or (
        message.from_user is not None and message.from_user.id in allowed_user_ids
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Пришли ссылку на видео, а я скачаю максимальное доступное качество "
        "и отправлю файл сюда."
    )


@router.message(F.text)
async def handle_url(
    message: Message,
    downloader: VideoDownloader,
    semaphore: asyncio.Semaphore,
    allowed_user_ids: set[int] | None,
) -> None:
    if not _allowed(message, allowed_user_ids):
        await message.answer("Этот бот приватный.")
        return

    match = URL_RE.search(message.text or "")
    if not match:
        await message.answer("Отправь URL, начинающийся с http:// или https://")
        return

    url = match.group(0).rstrip(").,]")
    status = await message.answer("Скачиваю видео в максимальном доступном качестве…")
    downloaded = None
    async with semaphore:
        try:
            downloaded = await downloader.download(url)
            await status.edit_text("Загрузка завершена. Отправляю файл в Telegram…")
            await message.answer_video(
                FSInputFile(downloaded.path, filename=downloaded.path.name),
                caption=downloaded.title[:1024],
                supports_streaming=True,
            )
            await status.delete()
        except DownloadError as exc:
            error_text = html.escape(str(exc)[:3000])
            await status.edit_text(f"Не удалось скачать видео:\n<code>{error_text}</code>")
        except Exception:
            logging.exception("Unexpected failure while processing %s", url)
            await status.edit_text(
                "Произошла непредвиденная ошибка. Подробности смотри в логах бота."
            )
        finally:
            if downloaded:
                with suppress(Exception):
                    shutil.rmtree(downloaded.path.parent)


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(config.api_root, is_local=True),
        timeout=config.request_timeout_seconds,
    )
    bot = Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(
        downloader=VideoDownloader(config.download_dir, config.ytdlp_cookies),
        semaphore=asyncio.Semaphore(config.max_concurrent_downloads),
        allowed_user_ids=config.allowed_user_ids,
    )
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
