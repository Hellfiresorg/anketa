import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index("ix_invitations_created_at", "created_at"),
        Index("ix_invitations_status", "status"),
        Index("ix_invitations_manager_id", "manager_id"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_templates.id", ondelete="RESTRICT"), nullable=False
    )
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("managers.id", ondelete="RESTRICT"), nullable=False
    )
    client_name: Mapped[str] = mapped_column(String, nullable=False)
    client_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    client_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template: Mapped["SurveyTemplate"] = relationship(back_populates="invitations")
    manager: Mapped["Manager"] = relationship(back_populates="invitations")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="invitation", cascade="all, delete-orphan"
    )
