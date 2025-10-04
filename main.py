from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db
from models import Base, Alert, Platform
from schemas import Alert, AlertCreate, AlertUpdate, Platform, AnalyticsTrend
from crud import get_alerts, create_alert, update_alert, get_critical_alerts, get_platforms, create_platform, get_analytics_trend
import smtplib
from email.mime.text import MIMEText
import requests
import os
from dotenv import load_dotenv
from background import scheduler, notify_slack, notify_email  # Starts monitoring

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SentinelAI Backend - Real-Time Sentiment Alerts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

def broadcast_alert(alert: Alert):
    if connected_clients:
        for client in connected_clients:
            client.send_json({"type": "newAlert", "data": alert.dict()})

# Alerts Endpoints
@app.get("/api/alerts", response_model=list[Alert])
def read_alerts(sentiment: str = None, search: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_alerts(db, skip=skip, limit=limit, sentiment=sentiment, search=search)

@app.post("/api/alerts", response_model=Alert)
def create_manual_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    new_alert = create_alert(db, alert)
    broadcast_alert(new_alert)
    notify_slack(new_alert)
    notify_email(new_alert)
    return new_alert

@app.put("/api/alerts/{alert_id}", response_model=Alert)
def update_alert_endpoint(alert_id: int, update: AlertUpdate, db: Session = Depends(get_db)):
    db_alert = update_alert(db, alert_id, update)
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if update.status == 'resolved':
        notify_email(db_alert)  # Notify on resolve
    return db_alert

@app.get("/api/critical-alerts", response_model=list[Alert])
def read_critical_alerts(limit: int = 5, db: Session = Depends(get_db)):
    return get_critical_alerts(db, limit)

# Platforms
@app.get("/api/platforms", response_model=list[Platform])
def read_platforms(db: Session = Depends(get_db)):
    return get_platforms(db)

# Analytics
@app.get("/api/analytics/trend", response_model=AnalyticsTrend)
def read_trend(days: int = 7, db: Session = Depends(get_db)):
    return get_analytics_trend(db, days)

# Settings (Mock persistent; extend with model)
@app.get("/api/settings/thresholds")
def get_thresholds():
    return [
        {"label": "High Priority Threshold", "value": "85"},
        {"label": "Medium Priority Threshold", "value": "60"},
        {"label": "Minimum Reach for Alert", "value": "500"},
        {"label": "Sentiment Score Threshold", "value": "-0.7"}
    ]

@app.put("/api/settings/thresholds")
def update_thresholds(thresholds: list):
    # Save to DB or config file
    print("Thresholds updated:", thresholds)
    return {"success": True}

# Monitoring (Static for now; dynamic via background)
@app.get("/api/monitors")
def get_monitors():
    return ["Twitter #brand", "Product Reviews", "Support Forums", "Facebook Page", "Reddit r/products"]

@app.get("/api/channels")
def get_channels():
    return [
        {"name": "Slack #support", "status": "Connected", "type": "connected"},
        {"name": "Email Alerts", "status": "Connected", "type": "connected"},
        {"name": "SMS Notifications", "status": "Enabled", "type": "enabled"},
        {"name": "Webhook API", "status": "Connected", "type": "connected"}
    ]

@app.get("/api/keywords")
def get_keywords():
    return ['refund', 'broken', 'terrible', 'disappointed', 'worst', 'scam', 'lawsuit', 'never again', 'poor quality', 'unacceptable']

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)