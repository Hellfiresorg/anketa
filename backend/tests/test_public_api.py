import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.models.manager import Manager
from app.models.response import Response
from app.models.survey import SurveyTemplate


@pytest_asyncio.fixture
async def invitation(db: AsyncSession, manager: Manager, template: SurveyTemplate):
    inv_id = f"t{uuid.uuid4().hex[:11]}"
    inv = Invitation(
        id=inv_id,
        template_id=template.id,
        manager_id=manager.id,
        client_name="Test Client",
        client_phone="+7 999 000 0000",
        status="pending",
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    yield inv
    # cleanup so next test gets a fresh state
    await db.execute(delete(Response).where(Response.invitation_id == inv_id))
    await db.execute(delete(Invitation).where(Invitation.id == inv_id))
    await db.commit()


@pytest.mark.asyncio
async def test_get_invitation_sets_in_progress(client: AsyncClient, invitation: Invitation):
    resp = await client.get(f"/api/public/invitations/{invitation.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["invitation"]["status"] == "in_progress"
    assert data["invitation"]["client_name"] == "Test Client"
    assert len(data["questions"]) == 3


@pytest.mark.asyncio
async def test_get_invitation_not_found(client: AsyncClient):
    resp = await client.get("/api/public/invitations/nonexistent00")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_deleted_invitation_returns_410(client: AsyncClient, db: AsyncSession, invitation: Invitation):
    invitation.deleted_at = datetime.now(UTC)
    await db.commit()
    resp = await client.get(f"/api/public/invitations/{invitation.id}")
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_submit_missing_required(client: AsyncClient, invitation: Invitation):
    await client.get(f"/api/public/invitations/{invitation.id}")
    resp = await client.post(f"/api/public/invitations/{invitation.id}/submit")
    assert resp.status_code == 400
    data = resp.json()
    assert "missing_question_ids" in data["detail"]


@pytest.mark.asyncio
async def test_submit_already_completed(client: AsyncClient, db: AsyncSession, invitation: Invitation):
    await client.get(f"/api/public/invitations/{invitation.id}")
    invitation.status = "completed"
    invitation.completed_at = datetime.now(UTC)
    await db.commit()
    resp = await client.post(f"/api/public/invitations/{invitation.id}/submit")
    assert resp.status_code == 409
