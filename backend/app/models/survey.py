import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SurveyTemplate(Base):
    __tablename__ = "survey_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    questions: Mapped[list["SurveyQuestion"]] = relationship(
        back_populates="template", order_by="SurveyQuestion.order_index"
    )
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="template")


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    __table_args__ = (UniqueConstraint("template_id", "order_index"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_templates.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    template: Mapped["SurveyTemplate"] = relationship(back_populates="questions")
    responses: Mapped[list["Response"]] = relationship(back_populates="question")
