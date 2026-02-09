from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.analytics_service import analytics_service
from app.services.cache import cache_service
from app.schemas.analytics import (
    GlobalStats, TimelineStats, FraudTrends,
    Leaderboard, DetectionQuality, AdminDashboard
)
from typing import Optional
from datetime import datetime
import json

router = APIRouter()

CACHE_TTL_SHORT = 60      # 1 minute
CACHE_TTL_MEDIUM = 300    # 5 minutes
CACHE_TTL_LONG = 3600     # 1 heure


@router.get("/stats", response_model=GlobalStats)
async def get_global_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Statistiques globales de la plateforme

    - Total fraudes dans la base
    - Fraudes bloquées (aujourd'hui, semaine, mois)
    - Répartition par type
    - Utilisateurs actifs
    - Signalements communautaires
    - Top fraudeurs
    - Performance système

    **Cache:** 5 minutes
    """

    # Vérifier cache
    cache_key = "analytics:global_stats"
    cached = await cache_service.get(cache_key)

    if cached:
        return json.loads(cached)

    # Calculer stats
    stats = await analytics_service.get_global_stats(db)

    # Mettre en cache
    await cache_service.set(
        cache_key,
        json.dumps(stats, default=str),
        ttl=CACHE_TTL_MEDIUM
    )

    return stats


@router.get("/timeline", response_model=TimelineStats)
async def get_timeline_stats(
    period: str = Query("week", regex="^(day|week|month|year)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Statistiques temporelles

    - **period**: day, week, month, year

    Retourne:
    - Détections par jour
    - Signalements par jour
    - Nouveaux utilisateurs par jour

    **Cache:** 1 minute
    """

    cache_key = f"analytics:timeline:{period}"
    cached = await cache_service.get(cache_key)

    if cached:
        return json.loads(cached)

    stats = await analytics_service.get_timeline_stats(db, period)

    await cache_service.set(
        cache_key,
        json.dumps(stats, default=str),
        ttl=CACHE_TTL_SHORT
    )

    return stats


@router.get("/trends", response_model=FraudTrends)
async def get_fraud_trends(
    db: AsyncSession = Depends(get_db)
):
    """
    Tendances fraudes

    - Types de fraude en hausse
    - Mots-clés tendances
    - Nouveaux patterns détectés

    Compare semaine actuelle vs précédente

    **Cache:** 5 minutes
    """

    cache_key = "analytics:trends"
    cached = await cache_service.get(cache_key)

    if cached:
        return json.loads(cached)

    trends = await analytics_service.get_fraud_trends(db)

    await cache_service.set(
        cache_key,
        json.dumps(trends, default=str),
        ttl=CACHE_TTL_MEDIUM
    )

    return trends


@router.get("/leaderboard", response_model=Leaderboard)
async def get_leaderboard(
    period: str = Query("month", regex="^(week|month|all_time)$"),
    limit: int = Query(10, ge=5, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Classement des meilleurs contributeurs

    - **period**: week, month, all_time
    - **limit**: Nombre de résultats (5-100)

    Score = signalements vérifiés × 10

    **Cache:** 5 minutes
    """

    cache_key = f"analytics:leaderboard:{period}:{limit}"
    cached = await cache_service.get(cache_key)

    if cached:
        return json.loads(cached)

    leaderboard = await analytics_service.get_leaderboard(db, period, limit)

    await cache_service.set(
        cache_key,
        json.dumps(leaderboard, default=str),
        ttl=CACHE_TTL_MEDIUM
    )

    return leaderboard


@router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Dashboard admin complet

    Agrège toutes les statistiques :
    - Overview global
    - Timeline semaine
    - Tendances
    - Qualité détection
    - Leaderboard

    **Cache:** 5 minutes
    **Usage:** Affichage dashboard admin
    """

    cache_key = "analytics:dashboard:admin"
    cached = await cache_service.get(cache_key)

    if cached:
        return json.loads(cached)

    # Récupérer toutes les stats en parallèle
    overview = await analytics_service.get_global_stats(db)
    timeline = await analytics_service.get_timeline_stats(db, "week")
    trends = await analytics_service.get_fraud_trends(db)
    leaderboard = await analytics_service.get_leaderboard(db, "month", 10)

    # Qualité (mock pour MVP - sera calculé par worker)
    quality = {
        "total_detections": overview["total_detections"],
        "true_positives": int(overview["total_detections"] * 0.95),
        "false_positives": int(overview["total_detections"] * 0.02),
        "false_negatives": int(overview["total_detections"] * 0.02),
        "true_negatives": int(overview["total_detections"] * 0.01),
        "precision": 0.979,
        "recall": 0.979,
        "f1_score": 0.979,
        "accuracy": 0.960,
        "by_fraud_type": {}
    }

    dashboard = {
        "overview": overview,
        "timeline": timeline,
        "trends": trends,
        "quality": quality,
        "leaderboard": leaderboard,
        "generated_at": datetime.utcnow().isoformat(),
        "cache_ttl": CACHE_TTL_MEDIUM
    }

    await cache_service.set(
        cache_key,
        json.dumps(dashboard, default=str),
        ttl=CACHE_TTL_MEDIUM
    )

    return dashboard


@router.post("/clear-cache")
async def clear_analytics_cache():
    """
    Vider le cache analytics

    À utiliser après mise à jour massive de données
    ou pour forcer recalcul

    **Admin only** (à protéger avec JWT admin)
    """

    # Supprimer tous les caches analytics
    patterns = [
        "analytics:*"
    ]

    cleared = 0
    for pattern in patterns:
        # Note: Redis KEYS est OK pour dev, utiliser SCAN en prod
        keys = await cache_service.client.keys(pattern)
        for key in keys:
            await cache_service.delete(key.decode())
            cleared += 1

    return {
        "message": f"Cache vidé : {cleared} entrées supprimées",
        "patterns": patterns
    }


@router.get("/health")
async def analytics_health(
    db: AsyncSession = Depends(get_db)
):
    """
    Santé du service analytics

    Vérifie :
    - Connexion DB
    - Cache Redis
    - Temps de réponse
    """

    import time
    start = time.time()

    # Test DB
    try:
        result = await db.execute("SELECT 1")
        db_ok = result.scalar() == 1
    except:
        db_ok = False

    # Test cache
    try:
        await cache_service.set("health:test", "ok", ttl=5)
        cache_ok = await cache_service.get("health:test") == "ok"
    except:
        cache_ok = False

    response_time = int((time.time() - start) * 1000)

    return {
        "status": "healthy" if (db_ok and cache_ok) else "degraded",
        "database": "ok" if db_ok else "error",
        "cache": "ok" if cache_ok else "error",
        "response_time_ms": response_time
    }