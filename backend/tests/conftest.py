import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base, get_db
from app.main import app
from app.models.manager import Manager
from app.models.survey import SurveyQuestion, SurveyTemplate
from app.services.security import hash_password

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="session")
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def manager(db: AsyncSession) -> Manager:
    m = Manager(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=hash_password("password123"),
        full_name="Test Manager",
        is_active=True,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


@pytest_asyncio.fixture(scope="session")
async def template(db: AsyncSession) -> SurveyTemplate:
    tmpl = SurveyTemplate(id=uuid.uuid4(), name="Test Template", is_active=True)
    db.add(tmpl)
    await db.flush()
    for i in range(3):
        q = SurveyQuestion(
            id=uuid.uuid4(),
            template_id=tmpl.id,
            order_index=i,
            text=f"Question {i + 1}",
            is_required=True,
        )
        db.add(q)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, manager: Manager) -> dict:
    resp = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
