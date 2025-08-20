from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from db.new_db import SessionLocal
from services.auth_service import get_current_user
from services.payment_service import payment_service
from db.models.dues import Due
from db.models.payment import Payment

router = APIRouter(prefix="/dues", tags=["dues"])

# Pydantic models
class DueCreate(BaseModel):
    title: str
    description: Optional[str] = None
    amount: Decimal
    due_date: datetime

class DueResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    amount: Decimal
    due_date: datetime
    status: str
    created_at: datetime

class PaymentRequest(BaseModel):
    due_id: int
    amount: Decimal
    payment_method_id: str

class PaymentResponse(BaseModel):
    id: int
    amount: Decimal
    status: str
    created_at: datetime
    stripe_payment_intent_id: str

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[DueResponse])
async def get_user_dues(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all dues for the current user."""
    dues = db.query(Due).filter(Due.user_id == current_user["user_id"]).all()
    return [
        DueResponse(
            id=due.id,
            title=due.title,
            description=due.description,
            amount=due.amount,
            due_date=due.due_date,
            status=due.status,
            created_at=due.created_at
        )
        for due in dues
    ]

@router.post("/", response_model=DueResponse)
async def create_due(
    due: DueCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new due."""
    db_due = Due(
        user_id=current_user["user_id"],
        title=due.title,
        description=due.description,
        amount=due.amount,
        due_date=due.due_date
    )
    db.add(db_due)
    db.commit()
    db.refresh(db_due)
    
    return DueResponse(
        id=db_due.id,
        title=db_due.title,
        description=db_due.description,
        amount=db_due.amount,
        due_date=db_due.due_date,
        status=db_due.status,
        created_at=db_due.created_at
    )

@router.get("/{due_id}", response_model=DueResponse)
async def get_due(
    due_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific due."""
    due = db.query(Due).filter(
        Due.id == due_id,
        Due.user_id == current_user["user_id"]
    ).first()
    
    if not due:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Due not found"
        )
    
    return DueResponse(
        id=due.id,
        title=due.title,
        description=due.description,
        amount=due.amount,
        due_date=due.due_date,
        status=due.status,
        created_at=due.created_at
    )

@router.post("/{due_id}/pay", response_model=PaymentResponse)
async def pay_due(
    due_id: int,
    payment_request: PaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process payment for a due."""
    due = db.query(Due).filter(
        Due.id == due_id,
        Due.user_id == current_user["user_id"]
    ).first()
    
    if not due:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Due not found"
        )
    
    if due.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due already paid"
        )
    
    # Process payment
    payment = payment_service.process_payment(
        db=db,
        user_id=current_user["user_id"],
        due_id=due_id,
        amount=payment_request.amount,
        payment_method_id=payment_request.payment_method_id
    )
    
    return PaymentResponse(
        id=payment.id,
        amount=payment.amount,
        status=payment.status,
        created_at=payment.created_at,
        stripe_payment_intent_id=payment.stripe_payment_intent_id
    )

@router.get("/{due_id}/payments", response_model=List[PaymentResponse])
async def get_due_payments(
    due_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all payments for a specific due."""
    payments = db.query(Payment).filter(
        Payment.due_id == due_id,
        Payment.user_id == current_user["user_id"]
    ).all()
    
    return [
        PaymentResponse(
            id=payment.id,
            amount=payment.amount,
            status=payment.status,
            created_at=payment.created_at,
            stripe_payment_intent_id=payment.stripe_payment_intent_id
        )
        for payment in payments
    ]
