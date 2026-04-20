import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models.invitation import Invitation
from app.models.response import Response
from app.models.survey import SurveyQuestion
from app.services import audio_storage

settings = get_settings()
router = APIRouter(prefix="/api/public", tags=["public"])


class TextAnswerBody(BaseModel):
    question_id: uuid.UUID
    text: str


def _check_disk_space():
    free = audio_storage.get_free_space_bytes()
    if free < settings.DISK_SPACE_MIN_BYTES:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Insufficient disk space")


async def _get_invitation_or_404(invitation_id: str, db: AsyncSession) -> Invitation:
    result = await db.execute(select(Invitation).where(Invitation.id == invitation_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.deleted_at is not None:
        raise HTTPException(status_code=410, detail="Invitation no longer available")
    return inv


@router.get("/invitations/{invitation_id}")
async def get_invitation(invitation_id: str, db: AsyncSession = Depends(get_db)):
    inv = await _get_invitation_or_404(invitation_id, db)

    if inv.status == "pending":
        inv.started_at = datetime.now(UTC)
        inv.status = "in_progress"
        await db.commit()
        await db.refresh(inv)

    template_result = await db.execute(
        select(SurveyQuestion)
        .where(SurveyQuestion.template_id == inv.template_id)
        .order_by(SurveyQuestion.order_index)
    )
    questions = template_result.scalars().all()

    responses_result = await db.execute(
        select(Response).where(Response.invitation_id == invitation_id)
    )
    responses = responses_result.scalars().all()

    existing = [
        {
            "question_id": str(r.question_id),
            "transcription_status": r.transcription_status,
            "audio_url": f"/api/public/responses/{r.id}/audio",
            "transcription": r.transcription,
        }
        for r in responses
    ]

    return {
        "invitation": {
            "id": inv.id,
            "client_name": inv.client_name,
            "status": inv.status,
            "started_at": inv.started_at.isoformat() if inv.started_at else None,
            "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
        },
        "questions": [
            {
                "id": str(q.id),
                "order_index": q.order_index,
                "text": q.text,
                "hint": q.hint,
                "is_required": q.is_required,
            }
            for q in questions
        ],
        "existing_responses": existing,
    }


@router.post("/invitations/{invitation_id}/responses")
async def upload_response(
    invitation_id: str,
    question_id: uuid.UUID = Form(...),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    _check_disk_space()
    inv = await _get_invitation_or_404(invitation_id, db)

    if inv.status == "completed":
        raise HTTPException(status_code=409, detail="Invitation already completed")
    if inv.status not in ("in_progress", "pending"):
        raise HTTPException(status_code=409, detail="Invitation not active")

    mime = audio.content_type or "audio/webm"
    ext = audio_storage.mime_to_ext(mime)

    data = await audio.read()
    if len(data) > settings.max_audio_size_bytes:
        raise HTTPException(status_code=422, detail="Audio file too large")

    if not audio_storage.validate_mime(data, mime):
        raise HTTPException(status_code=422, detail="Invalid audio format")

    existing_result = await db.execute(
        select(Response).where(
            Response.invitation_id == invitation_id,
            Response.question_id == question_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    response_id = uuid.uuid4()

    rel_path, size = await audio_storage.save_audio(data, invitation_id, response_id, ext)

    try:
        if existing:
            audio_storage.delete_audio(existing.audio_path)
            existing.audio_path = str(rel_path)
            existing.audio_size_bytes = size
            existing.audio_mime = mime
            existing.transcription = None
            existing.transcription_status = "pending"
            existing.transcription_error = None
            existing.transcription_attempts = 0
            existing.transcribed_at = None
            await db.commit()
            final_id = existing.id
        else:
            resp = Response(
                id=response_id,
                invitation_id=invitation_id,
                question_id=question_id,
                audio_path=str(rel_path),
                audio_size_bytes=size,
                audio_mime=mime,
                transcription_status="pending",
            )
            db.add(resp)
            await db.commit()
            final_id = response_id
    except Exception:
        audio_storage.delete_audio(str(rel_path))
        raise

    from app.workers.arq_worker import enqueue_transcription
    await enqueue_transcription(str(final_id))

    return {"response_id": str(final_id), "transcription_status": "pending"}


@router.post("/invitations/{invitation_id}/submit")
async def submit_invitation(invitation_id: str, db: AsyncSession = Depends(get_db)):
    inv = await _get_invitation_or_404(invitation_id, db)

    if inv.status == "completed":
        raise HTTPException(status_code=409, detail="Already submitted")

    questions_result = await db.execute(
        select(SurveyQuestion).where(
            SurveyQuestion.template_id == inv.template_id,
            SurveyQuestion.is_required == True,
        )
    )
    required_questions = questions_result.scalars().all()

    responses_result = await db.execute(
        select(Response).where(Response.invitation_id == invitation_id)
    )
    answered_ids = {r.question_id for r in responses_result.scalars().all()}

    missing = [str(q.id) for q in required_questions if q.id not in answered_ids]
    if missing:
        raise HTTPException(status_code=400, detail={"missing_question_ids": missing})

    inv.status = "completed"
    inv.completed_at = datetime.now(UTC)
    await db.commit()

    return {"status": "completed", "completed_at": inv.completed_at.isoformat()}


@router.post("/invitations/{invitation_id}/responses/text")
async def upload_text_response(
    invitation_id: str,
    body: TextAnswerBody,
    db: AsyncSession = Depends(get_db),
):
    inv = await _get_invitation_or_404(invitation_id, db)
    if inv.status == "completed":
        raise HTTPException(status_code=409, detail="Invitation already completed")
    if inv.status not in ("in_progress", "pending"):
        raise HTTPException(status_code=409, detail="Invitation not active")

    existing_result = await db.execute(
        select(Response).where(
            Response.invitation_id == invitation_id,
            Response.question_id == body.question_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.transcription = body.text
        existing.transcription_status = "done"
        existing.transcription_error = None
        await db.commit()
        return {"id": str(existing.id)}

    resp = Response(
        id=uuid.uuid4(),
        invitation_id=invitation_id,
        question_id=body.question_id,
        transcription=body.text,
        transcription_status="done",
    )
    db.add(resp)
    await db.commit()
    return {"id": str(resp.id)}


@router.post("/transcribe")
async def transcribe_audio_sync(audio: UploadFile = File(...)):
    """Synchronous transcription for client-side voice recording. Returns text immediately via Groq."""
    from pathlib import Path
    from app.services.transcription import transcribe_audio, TranscriptionError

    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="Transcription service not configured")

    data = await audio.read()
    if len(data) < 500:
        raise HTTPException(status_code=422, detail="Audio too short")
    if len(data) > settings.max_audio_size_bytes:
        raise HTTPException(status_code=422, detail="Audio file too large")

    mime = audio.content_type or "audio/webm"
    if "mp4" in mime or "m4a" in mime:
        ext = "m4a"
    elif "ogg" in mime:
        ext = "ogg"
    elif "mpeg" in mime or "mp3" in mime:
        ext = "mp3"
    else:
        ext = "webm"

    tmp_dir = Path("/var/voice-survey/audio/tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"tr_{uuid.uuid4()}.{ext}"

    try:
        tmp_path.write_bytes(data)
        text = await transcribe_audio(tmp_path)
        return {"text": text}
    except TranscriptionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Transcription failed")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/responses/{response_id}/audio")
async def stream_audio_public(response_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Response).where(Response.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    full_path = audio_storage.get_audio_full_path(resp.audio_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return _stream_file(full_path, resp.audio_mime or "audio/webm", request)


def _stream_file(path, mime: str, request: Request):
    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        range_val = range_header.replace("bytes=", "").split("-")
        start = int(range_val[0]) if range_val[0] else 0
        end = int(range_val[1]) if len(range_val) > 1 and range_val[1] else file_size - 1
        chunk_size = end - start + 1

        def iter_file():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = f.read(min(65536, remaining))
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=mime,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
            },
        )

    def iter_full():
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iter_full(),
        media_type=mime,
        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
    )
