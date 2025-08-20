from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from db.new_db import SessionLocal
from services.auth_service import get_current_user
from services.payment_service import payment_service
from db.models.payment import Payment
from db.models.card import Card

router = APIRouter(prefix="/payments", tags=["payments"])

# Pydantic models
class CardCreate(BaseModel):
    payment_method_id: str
    is_default: bool = False

class CardResponse(BaseModel):
    id: int
    last4: str
    brand: str
    exp_month: int
    exp_year: int
    is_default: bool

class PaymentCreate(BaseModel):
    due_id: int
    amount: Decimal
    payment_method_id: str

class PaymentResponse(BaseModel):
    id: int
    amount: Decimal
    status: str
    created_at: str
    stripe_payment_intent_id: str

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/cards", response_model=List[CardResponse])
async def get_user_cards(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all cards for the current user."""
    cards = db.query(Card).filter(Card.user_id == current_user["user_id"]).all()
    return [
        CardResponse(
            id=card.id,
            last4=card.last4,
            brand=card.brand,
            exp_month=card.exp_month,
            exp_year=card.exp_year,
            is_default=card.is_default
        )
        for card in cards
    ]

@router.post("/cards", response_model=CardResponse)
async def add_card(
    card: CardCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new card for the current user."""
    # Get card details from Stripe
    import stripe
    payment_method = stripe.PaymentMethod.retrieve(card.payment_method_id)
    
    db_card = Card(
        user_id=current_user["user_id"],
        card_token=card.payment_method_id,
        last4=payment_method.card.last4,
        brand=payment_method.card.brand,
        exp_month=payment_method.card.exp_month,
        exp_year=payment_method.card.exp_year,
        is_default=card.is_default
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    
    return CardResponse(
        id=db_card.id,
        last4=db_card.last4,
        brand=db_card.brand,
        exp_month=db_card.exp_month,
        exp_year=db_card.exp_year,
        is_default=db_card.is_default
    )

@router.get("/history", response_model=List[PaymentResponse])
async def get_payment_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment history for the current user."""
    payments = db.query(Payment).filter(Payment.user_id == current_user["user_id"]).all()
    return [
        PaymentResponse(
            id=payment.id,
            amount=payment.amount,
            status=payment.status,
            created_at=payment.created_at.isoformat(),
            stripe_payment_intent_id=payment.stripe_payment_intent_id
        )
        for payment in payments
    ]

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: dict, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    import stripe
    
    event = request
    
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        payment = db.query(Payment).filter(
            Payment.stripe_payment_intent_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = "completed"
            payment.due.status = "paid"
            db.commit()
    
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        payment = db.query(Payment).filter(
            Payment.stripe_payment_intent_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = "failed"
            payment.failure_reason = payment_intent.get("last_payment_error", {}).get("message")
            db.commit()
    
    return {"status": "success"}
