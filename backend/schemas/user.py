from pydantic import BaseModel
from typing import List

from .transaction import TransactionOut


class UserBase(BaseModel):
    name: str
    email: str


class UserIn(UserBase):
    pass


class UserOut(UserBase):
    id: str
    transactions: List[TransactionOut] = []

    class Config:
        orm_mode = True