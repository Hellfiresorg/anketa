from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.transcription import TranscriptionError, check_audio_duration, transcribe_audio


def test_check_duration_ffprobe_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = check_audio_duration(Path("/tmp/test.webm"))
    assert result is None


def test_check_duration_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "2.5\n"
    with patch("subprocess.run", return_value=mock_result):
        result = check_audio_duration(Path("/tmp/test.webm"))
    assert result == 2.5


def test_check_duration_ffprobe_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        result = check_audio_duration(Path("/tmp/test.webm"))
    assert result is None


@pytest.mark.asyncio
async def test_transcribe_too_short():
    mock_duration = MagicMock()
    mock_duration.returncode = 0
    mock_duration.stdout = "0.3\n"

    with patch("subprocess.run", return_value=mock_duration):
        with pytest.raises(TranscriptionError) as exc_info:
            await transcribe_audio(Path("/tmp/test.webm"))
    assert "слишком короткая" in str(exc_info.value)
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_transcribe_too_long():
    mock_duration = MagicMock()
    mock_duration.returncode = 0
    mock_duration.stdout = "400.0\n"

    with patch("subprocess.run", return_value=mock_duration):
        with pytest.raises(TranscriptionError) as exc_info:
            await transcribe_audio(Path("/tmp/test.webm"))
    assert "максимальную длительность" in str(exc_info.value)
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_transcribe_rate_limit_is_retryable():
    mock_duration = MagicMock()
    mock_duration.returncode = 0
    mock_duration.stdout = "5.0\n"

    mock_error = Exception("rate limit")
    mock_error.status_code = 429

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create.side_effect = mock_error

    with patch("subprocess.run", return_value=mock_duration):
        with patch("app.services.transcription.AsyncGroq", return_value=mock_client):
            with patch("builtins.open", MagicMock(return_value=MagicMock(read=lambda: b"data", __enter__=lambda s: s, __exit__=MagicMock()))):
                with pytest.raises(TranscriptionError) as exc_info:
                    await transcribe_audio(Path("/tmp/test.webm"))
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_transcribe_4xx_not_retryable():
    mock_duration = MagicMock()
    mock_duration.returncode = 0
    mock_duration.stdout = "5.0\n"

    mock_error = Exception("bad request")
    mock_error.status_code = 400

    mock_client = AsyncMock()
    mock_client.audio.transcriptions.create.side_effect = mock_error

    with patch("subprocess.run", return_value=mock_duration):
        with patch("app.services.transcription.AsyncGroq", return_value=mock_client):
            with patch("builtins.open", MagicMock(return_value=MagicMock(read=lambda: b"data", __enter__=lambda s: s, __exit__=MagicMock()))):
                with pytest.raises(TranscriptionError) as exc_info:
                    await transcribe_audio(Path("/tmp/test.webm"))
    assert exc_info.value.retryable is False
