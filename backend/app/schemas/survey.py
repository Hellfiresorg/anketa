import uuid
from datetime import datetime

from pydantic import BaseModel


class QuestionOut(BaseModel):
    id: uuid.UUID
    order_index: int
    text: str
    hint: str | None
    is_required: bool

    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    questions: list[QuestionOut] = []

    model_config = {"from_attributes": True}


class TemplateListItem(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}
