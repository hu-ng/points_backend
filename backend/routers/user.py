from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.orm import Session

from backend.crud import user as user_crud
from backend.crud import transaction as trans_crud
from backend.schemas import UserIn, UserOut
from backend import get_db


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut)
def create_user(user: UserIn, db: Session = Depends(get_db)):
    """
    Create user
    """
    existing_user = user_crud.get_user_by_email(db=db, email = user.email)

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return user_crud.create_user(db=db, user=user)


@router.get("/", response_model=List[UserOut])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get all users
    """
    users = user_crud.get_users(db=db, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """
    Get specific user
    """
    existing_user = user_crud.get_user(db=db, user_id=user_id)

    if not existing_user:
        raise HTTPException(status_code=400, detail="User does not exist")

    return existing_user


@router.get("/{user_id}/balance")
def get_points_balance(user_id: str, db: Session = Depends(get_db)):
    """
    Get point balance per payer for the user
    """
    db_user = user_crud.get_user(db=db, user_id=user_id)

    if not db_user:
        raise HTTPException(status_code=400, detail="User does not exist")

    user_transactions = db_user.transactions
    balance = defaultdict(int)

    for transaction in user_transactions:
        balance[transaction.payer] += transaction.points - transaction.used_points
    
    return balance


@router.post("/{user_id}/deduct")
def deduct_points_from_balance(user_id: str, deduct_amount: int = Query(..., gt=0), db: Session = Depends(get_db)):
    """
    Deduct points from transactions with unused positive points from oldest to latest
    """
    db_user = user_crud.get_user(db=db, user_id=user_id)

    if not db_user:
        raise HTTPException(status_code=400, detail="User does not exist")
    
    response = defaultdict(int)

    # Get all active transactions for this user
    active_transactions = trans_crud.get_all_active_transactions(db=db, user_id=user_id)

    for transaction in active_transactions:
        payer, usable_points = transaction.payer, transaction.usable_points
        amount_left = deduct_amount - usable_points

        # If there is still anything left to deduct, that means we used all of the available points for this transaction
        if amount_left > 0:
            transaction.used_points += usable_points
            response[payer] -= usable_points

        # If there is nothing left (or negative), this means the amount we used is equal to deduct_amount
        else:
            transaction.used_points += deduct_amount
            response[payer] -= deduct_amount
        
        deduct_amount = amount_left

        if deduct_amount <= 0:
            break

    # If there are still points to reduce, this means user doesn't have enough points
    if deduct_amount > 0:
        raise HTTPException(status_code=400, detail="This user does not have enough points to deduct")

    # Changes were valid, so commit
    db.commit()
    return response