import stripe
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
from db.models.payment import Payment
from db.models.dues import Due
from db.models.card import Card
from db.models.receipt import Receipt

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_your_stripe_key_here")

class PaymentService:
    def __init__(self):
        self.stripe = stripe
    
    def create_payment_intent(self, amount: Decimal, currency: str = "usd", 
                            customer_id: Optional[str] = None, 
                            payment_method_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a payment intent with Stripe."""
        try:
            intent_data = {
                "amount": int(amount * 100),  # Convert to cents
                "currency": currency,
                "automatic_payment_methods": {"enabled": True}
            }
            
            if customer_id:
                intent_data["customer"] = customer_id
            
            if payment_method_id:
                intent_data["payment_method"] = payment_method_id
                intent_data["confirm"] = True
            
            intent = stripe.PaymentIntent.create(**intent_data)
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "status": intent.status
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_customer(self, email: str, name: Optional[str] = None) -> str:
        """Create a Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            return customer.id
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def add_payment_method(self, customer_id: str, payment_method_id: str) -> Dict[str, Any]:
        """Add payment method to customer."""
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            return {
                "id": payment_method.id,
                "card": {
                    "last4": payment_method.card.last4,
                    "brand": payment_method.card.brand,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year
                }
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def get_payment_methods(self, customer_id: str) -> list:
        """Get all payment methods for a customer."""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            return [
                {
                    "id": pm.id,
                    "last4": pm.card.last4,
                    "brand": pm.card.brand,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year
                }
                for pm in payment_methods.data
            ]
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def process_payment(self, db: Session, user_id: int, due_id: int, 
                       amount: Decimal, payment_method_id: str) -> Payment:
        """Process payment for a due."""
        due = db.query(Due).filter(Due.id == due_id, Due.user_id == user_id).first()
        if not due:
            raise Exception("Due not found")
        
        if due.status == "paid":
            raise Exception("Due already paid")
        
        # Create payment intent
        payment_intent = self.create_payment_intent(
            amount=amount,
            payment_method_id=payment_method_id
        )
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            due_id=due_id,
            amount=amount,
            stripe_payment_intent_id=payment_intent["payment_intent_id"],
            status="processing"
        )
        
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        return payment
    
    def confirm_payment(self, db: Session, payment_intent_id: str) -> Payment:
        """Confirm payment completion."""
        payment = db.query(Payment).filter(
            Payment.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if not payment:
            raise Exception("Payment not found")
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == "succeeded":
                payment.status = "completed"
                payment.due.status = "paid"
                
                # Create receipt
                receipt = Receipt(
                    payment_id=payment.id,
                    receipt_number=f"RCP-{payment.id:06d}",
                    amount=payment.amount
                )
                db.add(receipt)
                
            elif intent.status in ["requires_payment_method", "payment_failed"]:
                payment.status = "failed"
                payment.failure_reason = intent.last_payment_error.message if intent.last_payment_error else "Payment failed"
            
            db.commit()
            return payment
            
        except stripe.error.StripeError as e:
            payment.status = "failed"
            payment.failure_reason = str(e)
            db.commit()
            raise Exception(f"Stripe error: {str(e)}")

# Initialize payment service
payment_service = PaymentService()
