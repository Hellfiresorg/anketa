import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from nanoid import generate
from pydantic import BaseModel as PydanticModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_manager
from app.db import get_db
from app.models.audit import AuditLog
from app.models.invitation import Invitation
from app.models.manager import Manager
from app.models.note import InvitationNote
from app.models.response import Response
from app.models.survey import SurveyQuestion, SurveyTemplate
from app.schemas.invitation import InvitationCreate, InvitationCreated
from app.services import export as export_service
from app.api.public import _stream_file
from app.services.audio_storage import get_audio_full_path
from app.config import get_settings


class NoteCreate(PydanticModel):
    text: str

settings = get_settings()
router = APIRouter(prefix="/api", tags=["invitations"])


@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    result = await db.execute(select(SurveyTemplate).where(SurveyTemplate.is_active == True))
    templates = result.scalars().all()
    return [{"id": str(t.id), "name": t.name} for t in templates]


@router.get("/templates/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    result = await db.execute(
        select(SurveyTemplate)
        .options(selectinload(SurveyTemplate.questions))
        .where(SurveyTemplate.id == template_id)
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": str(tmpl.id),
        "name": tmpl.name,
        "questions": [
            {"id": str(q.id), "order_index": q.order_index, "text": q.text, "hint": q.hint, "is_required": q.is_required}
            for q in tmpl.questions
        ],
    }


