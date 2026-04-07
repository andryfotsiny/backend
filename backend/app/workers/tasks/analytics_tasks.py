from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.analytics_service import analytics_service
from app.services.cache import cache_service
from datetime import datetime
import asyncio
import logging
import json

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.tasks.analytics_tasks.compute_metrics")
def compute_metrics():
    logger.info("Calcul metriques analytics...")

    async def _compute():
        async with AsyncSessionLocal() as db:
            global_stats = await analytics_service.get_global_stats(db)
            await cache_service.set(
                "analytics:global_stats",
                json.dumps(global_stats, default=str),
                ttl=600
            )
            timeline = await analytics_service.get_timeline_stats(db, "week")
            await cache_service.set(
                "analytics:timeline:week",
                json.dumps(timeline, default=str),
                ttl=600
            )
            trends = await analytics_service.get_fraud_trends(db)
            await cache_service.set(
                "analytics:trends",
                json.dumps(trends, default=str),
                ttl=600
            )
            return {
                "global_stats": global_stats,
                "timeline": timeline,
                "trends": trends
            }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        metrics = loop.run_until_complete(_compute())
        loop.close()
        logger.info("Metriques calculees et mises en cache")
        return {
            "success": True,
            "total_frauds": metrics["global_stats"].get("total_frauds", 0),
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Erreur calcul metriques: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task(name="app.workers.tasks.analytics_tasks.generate_report")
def generate_report(period: str = "week"):
    logger.info(f"Generation rapport {period}...")

    async def _generate():
        async with AsyncSessionLocal() as db:
            timeline = await analytics_service.get_timeline_stats(db, period)
            global_stats = await analytics_service.get_global_stats(db)
            return {
                "period": period,
                "generated_at": datetime.utcnow().isoformat(),
                "stats": global_stats,
                "timeline": timeline
            }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        report = loop.run_until_complete(_generate())
        loop.close()
        logger.info("Rapport genere")
        return {
            "success": True,
            "report": report,
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"Erreur generation rapport: {e}")
        return {"success": False, "error": str(e)}