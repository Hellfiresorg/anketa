import asyncio
import logging
import subprocess
from pathlib import Path

import httpx
from groq import AsyncGroq

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_semaphore = asyncio.Semaphore(3)

RETRY_BACKOFF = [5, 30, 120, 600, 1800]


class TranscriptionError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def check_audio_duration(file_path: Path) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return None
    except FileNotFoundError:
        logger.warning("ffprobe not found — skipping duration validation")
        return None
    except Exception as e:
        logger.warning("ffprobe failed: %s", e)
        return None


async def transcribe_audio(audio_path: Path) -> str:
    duration = check_audio_duration(audio_path)
    if duration is not None:
        if duration < 0.5:
            raise TranscriptionError("Запись слишком короткая или повреждена", retryable=False)
        if duration > settings.MAX_AUDIO_DURATION_SEC:
            raise TranscriptionError("Запись превышает максимальную длительность", retryable=False)

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async with _semaphore:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        try:
            response = await client.audio.transcriptions.create(
                file=(audio_path.name, audio_data),
                model="whisper-large-v3-turbo",
                language="ru",
                response_format="verbose_json",
            )
            return response.text
        except Exception as e:
            err_str = str(e)
            status_code = getattr(e, "status_code", None)

            if status_code == 429:
                raise TranscriptionError(f"Rate limited: {err_str}", retryable=True)
            if status_code and 500 <= status_code < 600:
                raise TranscriptionError(f"Server error: {err_str}", retryable=True)
            if isinstance(e, (httpx.ConnectError, httpx.TimeoutException)):
                raise TranscriptionError(f"Connection error: {err_str}", retryable=True)
            raise TranscriptionError(f"Transcription failed: {err_str}", retryable=False)
