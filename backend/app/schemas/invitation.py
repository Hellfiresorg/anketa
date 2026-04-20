import uuid
from datetime import datetime

from pydantic import BaseModel


class InvitationCreate(BaseModel):
    template_id: uuid.UUID
    client_name: str
    client_phone: str | None = None
    client_note: str | None = None


class InvitationCreated(BaseModel):
    id: str
    url: str


class InvitationListItem(BaseModel):
    id: str
    client_name: str
    client_phone: str | None
    manager_full_name: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    transcription_ready: int
    transcription_total: int

    model_config = {"from_attributes": True}


class InvitationListResponse(BaseModel):
    items: list[InvitationListItem]
    total: int
    page: int
    page_size: int


class ResponseOut(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    audio_url: str
    audio_duration_sec: float | None
    transcription: str | None
    transcription_status: str
    transcription_error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitationDetail(BaseModel):
    id: str
    client_name: str
    client_phone: str | None
    client_note: str | None
    manager_full_name: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    template_id: uuid.UUID
    questions: list
    responses: list[ResponseOut]


class PublicInvitationResponse(BaseModel):
    invitation: dict
    questions: list
    existing_responses: list


class SubmitResponse(BaseModel):
    status: str
    completed_at: datetime


class UploadResponseOut(BaseModel):
    response_id: uuid.UUID
    transcription_status: str
