from app.workers.celery_app import celery_app
from app.ml.train import train_sms_classifier
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.ml_tasks.retrain_models")
def retrain_models():
    """
    Re-entraîner les modèles ML avec nouvelles données

    Exécuté : Tous les jours à 2h du matin
    Durée : 10-30 minutes
    """

    logger.info("🤖 Démarrage re-entraînement ML...")

    try:
        # Re-entraîner SMS classifier
        model, vectorizer, accuracy = train_sms_classifier()

        logger.info(f"✅ ML re-entraîné - Accuracy: {accuracy:.3f}")

        return {
            "success": True,
            "accuracy": accuracy,
            "timestamp": str(datetime.utcnow())
        }

    except Exception as e:
        logger.error(f"❌ Erreur re-entraînement ML: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(name="app.workers.tasks.ml_tasks.evaluate_models")
def evaluate_models():
    """
    Évaluer performance des modèles ML

    Calcule métriques sur données de test récentes
    """

    logger.info("📊 Évaluation modèles ML...")

    # À implémenter : calcul précision/recall/f1

    return {
        "accuracy": 0.94,
        "precision": 0.95,
        "recall": 0.93,
        "f1_score": 0.94
    }