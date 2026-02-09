from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime, date

# === GLOBAL STATS ===

class GlobalStats(BaseModel):
    """Statistiques globales de la plateforme"""

    # Fraudes
    total_frauds: int = Field(..., description="Total fraudes dans la DB")
    frauds_blocked_today: int = Field(..., description="Fraudes bloquées aujourd'hui")
    frauds_blocked_week: int = Field(..., description="Fraudes bloquées cette semaine")
    frauds_blocked_month: int = Field(..., description="Fraudes bloquées ce mois")

    # Par type
    frauds_by_type: Dict[str, int] = Field(..., description="Répartition par type")

    # Utilisateurs
    total_users: int = Field(..., description="Total utilisateurs inscrits")
    active_users_today: int = Field(..., description="Utilisateurs actifs aujourd'hui")
    active_users_week: int = Field(..., description="Utilisateurs actifs cette semaine")

    # Signalements
    total_reports: int = Field(..., description="Total signalements communautaires")
    reports_today: int = Field(..., description="Signalements aujourd'hui")
    verified_reports: int = Field(..., description="Signalements vérifiés")
    pending_reports: int = Field(..., description="Signalements en attente")

    # Top fraudeurs
    top_fraud_numbers: List[Dict[str, any]] = Field(..., description="Top 10 numéros frauduleux")
    top_fraud_domains: List[Dict[str, any]] = Field(..., description="Top 10 domaines frauduleux")

    # Performance
    avg_detection_time_ms: float = Field(..., description="Temps détection moyen (ms)")
    total_detections: int = Field(..., description="Total détections effectuées")

    # Métriques ML
    ml_accuracy: Optional[float] = Field(None, description="Précision ML si modèles actifs")

    class Config:
        json_schema_extra = {
            "example": {
                "total_frauds": 127453,
                "frauds_blocked_today": 892,
                "frauds_by_type": {
                    "scam": 45000,
                    "phishing": 38000,
                    "spam": 32000,
                    "robocall": 12453
                },
                "total_users": 5432,
                "total_reports": 23456,
                "top_fraud_numbers": [
                    {"phone": "+33756123456", "reports": 127, "type": "scam"}
                ]
            }
        }


# === TIMELINE STATS ===

class TimelineStats(BaseModel):
    """Statistiques sur une période"""

    period: str = Field(..., description="Période (day, week, month, year)")
    start_date: date
    end_date: date

    detections_by_day: List[Dict[str, any]] = Field(..., description="Détections par jour")
    reports_by_day: List[Dict[str, any]] = Field(..., description="Signalements par jour")
    new_users_by_day: List[Dict[str, any]] = Field(..., description="Nouveaux users par jour")

    total_detections: int
    total_reports: int
    total_new_users: int

    class Config:
        json_schema_extra = {
            "example": {
                "period": "week",
                "start_date": "2026-01-25",
                "end_date": "2026-02-01",
                "detections_by_day": [
                    {"date": "2026-01-25", "count": 145},
                    {"date": "2026-01-26", "count": 178}
                ],
                "total_detections": 1234
            }
        }


# === FRAUD TRENDS ===

class FraudTrends(BaseModel):
    """Tendances fraudes"""

    trending_fraud_types: List[Dict[str, any]] = Field(..., description="Types en hausse")
    trending_keywords: List[Dict[str, any]] = Field(..., description="Mots-clés tendances")
    new_fraud_patterns: List[Dict[str, any]] = Field(..., description="Nouveaux patterns détectés")

    class Config:
        json_schema_extra = {
            "example": {
                "trending_fraud_types": [
                    {
                        "type": "phishing",
                        "count_week": 456,
                        "count_prev_week": 312,
                        "growth_percent": 46.2
                    }
                ],
                "trending_keywords": [
                    {"keyword": "livraison", "count": 234, "growth": 78.5}
                ]
            }
        }


# === LEADERBOARD ===

class Leaderboard(BaseModel):
    """Classement contributeurs"""

    period: str = Field(..., description="all_time, month, week")
    top_contributors: List[Dict[str, any]] = Field(..., description="Top contributeurs")

    class Config:
        json_schema_extra = {
            "example": {
                "period": "month",
                "top_contributors": [
                    {
                        "rank": 1,
                        "user_id": "user_123",
                        "username": "SafetyFirst",
                        "total_reports": 87,
                        "verified_reports": 75,
                        "score": 750
                    }
                ]
            }
        }


# === DETECTION QUALITY ===

class DetectionQuality(BaseModel):
    """Qualité des détections"""

    total_detections: int
    true_positives: int = Field(..., description="Vraies fraudes détectées")
    false_positives: int = Field(..., description="Faux positifs")
    false_negatives: int = Field(..., description="Fraudes manquées")
    true_negatives: int = Field(..., description="Légitimes correctement identifiés")

    precision: float = Field(..., description="Précision (TP / TP+FP)")
    recall: float = Field(..., description="Rappel (TP / TP+FN)")
    f1_score: float = Field(..., description="Score F1")
    accuracy: float = Field(..., description="Exactitude globale")

    by_fraud_type: Dict[str, Dict[str, float]] = Field(..., description="Métriques par type")

    class Config:
        json_schema_extra = {
            "example": {
                "total_detections": 10000,
                "true_positives": 8900,
                "false_positives": 150,
                "precision": 0.983,
                "recall": 0.957,
                "f1_score": 0.970,
                "accuracy": 0.975
            }
        }


# === ADMIN DASHBOARD ===

class AdminDashboard(BaseModel):
    """Dashboard admin complet"""

    overview: GlobalStats
    timeline: TimelineStats
    trends: FraudTrends
    quality: DetectionQuality
    leaderboard: Leaderboard

    generated_at: datetime
    cache_ttl: int = Field(300, description="TTL cache en secondes")