from pydantic import BaseModel, Field
from datetime import datetime


class TransactionBase(BaseModel):
    payer: str
    points: int
    transaction_date: datetime = Field(default_factory=datetime.utcnow)


class TransactionIn(TransactionBase):
    pass


class TransactionOut(TransactionBase):
    id: str
    used_points: int
    usable_points: int

    class Config:
        orm_mode = True