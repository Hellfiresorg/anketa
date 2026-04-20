import asyncio
import logging
import uuid
from datetime import UTC, datetime

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models.response import Response
from app.services import audio_storage
from app.services.transcription import TranscriptionError, transcribe_audio

settings = get_settings()
logger = logging.getLogger(__name__)

RETRY_BACKOFF = [5, 30, 120, 600, 1800]


async def transcribe_response(ctx: dict, response_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Response).where(Response.id == uuid.UUID(response_id)))
        resp = result.scalar_one_or_none()
        if not resp:
            logger.error("Response %s not found", response_id)
            return

        resp.transcription_status = "processing"
        resp.transcription_attempts += 1
        await db.commit()

        audio_path = audio_storage.get_audio_full_path(resp.audio_path)

        try:
            text = await transcribe_audio(audio_path)
            resp.transcription = text
            resp.transcription_status = "done"
            resp.transcribed_at = datetime.now(UTC)
            resp.transcription_error = None
            await db.commit()
            logger.info("Transcription done for response %s", response_id)

        except TranscriptionError as e:
            if e.retryable and resp.transcription_attempts < 5:
                backoff = RETRY_BACKOFF[min(resp.transcription_attempts - 1, len(RETRY_BACKOFF) - 1)]
                resp.transcription_status = "pending"
                resp.transcription_error = str(e)
                await db.commit()

                await asyncio.sleep(backoff)
                pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
                await pool.enqueue_job("transcribe_response", response_id, _defer_by=backoff)
                await pool.close()
            else:
                resp.transcription_status = "failed"
                resp.transcription_error = str(e)
                await db.commit()
                if not e.retryable:
                    logger.error("Non-retryable transcription failure for %s: %s", response_id, e)
                else:
                    logger.error("Max attempts reached for %s: %s", response_id, e)

        except Exception as e:
            resp.transcription_status = "failed"
            resp.transcription_error = str(e)
            await db.commit()
            logger.error("Unexpected transcription error for %s: %s", response_id, e, exc_info=True)


async def enqueue_transcription(response_id: str) -> None:
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await pool.enqueue_job("transcribe_response", response_id)
        await pool.close()
    except Exception as e:
        logger.error("Failed to enqueue transcription for %s: %s", response_id, e)


class WorkerSettings:
    functions = [transcribe_response]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
