from typing import Optional

from sqlalchemy.orm import Session

from app.models.statement import Statement, StatementStatus


class StatementRepository:
    @staticmethod
    def create(
        db: Session,
        *,
        user_id: int,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
    ) -> Statement:
        statement = Statement(
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            status=StatementStatus.UPLOADED,
        )
        db.add(statement)
        db.commit()
        db.refresh(statement)
        return statement

    @staticmethod
    def get_for_user(db: Session, *, statement_id: int, user_id: int) -> Optional[Statement]:
        return (
            db.query(Statement)
            .filter(Statement.id == statement_id, Statement.user_id == user_id)
            .first()
        )

    @staticmethod
    def list_for_user(db: Session, *, user_id: int) -> list[Statement]:
        return (
            db.query(Statement)
            .filter(Statement.user_id == user_id)
            .order_by(Statement.uploaded_at.desc())
            .all()
        )

    @staticmethod
    def set_status(db: Session, *, statement: Statement, status: StatementStatus) -> Statement:
        statement.status = status
        db.commit()
        db.refresh(statement)
        return statement
