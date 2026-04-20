import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_manager
from app.db import get_db
from app.models.audit import AuditLog
from app.models.manager import Manager
from app.schemas.auth import AccessTokenResponse, LoginRequest, ManagerOut, TokenResponse
from app.services.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Manager).where(Manager.email == body.email))
    manager = result.scalar_one_or_none()
    if not manager or not verify_password(body.password, manager.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(str(manager.id))
    refresh_token = create_refresh_token(str(manager.id))

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )

    db.add(AuditLog(manager_id=manager.id, action="login", target_id=str(manager.id)))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    manager_id = verify_token(token, "refresh")
    if not manager_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(Manager).where(Manager.id == uuid.UUID(manager_id)))
    manager = result.scalar_one_or_none()
    if not manager or not manager.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Manager not found")

    new_access = create_access_token(str(manager.id))
    new_refresh = create_refresh_token(str(manager.id))

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=new_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    return AccessTokenResponse(access_token=new_access)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=REFRESH_COOKIE)
    return {"ok": True}


@router.get("/me", response_model=ManagerOut)
async def me(manager: Manager = Depends(get_current_manager)):
    return ManagerOut(
        id=str(manager.id),
        email=manager.email,
        full_name=manager.full_name,
        is_active=manager.is_active,
    )


router_me = APIRouter(prefix="/api/me", tags=["me"])


from pydantic import BaseModel


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class NameUpdateRequest(BaseModel):
    full_name: str


@router_me.post("/password")
async def change_password(
    body: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    manager: Manager = Depends(get_current_manager),
):
    if not verify_password(body.current_password, manager.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    manager.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}


@router_me.patch("/name")
async def update_name(
    body: NameUpdateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Manager = Depends(get_current_manager),
):
    name = body.full_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    manager.full_name = name
    await db.commit()
    return {"ok": True, "full_name": manager.full_name}
