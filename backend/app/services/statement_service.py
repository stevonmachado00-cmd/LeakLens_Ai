from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.statement import Statement, StatementStatus, Transaction
from app.repositories.statement_repository import StatementRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.csv_parser_service import StatementParseError, parse_csv_transactions
from app.utils.file_storage import save_statement_file, validate_statement_upload


class StatementService:
    @staticmethod
    def upload_csv_statement(
        db: Session, *, user_id: int, file: UploadFile, content: bytes
    ) -> Statement:
        file_type = validate_statement_upload(file, content)
        stored_filename = save_statement_file(
            original_filename=file.filename or "statement.csv", content=content
        )
        statement = StatementRepository.create(
            db,
            user_id=user_id,
            filename=stored_filename,
            original_filename=file.filename or stored_filename,
            file_type=file_type,
            file_size=len(content),
        )
        StatementRepository.set_status(
            db, statement=statement, status=StatementStatus.PROCESSING
        )

        try:
            transactions = parse_csv_transactions(content)
            TransactionRepository.create_many(
                db, statement_id=statement.id, transactions=transactions
            )
        except StatementParseError as exc:
            StatementRepository.set_status(db, statement=statement, status=StatementStatus.FAILED)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
        except Exception:
            db.rollback()
            StatementRepository.set_status(db, statement=statement, status=StatementStatus.FAILED)
            raise

        return StatementRepository.set_status(
            db, statement=statement, status=StatementStatus.PROCESSED
        )

    @staticmethod
    def get_statement_file(db: Session, *, user_id: int, statement_id: int):
        """Validate ownership and return (Path to stored file, original filename).

        Raises HTTPException(404) when statement not found or file missing/outside upload dir.
        """
        statement = StatementRepository.get_for_user(db, statement_id=statement_id, user_id=user_id)
        if not statement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")

        from app.utils.file_storage import get_statement_file_path

        try:
            path = get_statement_file_path(statement.filename)
        except FileNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement file not found")

        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement file not found")

        return path, statement.original_filename

    @staticmethod
    def list_statements(db: Session, *, user_id: int) -> list[Statement]:
        return StatementRepository.list_for_user(db, user_id=user_id)

    @staticmethod
    def list_transactions(
        db: Session, *, statement_id: int, user_id: int
    ) -> list[Transaction]:
        statement = StatementRepository.get_for_user(
            db, statement_id=statement_id, user_id=user_id
        )
        if not statement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statement not found")
        return TransactionRepository.list_for_statement(db, statement_id=statement.id)
