import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (
        Index(
            "ix_responses_transcription_status",
            "transcription_status",
            postgresql_where="transcription_status IN ('pending', 'processing', 'failed')",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invitation_id: Mapped[str] = mapped_column(
        ForeignKey("invitations.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_questions.id", ondelete="RESTRICT"), nullable=False
    )
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    audio_mime: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    transcription_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    transcribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invitation: Mapped["Invitation"] = relationship(back_populates="responses")
    question: Mapped["SurveyQuestion"] = relationship(back_populates="responses")
