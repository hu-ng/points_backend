from sqlalchemy import String, Integer, ForeignKey, Column, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from uuid import uuid4

from backend.database.config import Base


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    points = Column(Integer, nullable=False)
    used_points = Column(Integer, nullable=False, default=0)
    payer = Column(String, nullable=False)
    transaction_date = Column(DateTime)

    user_id = Column(String, ForeignKey("users.id"))
    user = relationship("User", back_populates="transactions")

    @hybrid_property
    def usable_points(self):
        return self.points - self.used_points