@router.get("/invitations")
async def list_invitations(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    my_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_manager: Manager = Depends(get_current_manager),
):
    query = (
        select(Invitation, Manager.full_name)
        .join(Manager, Invitation.manager_id == Manager.id)
        .where(Invitation.deleted_at == None)
    )

    if my_only:
        query = query.where(Invitation.manager_id == current_manager.id)
    if status_filter:
        query = query.where(Invitation.status == status_filter)
    if search:
        query = query.where(
            (Invitation.client_name.ilike(f"%{search}%"))
            | (Invitation.client_phone.ilike(f"%{search}%"))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Invitation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()

    items = []
    for inv, mgr_name in rows:
        resp_result = await db.execute(select(Response).where(Response.invitation_id == inv.id))
        responses = resp_result.scalars().all()
        ready = sum(1 for r in responses if r.transcription_status == "done")
        items.append({
            "id": inv.id,
            "client_name": inv.client_name,
            "client_phone": inv.client_phone,
            "manager_full_name": mgr_name,
            "status": inv.status,
            "created_at": inv.created_at.isoformat(),
            "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
            "transcription_ready": ready,
            "transcription_total": len(responses),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/invitations", response_model=InvitationCreated, status_code=201)
async def create_invitation(
    body: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_manager: Manager = Depends(get_current_manager),
):
    tmpl_result = await db.execute(
        select(SurveyTemplate).where(SurveyTemplate.id == body.template_id, SurveyTemplate.is_active == True)
    )
    if not tmpl_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Template not found")

    inv_id = generate(size=12)
    inv = Invitation(
        id=inv_id,
        template_id=body.template_id,
        manager_id=current_manager.id,
        client_name=body.client_name,
        client_phone=body.client_phone,
        client_note=body.client_note,
        status="pending",
    )
    db.add(inv)

    audit = AuditLog(
        manager_id=current_manager.id,
        action="create_invitation",
        target_id=inv_id,
        meta={"client_name": body.client_name},
    )
    db.add(audit)
    await db.commit()

    url = f"{settings.FRONTEND_URL}/s/{inv_id}"
    return InvitationCreated(id=inv_id, url=url)


@router.get("/invitations/export")
async def bulk_export_stub(_: Manager = Depends(get_current_manager)):
    raise HTTPException(status_code=501, detail="Bulk export not implemented in MVP")


@router.get("/invitations/{invitation_id}")
async def get_invitation_detail(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    result = await db.execute(
        select(Invitation, Manager.full_name)
        .join(Manager, Invitation.manager_id == Manager.id)
        .where(Invitation.id == invitation_id, Invitation.deleted_at == None)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Invitation not found")
    inv, mgr_name = row

    questions_result = await db.execute(
        select(SurveyQuestion)
        .where(SurveyQuestion.template_id == inv.template_id)
        .order_by(SurveyQuestion.order_index)
    )
    questions = questions_result.scalars().all()

    responses_result = await db.execute(
        select(Response).where(Response.invitation_id == invitation_id)
    )
    responses = responses_result.scalars().all()

    return {
        "id": inv.id,
        "client_name": inv.client_name,
        "client_phone": inv.client_phone,
        "client_note": inv.client_note,
        "manager_full_name": mgr_name,
        "status": inv.status,
        "created_at": inv.created_at.isoformat(),
        "started_at": inv.started_at.isoformat() if inv.started_at else None,
        "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
        "template_id": str(inv.template_id),
        "questions": [
            {"id": str(q.id), "order_index": q.order_index, "text": q.text, "hint": q.hint, "is_required": q.is_required}
            for q in questions
        ],
        "responses": [
            {
                "id": str(r.id),
                "question_id": str(r.question_id),
                "audio_url": f"/api/admin/responses/{r.id}/audio" if r.audio_path else None,
                "audio_duration_sec": r.audio_duration_sec,
                "transcription": r.transcription,
                "transcription_status": r.transcription_status,
                "transcription_error": r.transcription_error,
                "created_at": r.created_at.isoformat(),
            }
            for r in responses
        ],
    }


@router.delete("/invitations/{invitation_id}", status_code=204)
async def delete_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    current_manager: Manager = Depends(get_current_manager),
):
    result = await db.execute(
        select(Invitation).where(Invitation.id == invitation_id, Invitation.deleted_at == None)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    inv.deleted_at = datetime.now(UTC)
    audit = AuditLog(
        manager_id=current_manager.id,
        action="delete_invitation",
        target_id=invitation_id,
        meta={"client_name": inv.client_name},
    )
    db.add(audit)
    await db.commit()


@router.get("/invitations/{invitation_id}/export")
async def export_invitation(
    invitation_id: str,
    format: str = Query(..., pattern="^(csv_summary|csv_rows|xlsx_summary|xlsx_rows|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_manager: Manager = Depends(get_current_manager),
):
    result = await db.execute(
        select(Invitation).where(Invitation.id == invitation_id, Invitation.deleted_at == None)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    questions_result = await db.execute(
        select(SurveyQuestion)
        .where(SurveyQuestion.template_id == inv.template_id)
        .order_by(SurveyQuestion.order_index)
    )
    questions = questions_result.scalars().all()

    responses_result = await db.execute(
        select(Response).where(Response.invitation_id == invitation_id)
    )
    responses = responses_result.scalars().all()

    manager_result = await db.execute(select(Manager).where(Manager.id == inv.manager_id))
    manager = manager_result.scalar_one_or_none()

    audit = AuditLog(
        manager_id=current_manager.id,
        action="export",
        target_id=invitation_id,
        meta={"format": format},
    )
    db.add(audit)
    await db.commit()

    inv_data = {
        "id": inv.id,
        "client_name": inv.client_name,
        "client_phone": inv.client_phone or "",
        "manager_full_name": manager.full_name if manager else "",
        "status": inv.status,
        "created_at": inv.created_at,
        "completed_at": inv.completed_at,
    }
    questions_data = [{"id": str(q.id), "order_index": q.order_index, "text": q.text} for q in questions]
    responses_data = [
        {
            "question_id": str(r.question_id),
            "transcription": r.transcription or "",
            "audio_duration_sec": r.audio_duration_sec,
            "created_at": r.created_at,
        }
        for r in responses
    ]

    if format == "csv_summary":
        content, filename, media_type = export_service.generate_csv_summary([inv_data], questions_data, [responses_data])
    elif format == "csv_rows":
        content, filename, media_type = export_service.generate_csv_rows(inv_data, questions_data, responses_data)
    elif format == "xlsx_summary":
        content, filename, media_type = export_service.generate_xlsx_summary([inv_data], questions_data, [responses_data])
    elif format == "xlsx_rows":
        content, filename, media_type = export_service.generate_xlsx_rows(inv_data, questions_data, responses_data)
    else:
        content, filename, media_type = export_service.generate_pdf(inv_data, questions_data, responses_data)

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/invitations/{invitation_id}/notes")
async def list_notes(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    result = await db.execute(
        select(InvitationNote, Manager.full_name)
        .join(Manager, InvitationNote.manager_id == Manager.id)
        .where(InvitationNote.invitation_id == invitation_id)
        .order_by(InvitationNote.created_at)
    )
    rows = result.all()
    return [
        {
            "id": str(n.id),
            "text": n.text,
            "manager_name": mgr_name,
            "created_at": n.created_at.isoformat(),
        }
        for n, mgr_name in rows
    ]


@router.post("/invitations/{invitation_id}/notes", status_code=201)
async def create_note(
    invitation_id: str,
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_manager: Manager = Depends(get_current_manager),
):
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="Note text cannot be empty")
    note = InvitationNote(
        invitation_id=invitation_id,
        manager_id=current_manager.id,
        text=body.text.strip(),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return {
        "id": str(note.id),
        "text": note.text,
        "manager_name": current_manager.full_name,
        "created_at": note.created_at.isoformat(),
    }


@router.get("/admin/responses/{response_id}/audio")
async def stream_audio_admin(
    response_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    result = await db.execute(select(Response).where(Response.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
    full_path = get_audio_full_path(resp.audio_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return _stream_file(full_path, resp.audio_mime or "audio/webm", request)


@router.post("/admin/responses/{response_id}/retranscribe")
async def retranscribe(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    result = await db.execute(select(Response).where(Response.id == response_id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    resp.transcription_status = "pending"
    resp.transcription_attempts = 0
    resp.transcription_error = None
    await db.commit()

    from app.workers.arq_worker import enqueue_transcription
    await enqueue_transcription(str(response_id))
    return {"ok": True}
