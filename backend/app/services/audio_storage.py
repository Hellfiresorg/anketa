import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles

from app.config import get_settings

settings = get_settings()

ALLOWED_MIMES = {"audio/webm", "audio/mp4", "audio/wav", "audio/ogg", "audio/mpeg"}

MAGIC_BYTES: dict[str, list[bytes]] = {
    "audio/webm": [b"\x1a\x45\xdf\xa3"],
    "audio/mp4": [b"\x00\x00\x00\x18ftypM4A", b"\x00\x00\x00\x1cftyp", b"\x00\x00\x00\x20ftyp"],
    "audio/wav": [b"RIFF"],
    "audio/ogg": [b"OggS"],
}


def _audio_root() -> Path:
    return Path(settings.AUDIO_ROOT)


def get_free_space_bytes() -> int:
    root = _audio_root()
    root.mkdir(parents=True, exist_ok=True)
    stat = shutil.disk_usage(root)
    return stat.free


def build_audio_path(invitation_id: str, response_id: uuid.UUID, ext: str) -> Path:
    now = datetime.utcnow()
    rel = Path(str(now.year)) / str(now.month).zfill(2) / invitation_id / f"{response_id}{ext}"
    return rel


def validate_mime(data: bytes, claimed_mime: str) -> bool:
    claimed_mime = claimed_mime.split(";")[0].strip().lower()
    if claimed_mime not in ALLOWED_MIMES:
        return False
    signatures = MAGIC_BYTES.get(claimed_mime, [])
    if not signatures:
        return True
    return any(data[:len(sig)] == sig for sig in signatures)


async def save_audio(
    data: bytes,
    invitation_id: str,
    response_id: uuid.UUID,
    ext: str,
) -> tuple[Path, int]:
    root = _audio_root()
    rel_path = build_audio_path(invitation_id, response_id, ext)
    final_path = root / rel_path
    tmp_path = root / "tmp" / f"{response_id}{ext}"

    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(data)

    os.rename(tmp_path, final_path)
    final_path.chmod(0o640)

    return rel_path, len(data)


def delete_audio(rel_path: str) -> None:
    full = _audio_root() / rel_path
    try:
        full.unlink(missing_ok=True)
    except Exception:
        pass


def get_audio_full_path(rel_path: str) -> Path:
    return _audio_root() / rel_path


def mime_to_ext(mime: str) -> str:
    mime = mime.split(";")[0].strip().lower()
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
    }
    return mapping.get(mime, ".bin")
