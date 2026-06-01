from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.services.analytics_service import analytics_service
from app.models.user import User
from app.models.fraud import FraudulentDomain
from app.api.deps.auth_deps import get_current_user
from app.api.deps.role_deps import require_organisation, require_admin
from app.services.cache import cache_service
from datetime import datetime, timezone

router = APIRouter()


@router.get("/stats/public")
async def get_public_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Statistiques communautaires — accessibles à tous les utilisateurs connectés.

    Retourne les chiffres globaux de la plateforme (détections totales, numéros
    frauduleux connus, utilisateurs actifs) sans données sensibles.

    **Accès:** USER / ORGANISATION / ADMIN
    """
    cache_key = "analytics:public_stats"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    full = await analytics_service.get_global_stats(db)

    # Sous-ensemble sans données sensibles (pas de top_fraud_numbers ni top_fraud_domains)
    public = {
        "total_detections": full["total_detections"],
        "fraudulent_numbers": full["total_frauds"],
        "fraudulent_domains": 0,  # enrichi ci-dessous
        "total_reports": full["total_reports"],
        "active_users": full["active_users_week"],
        "detection_rate": round(
            full["total_detections"] / max(full["total_detections"] + 1, 1), 4
        ),
        "avg_response_time_ms": full["avg_detection_time_ms"],
        "frauds_blocked_today": full["frauds_blocked_today"],
        "frauds_blocked_week": full["frauds_blocked_week"],
    }

    # Nombre de domaines frauduleux
    domain_count_q = await db.execute(select(func.count(FraudulentDomain.domain)))
    public["fraudulent_domains"] = domain_count_q.scalar() or 0

    await cache_service.set(cache_key, public, expire=300)  # 5 min
    return public


@router.get("/stats")
async def get_global_stats(
    current_user: User = Depends(require_organisation),
    db: AsyncSession = Depends(get_db)
):
    """Statistiques globales complètes - ORGANISATION/ADMIN"""
    stats = await analytics_service.get_global_stats(db)
    return stats


@router.get("/timeline")
async def get_timeline_stats(
    period: str = Query("week", regex="^(day|week|month|year)$"),
    current_user: User = Depends(require_organisation),
    db: AsyncSession = Depends(get_db)
):
    """Statistiques temporelles - ORGANISATION/ADMIN"""
    stats = await analytics_service.get_timeline_stats(db, period)
    return stats


@router.get("/trends")
async def get_fraud_trends(
    current_user: User = Depends(require_organisation),
    db: AsyncSession = Depends(get_db)
):
    """Tendances fraudes - ORGANISATION/ADMIN"""
    trends = await analytics_service.get_fraud_trends(db)
    return trends


@router.get("/leaderboard")
async def get_leaderboard(
    period: str = Query("month", regex="^(week|month|all_time)$"),
    limit: int = Query(10, ge=5, le=100),
    current_user: User = Depends(require_organisation),
    db: AsyncSession = Depends(get_db)
):
    """Classement contributeurs - ORGANISATION/ADMIN"""
    leaderboard = await analytics_service.get_leaderboard(db, period, limit)
    return leaderboard


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Dashboard admin complet - ADMIN uniquement"""

    # Récupérer toutes les stats
    overview = await analytics_service.get_global_stats(db)
    timeline = await analytics_service.get_timeline_stats(db, "week")
    trends = await analytics_service.get_fraud_trends(db)
    leaderboard = await analytics_service.get_leaderboard(db, "month", 10)

    # Qualité (mock pour MVP)
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
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "cache_ttl": 300
    }

    return dashboard


@router.post("/clear-cache")
async def clear_analytics_cache(
    current_user: User = Depends(require_admin)
):
    """Vider le cache - ADMIN uniquement"""
    return {
        "message": "Cache désactivé (MVP)",
        "cleared_by": str(current_user.user_id),
        "cleared_by_role": current_user.role
    }


@router.get("/health")
async def analytics_health(
    db: AsyncSession = Depends(get_db)
):
    """Health check"""
    import time
    start = time.time()

    # Test DB
    try:
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        db_ok = result.scalar() == 1
    except Exception as e:
        print(f"DB Health error: {e}")
        db_ok = False

    response_time = int((time.time() - start) * 1000)

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "cache": "disabled",
        "response_time_ms": response_time
    }