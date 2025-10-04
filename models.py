from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    customer = Column(String, nullable=False)  # e.g., tweet author
    platform = Column(String, nullable=False)  # Twitter, Reddit, etc.
    sentiment = Column(String, nullable=False)  # negative, neutral, positive
    urgency = Column(String, nullable=False)  # high, medium, low
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")  # pending, in-progress, resolved
    reach = Column(Integer, default=0)
    engagement = Column(Integer, default=0)
    recommended_response = Column(Text)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    mentions = Column(Integer, default=0)
    sentiment_avg = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())