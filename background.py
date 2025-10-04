import os
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal
from crud import create_alert
from schemas import AlertCreate  # Add this import (adjust 'schemas' to your actual module if needed)
from transformers import pipeline
import tweepy
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Sentiment Pipeline (DistilBERT for speed)
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Twitter Client
bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token=bearer_token) if bearer_token else None

def analyze_sentiment(text: str):
    result = sentiment_pipeline(text)[0]
    label = result['label'].lower()
    score = result['score']
    if label == 'negative':
        sentiment_str = 'negative'
        urgency = 'high' if score > 0.8 else 'medium'
    elif label == 'positive':
        sentiment_str = 'positive'
        urgency = 'low'
    else:
        sentiment_str = 'neutral'
        urgency = 'low'
    return sentiment_str, urgency, -score if label == 'negative' else score  # Numeric for avg

def generate_recommendation(sentiment: str, message: str):
    templates = {
        'negative': 'Apologize sincerely, offer immediate resolution (e.g., refund/replacement), and escalate to support team.',
        'neutral': 'Acknowledge feedback, ask for more details, and share how we\'re improving.',
        'positive': 'Thank the customer, encourage sharing more, and offer loyalty perks.'
    }
    return templates.get(sentiment, 'Thank you for your feedback. We value your input and will review this.')

def monitor_feeds():
    if not client:
        print("No Twitter token; skipping fetch.")
        return
    db = next(SessionLocal())
    try:
        query = os.getenv("BRAND_QUERY", "SentinelAI")
        tweets = client.search_recent_tweets(query=query, max_results=10, tweet_fields=['author_id', 'public_metrics', 'created_at'])
        if tweets.data:
            for tweet in tweets.data:
                sentiment_str, urgency, score = analyze_sentiment(tweet.text)
                if sentiment_str == 'negative':  # Flag only negative
                    author = tweets.includes['users'][0].username if tweets.includes and tweets.includes['users'] else 'Anonymous'
                    alert = AlertCreate(
                        customer=author,
                        platform='Twitter',
                        sentiment=sentiment_str,
                        urgency=urgency,
                        message=tweet.text,
                        reach=tweet.public_metrics['impression_count'] or 100,  # Mock if not available
                        engagement=tweet.public_metrics['like_count'] + tweet.public_metrics['retweet_count'],
                        recommended_response=generate_recommendation(sentiment_str, tweet.text)
                    )
                    new_alert = create_alert(db, alert)
                    print(f"New alert: {new_alert.message}")
                    # Trigger notification (Slack/Email)
                    notify_slack(new_alert)
                    notify_email(new_alert)
    except Exception as e:
        print(f"Monitoring error: {e}")
    finally:
        db.close()

# Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(monitor_feeds, 'interval', seconds=30)
scheduler.start()

def notify_slack(alert):
    import requests
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if webhook:
        requests.post(webhook, json={"text": f"🚨 {alert.urgency.upper()}: {alert.message[:100]}...\nRec: {alert.recommended_response}"})

def notify_email(alert):
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(f"Alert: {alert.message}\nRecommendation: {alert.recommended_response}")
    msg['Subject'] = f"SentinelAI Alert: {alert.urgency}"
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = "support@sentinelai.com"  # Configurable
    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), 587) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.send_message(msg)
    except Exception as e:
        print(f"Email error: {e}")