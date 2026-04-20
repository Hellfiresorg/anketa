import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.manager import Manager
from app.services.security import verify_token

bearer_scheme = HTTPBearer()


async def get_current_manager(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Manager:
    token = credentials.credentials
    manager_id = verify_token(token, "access")
    if not manager_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(Manager).where(Manager.id == uuid.UUID(manager_id)))
    manager = result.scalar_one_or_none()
    if not manager or not manager.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Manager not found")
    return manager
