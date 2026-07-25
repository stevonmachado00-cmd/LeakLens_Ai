from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def validate_statement_upload(file: UploadFile, content: bytes) -> str:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A filename is required.")
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Uploaded file exceeds the {settings.MAX_FILE_SIZE} byte limit.",
        )

    extension = Path(file.filename).suffix.lower()
    if extension not in settings.SUPPORTED_STATEMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV statement files are currently supported.",
        )
    return extension.removeprefix(".")


def save_statement_file(*, original_filename: str, content: bytes) -> str:
    extension = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid4().hex}{extension}"
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / stored_filename
    destination.write_bytes(content)
    return stored_filename


def get_statement_file_path(filename: str) -> Path:
    """Return a safe resolved path for a stored statement file inside the upload directory.

    Raises FileNotFoundError if the resolved path is outside the upload directory.
    """
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    destination = (upload_dir / filename)
    # Resolve without strict to allow non-existent targets (tests may remove files)
    destination_resolved = destination.resolve(strict=False)

    try:
        # Ensure the destination is within the upload directory to avoid directory traversal
        if upload_dir not in destination_resolved.parents and destination_resolved != upload_dir:
            raise FileNotFoundError("Requested file is outside of upload directory")
    except Exception:
        # Re-raise as FileNotFoundError for callers to translate into 404
        raise FileNotFoundError("Requested file is outside of upload directory")

    return destination_resolved
