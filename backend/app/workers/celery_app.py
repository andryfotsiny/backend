from celery import Celery
from celery.schedules import crontab
import os

# Configuration Redis pour Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Créer app Celery
celery_app = Celery(
    "dyleth_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.tasks.ml_tasks",
        "app.workers.tasks.db_tasks",
        "app.workers.tasks.analytics_tasks",
        "app.workers.tasks.notification_tasks"
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 heure max par task
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True
)

# Scheduler (Celery Beat)
celery_app.conf.beat_schedule = {
    # Re-entraînement ML quotidien
    "retrain-ml-models-daily": {
        "task": "app.workers.tasks.ml_tasks.retrain_models",
        "schedule": crontab(hour=2, minute=0),  # 2h du matin
    },

    # Mise à jour DB externe (toutes les 5 minutes)
    "sync-fraud-database": {
        "task": "app.workers.tasks.db_tasks.sync_external_frauds",
        "schedule": crontab(minute="*/5"),
    },

    # Nettoyage cache (toutes les heures)
    "cleanup-cache": {
        "task": "app.workers.tasks.db_tasks.cleanup_cache",
        "schedule": crontab(minute=0),
    },

    # Calcul métriques analytics (toutes les 10 minutes)
    "compute-analytics": {
        "task": "app.workers.tasks.analytics_tasks.compute_metrics",
        "schedule": crontab(minute="*/10"),
    },

    # Nettoyage anciens logs (tous les jours)
    "cleanup-old-logs": {
        "task": "app.workers.tasks.db_tasks.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0),
    },

    # Notifications push (toutes les heures)
    "send-fraud-alerts": {
        "task": "app.workers.tasks.notification_tasks.send_fraud_alerts",
        "schedule": crontab(minute=0),
    },
}

# Routes des tasks
celery_app.conf.task_routes = {
    "app.workers.tasks.ml_tasks.*": {"queue": "ml"},
    "app.workers.tasks.db_tasks.*": {"queue": "db"},
    "app.workers.tasks.analytics_tasks.*": {"queue": "analytics"},
    "app.workers.tasks.notification_tasks.*": {"queue": "notifications"},
}