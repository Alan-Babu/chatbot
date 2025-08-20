from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import existing models
from .models.user import User
from .models.dues import Due
from .models.payment import Payment
from .models.card import Card
from .models.receipt import Receipt

# Import existing models for backward compatibility
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class MessageFeedback(Base):
    __tablename__ = "message_feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, index=True, nullable=False)
    feedback = Column(String(20), nullable=False)  # 'up' | 'down'
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SessionFeedback(Base):
    __tablename__ = "session_feedback"

    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CacheEntry(Base):
    __tablename__ = "response_cache"

    id = Column(Integer, primary_key=True, index=True)
    query_key = Column(String(512), unique=True, index=True, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    ttl_seconds = Column(Integer, default=3600)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds or 0)


def init_db():
    """Initialize the database with all tables."""
    Base.metadata.create_all(bind=engine)
