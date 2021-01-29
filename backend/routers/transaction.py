from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from backend.crud import transaction as trans_crud
from backend.crud import user as user_crud
from backend.schemas import TransactionIn, TransactionOut
from backend import get_db


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/{user_id}", response_model=List[TransactionOut])
def get_transactions(user_id: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Route to grab all transactions
    """
    db_user = user_crud.get_user(db=db, user_id=user_id)
    if db_user:
        return trans_crud.get_transactions(db=db, skip=skip, limit=limit, user_id=user_id)
    
    raise HTTPException(status_code=400, detail="User does not exist")


@router.post("/{user_id}", response_model=TransactionOut)
def create_transaction(user_id: str, transaction: TransactionIn, db: Session = Depends(get_db)):
    """
    Route to create a new transaction
    """
    db_user = user_crud.get_user(db=db, user_id=user_id)

    if not db_user:
        raise HTTPException(status_code=400, detail="User does not exist")
    
    new_transaction = trans_crud.create_transaction(db=db, transaction=transaction, user_id=user_id)

    # If it has negative points, take off points from the oldest entries of the same payer
    if new_transaction.points < 0:
        # Get all transactions from this payer with positive points
        payer_transactions = trans_crud.get_all_active_transactions_of_payer(db=db, user_id=user_id, payer=new_transaction.payer)
        to_reduce = abs(new_transaction.points)

        # Reduce transactions until to_reduce is 0
        for transaction in payer_transactions:
            if transaction.usable_points >= to_reduce:
                transaction.used_points += to_reduce
                break
            # If usable points < to_reduce
            else:
                to_use = transaction.usable_points
                transaction.used_points += to_use
                to_reduce -= to_use
        new_transaction.used_points = new_transaction.points

        db.commit()
        db.refresh(new_transaction)
    
    return new_transaction

