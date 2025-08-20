from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from db.db import Base
import enum

class DuesStatus(enum.Enum):
    PENDING = "pending"
    OVERDUE = "overdue"
    PAID = "paid"
    PARTIAL = "partial"

class Dues(Base):
    __tablename__ = "dues"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(DuesStatus), default=DuesStatus.PENDING)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="dues")
    payments = relationship("Payment", back_populates="dues")
