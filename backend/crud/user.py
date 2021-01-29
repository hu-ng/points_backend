from sqlalchemy.orm import Session

from backend.schemas import UserIn, UserOut
from backend.models import User


def get_user(db: Session, user_id: str):
    """
    Returns a single user
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 10):
    """
    Returns all users with a limit and offset
    """
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserIn):
    """
    Create a user in the DB
    """
    db_user = User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user