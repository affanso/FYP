from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from datetime import datetime




class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)

    def get_id(self):
        return self.user_id

    
    # Relationships
    sessions = relationship("Session", back_populates="user")

class Session(db.Model):
    __tablename__ = 'sessions'
    
    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.user_id'))
    start_time: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    therapy_responses = relationship("TherapyResponse", back_populates="session")

class Message(db.Model):
    __tablename__ = 'messages'
    
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey('sessions.session_id'))
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'user' or 'bot'
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    emotions = relationship("Emotion", back_populates="message")

class Emotion(db.Model):
    __tablename__ = 'emotions'
    
    emotion_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey('messages.message_id'))
    emotion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="emotions")

class TherapyResponse(db.Model):
    __tablename__ = 'therapy_responses'
    
    response_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey('sessions.session_id'))
    response_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="therapy_responses")