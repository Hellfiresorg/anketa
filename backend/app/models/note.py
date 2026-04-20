import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class InvitationNote(Base):
    __tablename__ = "invitation_notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invitation_id: Mapped[str] = mapped_column(
        ForeignKey("invitations.id", ondelete="CASCADE"), nullable=False
    )
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("managers.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    manager: Mapped["Manager"] = relationship()
