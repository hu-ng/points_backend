from sqlalchemy import String, Column
from sqlalchemy.orm import relationship

from uuid import uuid4

from backend.database.config import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)

    transactions = relationship("Transaction", back_populates="user")