from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from datetime import timezone

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

    if not db_user:
        raise HTTPException(status_code=400, detail="User does not exist")
        
    return trans_crud.get_transactions(db=db, skip=skip, limit=limit, user_id=user_id)


@router.post("/{user_id}", response_model=TransactionOut)
def create_transaction(user_id: str, transaction: TransactionIn, db: Session = Depends(get_db)):
    """
    Route to create a new transaction
    """
    db_user = user_crud.get_user(db=db, user_id=user_id)

    if not db_user:
        raise HTTPException(status_code=400, detail="User does not exist")

    payer_transactions = trans_crud.get_all_active_transactions_of_payer(db=db, user_id=user_id, payer=transaction.payer)

    # If the current balance for this payer is less than amount being subtracted
    if transaction.points < 0 and sum([t.usable_points for t in payer_transactions]) + transaction.points < 0:
        raise HTTPException(status_code=400, detail="Invalid transaction with negative points: amount exceeds current balance for this payer")
    
    # For this implementation and for simplicity, all new transactions should follow each other chronologically (more in README)
    if db_user.transactions:
        # Make the date timezone-aware for comparison
        last_transaction_time = db_user.transactions[-1].transaction_date
        last_transaction_time = last_transaction_time.replace(tzinfo=timezone.utc)
        if transaction.transaction_date < last_transaction_time:
            raise HTTPException(status_code=400, detail="New transactions must occur after the last recorded transaction")
    
    new_transaction = trans_crud.create_transaction(db=db, transaction=transaction, user_id=user_id)

    # If the added transaction has negative points, take off points from the oldest entries of the same payer
    if new_transaction.points < 0:
        # Get all transactions from this payer with positive points
        payer_transactions = trans_crud.get_all_active_transactions_of_payer(db=db, user_id=user_id, payer=new_transaction.payer)
        to_reduce = abs(new_transaction.points)

        # Reduce transactions until to_reduce is 0
        for transaction in payer_transactions:
            # If can use all points, do so
            if transaction.usable_points >= to_reduce:
                transaction.used_points += to_reduce
                break
            # If not, reduce from current transaction and calc what's left
            else:
                to_use = transaction.usable_points
                transaction.used_points += to_use
                to_reduce -= to_use

        # Mark the transaction as used
        new_transaction.used_points = new_transaction.points

        db.commit()
        db.refresh(new_transaction)
    
    return new_transaction

