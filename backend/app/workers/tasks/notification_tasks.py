from app.workers.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.tasks.notification_tasks.send_fraud_alerts")
def send_fraud_alerts():
    logger.info("Envoi alertes fraude...")
    return {"success": True}

@celery_app.task(name="app.workers.tasks.notification_tasks.send_notification")
def send_notification(user_id: str, message: str):
    logger.info(f"Notification envoyee a {user_id}")
    return {"success": True}