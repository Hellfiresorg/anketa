import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.models.manager import Manager
from app.models.survey import SurveyTemplate


@pytest.mark.asyncio
async def test_create_invitation(client: AsyncClient, manager: Manager, template: SurveyTemplate, auth_headers: dict):
    resp = await client.post(
        "/api/invitations",
        json={"template_id": str(template.id), "client_name": "New Client", "client_phone": "+7 999 111 2222"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "url" in data
    assert data["id"] in data["url"]


@pytest.mark.asyncio
async def test_list_invitations_requires_auth(client: AsyncClient):
    resp = await client.get("/api/invitations")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_invitations(client: AsyncClient, auth_headers: dict, manager: Manager, template: SurveyTemplate):
    await client.post(
        "/api/invitations",
        json={"template_id": str(template.id), "client_name": "Client A"},
        headers=auth_headers,
    )
    resp = await client.get("/api/invitations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_invitations_search(client: AsyncClient, auth_headers: dict, manager: Manager, template: SurveyTemplate):
    await client.post(
        "/api/invitations",
        json={"template_id": str(template.id), "client_name": "Unique Search Client"},
        headers=auth_headers,
    )
    resp = await client.get("/api/invitations?search=Unique+Search", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any("Unique Search Client" in item["client_name"] for item in data["items"])


@pytest.mark.asyncio
async def test_delete_invitation_soft(client: AsyncClient, auth_headers: dict, manager: Manager, template: SurveyTemplate):
    create_resp = await client.post(
        "/api/invitations",
        json={"template_id": str(template.id), "client_name": "To Delete"},
        headers=auth_headers,
    )
    inv_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/invitations/{inv_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/invitations/{inv_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_invitation_detail(client: AsyncClient, auth_headers: dict, manager: Manager, template: SurveyTemplate):
    create_resp = await client.post(
        "/api/invitations",
        json={"template_id": str(template.id), "client_name": "Detail Client"},
        headers=auth_headers,
    )
    inv_id = create_resp.json()["id"]
    resp = await client.get(f"/api/invitations/{inv_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_name"] == "Detail Client"
    assert len(data["questions"]) == 3


@pytest.mark.asyncio
async def test_bulk_export_stub(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/invitations/export?format=csv_summary", headers=auth_headers)
    assert resp.status_code == 501
