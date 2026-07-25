from app.database.session import SessionLocal
from app.models.statement import Statement
from app.models.user import User

if __name__ == '__main__':
    db = SessionLocal()
    users = db.query(User).all()
    print('Users:')
    for u in users:
        print(' id=', u.id, ' email=', u.email)
    stmts = db.query(Statement).all()
    print('\nStatements:')
    for s in stmts:
        print(' id=', s.id, 'user_id=', s.user_id, 'status=', s.status, 'file_name=', s.file_name)
    db.close()
