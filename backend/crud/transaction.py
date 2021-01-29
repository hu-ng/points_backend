from sqlalchemy.orm import Session

from backend.schemas import TransactionIn
from backend.models import Transaction


def get_transaction(db: Session, transaction_id: str):
    """
    Returns a single transaction
    """
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def get_transactions(user_id, db: Session, skip: int = 0, limit: int = 10):
    """
    Returns all transactions with a limit and offset. If user is indicated, select all transactions for that user
    """
    if user_id:
        return db.query(Transaction).filter(Transaction.user_id == user_id).all()
    
    return db.query(Transaction).offset(skip).limit(limit).all()


def get_all_active_transactions(db: Session, user_id: str):
    """
    Get all transactions with unused points, sorted by old to late
    """
    return db.query(Transaction).\
        filter(Transaction.user_id == user_id, Transaction.points != Transaction.used_points).\
        order_by(Transaction.transaction_date).all()


def get_all_active_transactions_of_payer(db: Session, user_id: str, payer: str):
    """
    Get all transactions with unused positive points of a specific payer
    """
    return db.query(Transaction).\
        filter(Transaction.user_id == user_id, Transaction.points != Transaction.used_points, Transaction.payer == payer, Transaction.points > 0).\
        order_by(Transaction.transaction_date).all()


def create_transaction(db: Session, transaction: TransactionIn, user_id: str):
    """
    Create a transaction in the DB
    """
    db_transaction = Transaction(**transaction.dict(), user_id=user_id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction