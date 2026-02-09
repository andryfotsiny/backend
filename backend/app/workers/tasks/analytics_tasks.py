from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.analytics_service import analytics_service
from app.services.cache import cache_service
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.analytics_tasks.compute_metrics")
def compute_metrics():
    """
    Pré-calculer métriques analytics et mettre en cache
    
    Exécuté : Toutes les 10 minutes
    Avantage : endpoints /stats répondent instantanément (depuis cache)
    """
    
    logger.info("📊 Calcul métriques analytics...")
    
    async def _compute():
        async with AsyncSessionLocal() as db:
            # Calculer stats globales
            global_stats = await analytics_service.get_global_stats(db)
            
            # Mettre en cache
            await cache_service.set(
                "analytics:global_stats",
                json.dumps(global_stats, default=str),
                ttl=600  # 10 minutes
            )
            
            # Timeline semaine
            timeline = await analytics_service.get_timeline_stats(db, "week")
            await cache_service.set(
                "analytics:timeline:week",
                json.dumps(timeline, default=str),
                ttl=600
            )
            
            # Tendances
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
        import asyncio
        metrics = asyncio.run(_compute())
        
        logger.info("✅ Métriques calculées et mises en cache")
        
        return {
            "success": True,
            "total_frauds": metrics["global_stats"]["total_frauds"],
            "timestamp": str(datetime.utcnow())
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul métriques: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name="app.workers.tasks.analytics_tasks.generate_report")
def generate_report(period: str = "week"):
    """
    Générer rapport analytics (PDF ou JSON)
    
    Peut être appelé manuellement : celery_app.send_task(...)
    """
    
    logger.info(f"📄 Génération rapport {period}...")
    
    async def _generate():
        async with AsyncSessionLocal() as db:
            timeline = await analytics_service.get_timeline_stats(db, period)
            global_stats = await analytics_service.get_global_stats(db)
            
            report = {
                "period": period,
                "generated_at": datetime.utcnow().isoformat(),
                "stats": global_stats,
                "timeline": timeline
            }
            
            # Sauvegarder rapport
            filename = f"report_{period}_{datetime.utcnow().date()}.json"
            # with open(f"/tmp/{filename}", "w") as f:
            #     json.dump(report, f, indent=2, default=str)
            
            return report
    
    try:
        import asyncio
        report = asyncio.run(_generate())
        
        logger.info("✅ Rapport généré")
        
        return {
            "success": True,
            "report": report,
            "timestamp": str(datetime.utcnow())
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur génération rapport: {e}")
        return {"success": False, "error": str(e)}