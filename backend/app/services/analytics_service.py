from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from app.models.fraud import FraudulentNumber, FraudulentDomain, FraudType
from app.models.user import User
from app.models.report import UserReport, DetectionLog, VerificationStatus
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import json

class AnalyticsService:
    """Service de calcul des statistiques"""

    @staticmethod
    async def get_global_stats(db: AsyncSession) -> dict:
        """Statistiques globales de la plateforme"""

        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        # Total fraudes
        total_frauds_query = await db.execute(
            select(func.count(FraudulentNumber.phone_number))
        )
        total_frauds = total_frauds_query.scalar() or 0

        # Fraudes par période (via detection_logs)
        frauds_today_query = await db.execute(
            select(func.count(DetectionLog.log_id)).where(
                and_(
                    DetectionLog.is_fraud == True,
                    DetectionLog.timestamp >= today_start
                )
            )
        )
        frauds_today = frauds_today_query.scalar() or 0

        frauds_week_query = await db.execute(
            select(func.count(DetectionLog.log_id)).where(
                and_(
                    DetectionLog.is_fraud == True,
                    DetectionLog.timestamp >= week_start
                )
            )
        )
        frauds_week = frauds_week_query.scalar() or 0

        frauds_month_query = await db.execute(
            select(func.count(DetectionLog.log_id)).where(
                and_(
                    DetectionLog.is_fraud == True,
                    DetectionLog.timestamp >= month_start
                )
            )
        )
        frauds_month = frauds_month_query.scalar() or 0

        # Fraudes par type
        frauds_by_type_query = await db.execute(
            select(
                FraudulentNumber.fraud_type,
                func.count(FraudulentNumber.phone_number)
            ).group_by(FraudulentNumber.fraud_type)
        )
        frauds_by_type = {
            row[0].value: row[1]
            for row in frauds_by_type_query.all()
        }

        # Utilisateurs - ✅ CORRIGÉ : User.user_id
        total_users_query = await db.execute(
            select(func.count(User.user_id))
        )
        total_users = total_users_query.scalar() or 0

        active_today_query = await db.execute(
            select(func.count(User.user_id)).where(
                User.last_active >= today_start
            )
        )
        active_today = active_today_query.scalar() or 0

        active_week_query = await db.execute(
            select(func.count(User.user_id)).where(
                User.last_active >= week_start
            )
        )
        active_week = active_week_query.scalar() or 0

        # Signalements - ✅ CORRIGÉ : UserReport.report_id
        total_reports_query = await db.execute(
            select(func.count(UserReport.report_id))
        )
        total_reports = total_reports_query.scalar() or 0

        reports_today_query = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.timestamp >= today_start
            )
        )
        reports_today = reports_today_query.scalar() or 0

        verified_reports_query = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.verification_status == VerificationStatus.VERIFIED
            )
        )
        verified_reports = verified_reports_query.scalar() or 0

        # Top fraudeurs (numéros)
        top_numbers_query = await db.execute(
            select(
                FraudulentNumber.phone_number,
                FraudulentNumber.fraud_type,
                FraudulentNumber.report_count,
                FraudulentNumber.confidence_score
            ).order_by(desc(FraudulentNumber.report_count)).limit(10)
        )
        top_fraud_numbers = [
            {
                "phone": row[0],
                "type": row[1].value,
                "reports": row[2] or 0,
                "confidence": float(row[3]) if row[3] else 0.0
            }
            for row in top_numbers_query.all()
        ]

        # Top domaines
        top_domains_query = await db.execute(
            select(
                FraudulentDomain.domain,
                FraudulentDomain.phishing_type,
                FraudulentDomain.blocked_count,
                FraudulentDomain.reputation_score
            ).order_by(desc(FraudulentDomain.blocked_count)).limit(10)
        )
        top_fraud_domains = [
            {
                "domain": row[0],
                "type": row[1] or "unknown",
                "blocks": row[2] or 0,
                "reputation": float(row[3]) if row[3] else 0.0
            }
            for row in top_domains_query.all()
        ]

        # Performance
        avg_time_query = await db.execute(
            select(func.avg(DetectionLog.response_time_ms)).where(
                DetectionLog.timestamp >= week_start
            )
        )
        avg_detection_time = float(avg_time_query.scalar() or 0)

        total_detections_query = await db.execute(
            select(func.count(DetectionLog.log_id))
        )
        total_detections = total_detections_query.scalar() or 0

        return {
            "total_frauds": total_frauds,
            "frauds_blocked_today": frauds_today,
            "frauds_blocked_week": frauds_week,
            "frauds_blocked_month": frauds_month,
            "frauds_by_type": frauds_by_type,
            "total_users": total_users,
            "active_users_today": active_today,
            "active_users_week": active_week,
            "total_reports": total_reports,
            "reports_today": reports_today,
            "verified_reports": verified_reports,
            "pending_reports": total_reports - verified_reports,
            "top_fraud_numbers": top_fraud_numbers,
            "top_fraud_domains": top_fraud_domains,
            "avg_detection_time_ms": round(avg_detection_time, 2),
            "total_detections": total_detections,
            "ml_accuracy": None  # Calculé par worker si modèles actifs
        }

    @staticmethod
    async def get_timeline_stats(
        db: AsyncSession,
        period: str = "week"
    ) -> dict:
        """Statistiques sur une période"""

        now = datetime.utcnow()

        if period == "day":
            days = 1
        elif period == "week":
            days = 7
        elif period == "month":
            days = 30
        elif period == "year":
            days = 365
        else:
            days = 7

        start_date = now - timedelta(days=days)

        # Détections par jour
        detections_query = await db.execute(
            select(
                func.date(DetectionLog.timestamp).label('date'),
                func.count(DetectionLog.log_id).label('count')
            ).where(
                DetectionLog.timestamp >= start_date
            ).group_by(func.date(DetectionLog.timestamp))
            .order_by('date')
        )

        detections_by_day = [
            {
                "date": row[0].isoformat(),
                "count": row[1]
            }
            for row in detections_query.all()
        ]

        # Signalements par jour - ✅ CORRIGÉ : UserReport.report_id
        reports_query = await db.execute(
            select(
                func.date(UserReport.timestamp).label('date'),
                func.count(UserReport.report_id).label('count')
            ).where(
                UserReport.timestamp >= start_date
            ).group_by(func.date(UserReport.timestamp))
            .order_by('date')
        )

        reports_by_day = [
            {
                "date": row[0].isoformat(),
                "count": row[1]
            }
            for row in reports_query.all()
        ]

        # Nouveaux users par jour - ✅ CORRIGÉ : User.user_id
        users_query = await db.execute(
            select(
                func.date(User.created_at).label('date'),
                func.count(User.user_id).label('count')
            ).where(
                User.created_at >= start_date
            ).group_by(func.date(User.created_at))
            .order_by('date')
        )

        new_users_by_day = [
            {
                "date": row[0].isoformat(),
                "count": row[1]
            }
            for row in users_query.all()
        ]

        return {
            "period": period,
            "start_date": start_date.date().isoformat(),
            "end_date": now.date().isoformat(),
            "detections_by_day": detections_by_day,
            "reports_by_day": reports_by_day,
            "new_users_by_day": new_users_by_day,
            "total_detections": sum(d["count"] for d in detections_by_day),
            "total_reports": sum(r["count"] for r in reports_by_day),
            "total_new_users": sum(u["count"] for u in new_users_by_day)
        }

    @staticmethod
    async def get_fraud_trends(db: AsyncSession) -> dict:
        """Tendances fraudes (semaine actuelle vs précédente)"""

        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        # Types en hausse - ✅ AJOUTÉ : Gestion du cas où fraud_category n'existe pas
        try:
            current_week = await db.execute(
                select(
                    DetectionLog.detection_type,  # Utiliser detection_type au lieu de fraud_category
                    func.count(DetectionLog.log_id)
                ).where(
                    and_(
                        DetectionLog.timestamp >= week_start,
                        DetectionLog.is_fraud == True
                    )
                ).group_by(DetectionLog.detection_type)
            )

            prev_week = await db.execute(
                select(
                    DetectionLog.detection_type,
                    func.count(DetectionLog.log_id)
                ).where(
                    and_(
                        DetectionLog.timestamp >= prev_week_start,
                        DetectionLog.timestamp < week_start,
                        DetectionLog.is_fraud == True
                    )
                ).group_by(DetectionLog.detection_type)
            )

            current_counts = {row[0]: row[1] for row in current_week.all() if row[0]}
            prev_counts = {row[0]: row[1] for row in prev_week.all() if row[0]}

            trending = []
            for fraud_type, current_count in current_counts.items():
                prev_count = prev_counts.get(fraud_type, 0)
                if prev_count > 0:
                    growth = ((current_count - prev_count) / prev_count) * 100
                else:
                    growth = 100 if current_count > 0 else 0

                trending.append({
                    "type": fraud_type,
                    "count_week": current_count,
                    "count_prev_week": prev_count,
                    "growth_percent": round(growth, 1)
                })

            trending.sort(key=lambda x: x["growth_percent"], reverse=True)
        except Exception as e:
            print(f"Erreur trends: {e}")
            trending = []

        return {
            "trending_fraud_types": trending[:5],
            "trending_keywords": [],  # À implémenter avec NLP
            "new_fraud_patterns": []  # À implémenter avec ML
        }

    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        period: str = "month",
        limit: int = 10
    ) -> dict:
        """Classement contributeurs"""

        now = datetime.utcnow()

        if period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2000, 1, 1)

        # Top contributeurs - ✅ CORRIGÉ : UserReport.report_id
        query = await db.execute(
            select(
                UserReport.user_id,
                func.count(UserReport.report_id).label('total_reports'),
                func.sum(
                    func.cast(
                        UserReport.verification_status == VerificationStatus.VERIFIED,
                        func.Integer
                    )
                ).label('verified_reports')
            ).where(
                and_(
                    UserReport.timestamp >= start_date,
                    UserReport.user_id.isnot(None)
                )
            ).group_by(UserReport.user_id)
            .order_by(desc('verified_reports'))
            .limit(limit)
        )

        top_contributors = []
        for rank, row in enumerate(query.all(), 1):
            user_id = str(row[0]) if row[0] else "anonymous"
            total = row[1]
            verified = row[2] or 0
            score = verified * 10  # 10 points par report vérifié

            top_contributors.append({
                "rank": rank,
                "user_id": user_id[:8] + "..." if len(user_id) > 8 else user_id,
                "total_reports": total,
                "verified_reports": verified,
                "score": score
            })

        return {
            "period": period,
            "top_contributors": top_contributors
        }


# Instance globale
analytics_service = AnalyticsService()