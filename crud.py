from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models import Alert, Platform
from schemas import AlertCreate, AlertUpdate, PlatformCreate
from datetime import datetime

def get_alerts(db: Session, skip: int = 0, limit: int = 100, sentiment: str = None, search: str = None):
    query = db.query(Alert).order_by(Alert.timestamp.desc())
    if sentiment and sentiment != 'all':
        query = query.filter(Alert.sentiment == sentiment)
    if search:
        query = query.filter(or_(Alert.customer.ilike(f"%{search}%"), Alert.message.ilike(f"%{search}%")))
    return query.offset(skip).limit(limit).all()

def create_alert(db: Session, alert: AlertCreate):
    db_alert = Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def update_alert(db: Session, alert_id: int, update: AlertUpdate):
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if db_alert:
        for key, value in update.dict(exclude_unset=True).items():
            setattr(db_alert, key, value)
        if update.status == 'resolved':
            db_alert.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(db_alert)
    return db_alert

def get_critical_alerts(db: Session, limit: int = 5):
    return db.query(Alert).filter(Alert.urgency == 'high').order_by(Alert.timestamp.desc()).limit(limit).all()

def get_platforms(db: Session):
    # Aggregate from alerts if no direct data
    platforms = db.query(Platform).all()
    if not platforms:
        # Compute on fly
        from sqlalchemy import func
        agg = db.query(
            Alert.platform,
            func.count(Alert.id).label('mentions'),
            func.avg(Alert.sentiment).label('sentiment_avg')  # Mock numeric sentiment
        ).group_by(Alert.platform).all()
        for p in agg:
            create_platform(db, PlatformCreate(name=p.platform, mentions=p.mentions, sentiment_avg=float(p.sentiment_avg or 0)))
        platforms = db.query(Platform).all()
    return platforms

def create_platform(db: Session, platform: PlatformCreate):
    db_platform = Platform(**platform.dict())
    db.add(db_platform)
    db.commit()
    db.refresh(db_platform)
    return db_platform

class AnalyticsTrend:
    def __init__(self, dates, sentiments):
        self.dates = dates
        self.sentiments = sentiments

def get_analytics_trend(db: Session, days: int = 7):
    from datetime import datetime, timedelta
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    trends = db.query(
        func.date(Alert.timestamp).label('date'),
        func.avg(Alert.sentiment).label('avg_sentiment')  # Assume sentiment as numeric for avg
    ).filter(Alert.timestamp >= start).group_by(func.date(Alert.timestamp)).all()
    return AnalyticsTrend(
        dates=[t.date.strftime('%Y-%m-%d') for t in trends],
        sentiments=[float(t.avg_sentiment or 0) for t in trends]
    )