from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class AlertBase(BaseModel):
    customer: str
    platform: str
    sentiment: str
    urgency: str
    message: str
    reach: int = 0
    engagement: int = 0
    recommended_response: Optional[str] = None

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    status: str
    response_text: Optional[str] = None

class Alert(AlertBase):
    id: int
    timestamp: datetime
    status: str
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

class PlatformBase(BaseModel):
    name: str
    mentions: int
    sentiment_avg: float

class PlatformCreate(PlatformBase):
    pass

class Platform(PlatformBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class AnalyticsTrend(BaseModel):
    dates: List[str]
    sentiments: List[float]