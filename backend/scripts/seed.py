"""Idempotent seed script: creates managers and default survey template."""
import asyncio
import os
import sys
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.manager import Manager
from app.models.survey import SurveyQuestion, SurveyTemplate
from app.services.security import hash_password

settings = get_settings()


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        await _seed_managers(db)
        scripts_dir = Path(__file__).parent
        for yaml_file in sorted(scripts_dir.glob("*.yaml")):
            await _seed_template(db, yaml_file)

    await engine.dispose()
    print("Seed completed successfully.")


async def _seed_managers(db: AsyncSession):
    raw = os.getenv("SEED_MANAGERS", "")
    if not raw:
        print("SEED_MANAGERS not set, skipping manager seed.")
        return

    entries = [e.strip() for e in raw.split(",") if e.strip()]
    for entry in entries:
        parts = entry.split(":")
        if len(parts) < 3:
            print(f"Skipping invalid entry: {entry}")
            continue
        email, password, full_name = parts[0], parts[1], ":".join(parts[2:])

        result = await db.execute(select(Manager).where(Manager.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Manager {email} already exists, skipping.")
            continue

        manager = Manager(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
        )
        db.add(manager)
        print(f"Created manager: {email}")

    await db.commit()


async def _seed_template(db: AsyncSession, questions_file: Path):
    with open(questions_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    template_name = data["template_name"]
    questions_data = data["questions"]

    result = await db.execute(select(SurveyTemplate).where(SurveyTemplate.name == template_name))
    template = result.scalar_one_or_none()

    if not template:
        template = SurveyTemplate(id=uuid.uuid4(), name=template_name, is_active=True)
        db.add(template)
        await db.flush()
        print(f"Created template: {template_name}")
    else:
        print(f"Template '{template_name}' already exists, updating questions.")

    for q_data in questions_data:
        result = await db.execute(
            select(SurveyQuestion).where(
                SurveyQuestion.template_id == template.id,
                SurveyQuestion.order_index == q_data["order_index"],
            )
        )
        question = result.scalar_one_or_none()
        if question:
            question.text = q_data["text"]
            question.hint = q_data.get("hint")
            question.is_required = q_data.get("is_required", True)
        else:
            question = SurveyQuestion(
                id=uuid.uuid4(),
                template_id=template.id,
                order_index=q_data["order_index"],
                text=q_data["text"],
                hint=q_data.get("hint"),
                is_required=q_data.get("is_required", True),
            )
            db.add(question)

    await db.commit()
    print("Template questions seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
