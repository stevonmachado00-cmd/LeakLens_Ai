from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.statement import Statement, StatementStatus, Transaction
from app.schemas.transaction import ParsedTransaction


class TransactionRepository:
    @staticmethod
    def create_many(
        db: Session, *, statement_id: int, transactions: Sequence[ParsedTransaction]
    ) -> list[Transaction]:
        records = [
            Transaction(
                statement_id=statement_id,
                date=transaction.date,
                merchant=transaction.merchant,
                description=transaction.description,
                amount=transaction.amount,
                currency=transaction.currency,
                category=transaction.category,
            )
            for transaction in transactions
        ]
        db.add_all(records)
        db.commit()
        return records

    @staticmethod
    def list_for_statement(db: Session, *, statement_id: int) -> list[Transaction]:
        return (
            db.query(Transaction)
            .filter(Transaction.statement_id == statement_id)
            .order_by(Transaction.date.asc(), Transaction.id.asc())
            .all()
        )

    @staticmethod
    def list_for_user(db: Session, *, user_id: int) -> list[Transaction]:
        return (
            db.query(Transaction)
            .join(Statement, Transaction.statement_id == Statement.id)
            .filter(Statement.user_id == user_id, Statement.status == StatementStatus.PROCESSED)
            .order_by(Transaction.date.asc(), Transaction.id.asc())
            .all()
        )
