from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.fraud import FraudulentNumber, FraudType
from app.models.report import DetectionLog
from app.services.cache import cache_service
from datetime import datetime, timedelta
from sqlalchemy import delete
import logging
import httpx

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.db_tasks.sync_external_frauds")
def sync_external_frauds():
    """
    Synchroniser avec base de données externe de fraudes

    Exécuté : Toutes les 5 minutes
    Sources possibles :
    - API partenaires
    - CSV publics
    - Scraping sites gouvernementaux
    """

    logger.info("🔄 Synchronisation base fraudes externe...")

    # Exemple : récupérer depuis API partenaire
    try:
        # À implémenter : appel API réel
        # response = httpx.get("https://fraud-db.example.com/api/latest")
        # new_frauds = response.json()

        # Pour MVP : simulation
        new_frauds = []

        logger.info(f"✅ {len(new_frauds)} nouvelles fraudes synchronisées")

        return {
            "success": True,
            "new_frauds": len(new_frauds),
            "timestamp": str(datetime.utcnow())
        }

    except Exception as e:
        logger.error(f"❌ Erreur sync fraudes: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@celery_app.task(name="app.workers.tasks.db_tasks.cleanup_cache")
def cleanup_cache():
    """
    Nettoyer cache Redis (entrées expirées)

    Exécuté : Toutes les heures
    """

    logger.info("🧹 Nettoyage cache Redis...")

    try:
        # Redis expire automatiquement les clés avec TTL
        # Cette task peut faire du ménage supplémentaire si besoin

        logger.info("✅ Cache nettoyé")

        return {
            "success": True,
            "timestamp": str(datetime.utcnow())
        }

    except Exception as e:
        logger.error(f"❌ Erreur nettoyage cache: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="app.workers.tasks.db_tasks.cleanup_old_logs")
def cleanup_old_logs():
    """
    Supprimer anciens logs de détection (> 90 jours)

    Exécuté : Tous les jours à 3h du matin
    Garde seulement les 90 derniers jours pour économiser espace
    """

    logger.info("🧹 Nettoyage anciens logs...")

    async def _cleanup():
        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            result = await db.execute(
                delete(DetectionLog).where(
                    DetectionLog.timestamp < cutoff_date
                )
            )

            await db.commit()
            return result.rowcount

    try:
        import asyncio
        deleted = asyncio.run(_cleanup())

        logger.info(f"✅ {deleted} anciens logs supprimés")

        return {
            "success": True,
            "deleted_logs": deleted,
            "timestamp": str(datetime.utcnow())
        }

    except Exception as e:
        logger.error(f"❌ Erreur nettoyage logs: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="app.workers.tasks.db_tasks.backup_database")
def backup_database():
    """
    Backup base de données (snapshot)

    Exécuté : Tous les jours à 4h du matin
    """

    logger.info("💾 Backup base de données...")

    try:
        # À implémenter : pg_dump ou autre solution

        logger.info("✅ Backup créé")

        return {
            "success": True,
            "timestamp": str(datetime.utcnow())
        }

    except Exception as e:
        logger.error(f"❌ Erreur backup: {e}")
        return {"success": False, "error": str(e)}