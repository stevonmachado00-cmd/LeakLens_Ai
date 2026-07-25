from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.deps import get_current_user
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.statement import StatementResponse, TransactionResponse
from app.services.statement_service import StatementService


router = APIRouter()


@router.post("/upload", response_model=StatementResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
) -> StatementResponse:
    content = await file.read(settings.MAX_FILE_SIZE + 1)
    return StatementService.upload_csv_statement(
        db, user_id=current_user.id, file=file, content=content
    )


@router.get("", response_model=list[StatementResponse])
def list_statements(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StatementResponse]:
    return StatementService.list_statements(db, user_id=current_user.id)


@router.get("/{statement_id}/transactions", response_model=list[TransactionResponse])
def list_statement_transactions(
    *,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TransactionResponse]:
    return StatementService.list_transactions(
        db, statement_id=statement_id, user_id=current_user.id
    )


@router.get("/{statement_id}/download")
def download_statement(
    *,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the stored statement file for the current user.

    Returns a FileResponse with Content-Disposition attachment.
    """
    path, original_filename = StatementService.get_statement_file(
        db, user_id=current_user.id, statement_id=statement_id
    )
    # Ensure we return a proper FileResponse that sets Content-Disposition; filename argument
    # will be used for the attachment filename.
    return FileResponse(path, media_type="application/octet-stream", filename=original_filename)
