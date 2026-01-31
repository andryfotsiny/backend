# Architecture Technique DYLETH

## Vue d'ensemble

DYLETH est une application anti-fraude 3-en-1 avec une architecture microservices moderne.

## Stack Technique

### Backend
- **Framework**: FastAPI 0.109
- **ORM**: SQLAlchemy 2.0 (async)
- **Base de données**: PostgreSQL 15
- **Cache**: Redis 7
- **Vector DB**: Qdrant 1.7

### Machine Learning
- **ML Classique**: Scikit-learn 1.4 + XGBoost 2.0
- **NLP**: spaCy 3.7
- **Embeddings**: Sentence Transformers
- **Stratégie**: Système hybride 3 niveaux

### Infrastructure
- **Containers**: Docker + Docker Compose
- **Orchestration future**: Kubernetes
- **Cloud recommandé**: GCP

## Système de Détection 3 Niveaux

### Niveau 1: Cache/Blacklist (10ms)
- Recherche dans Redis cache
- Lookup PostgreSQL blacklist
- Couvre 80% des cas

### Niveau 2: ML Classique (50ms)
- Random Forest / XGBoost
- Features: TF-IDF, patterns, métadonnées
- Couvre 95% des cas

### Niveau 3: RAG Avancé (100ms)
- Embeddings avec Sentence Transformers
- Recherche de similarité dans Qdrant
- Contexte enrichi
- Couvre 100% des cas avec explicabilité

## Base de Données

### Tables Principales

**users**
- Gestion utilisateurs
- Hash email/téléphone pour privacy
- Settings JSONB flexible
- Device tokens pour push notifications

**fraudulent_numbers**
- 50M+ numéros frauduleux (objectif)
- Score de confiance
- Compteur signalements
- Métadonnées flexibles

**fraudulent_sms_patterns**
- Patterns regex
- Keywords frauduleux
- Catégorisation
- Taux faux positifs

**fraudulent_domains**
- Domaines phishing
- Vérification SPF/DKIM/DMARC
- Score réputation

**user_reports**
- Signalements communautaires
- Système de vérification
- Content hash pour privacy

**detection_logs**
- Analytics et métriques
- Performance monitoring
- A/B testing modèles

**ml_model_versions**
- Versioning modèles
- Métriques performance
- Déploiement actif/inactif

## Services

### CacheService
- Gestion Redis
- Rate limiting
- TTL configurables

### MLService
- Chargement modèles
- Prédictions phone/sms/email
- Fallback rule-based

### RAGService
- Connexion Qdrant
- Recherche similarité
- Ajout vecteurs

### DetectionService
- Orchestration 3 niveaux
- Logging automatique
- Cache intelligent

### EmbeddingService
- Sentence Transformers
- Génération embeddings
- Batch processing

## API Endpoints

### GET /health
Health check système

### POST /api/v1/phone/check-phone
Vérification numéro téléphone

**Request:**
```json
{
  "phone": "+33612345678",
  "country": "FR",
  "user_id": "optional"
}
```

**Response:**
```json
{
  "is_fraud": true,
  "confidence": 0.95,
  "category": "scam",
  "reason": "Signalé 127 fois",
  "action": "block",
  "similar_cases": 127,
  "response_time_ms": 45
}
```

### POST /api/v1/sms/analyze-sms
Analyse SMS

**Request:**
```json
{
  "content": "URGENT! Payez maintenant",
  "sender": "+33612345678",
  "user_id": "optional"
}
```

**Response:**
```json
{
  "is_fraud": true,
  "confidence": 0.87,
  "category": "phishing",
  "risk_factors": [
    "Urgence factice",
    "Demande de paiement"
  ],
  "action": "block_link",
  "similar_frauds": 45,
  "response_time_ms": 67
}
```

### POST /api/v1/email/analyze-email
Analyse email

**Request:**
```json
{
  "sender": "noreply@fake-bank.com",
  "subject": "Action requise",
  "body": "Confirmez vos identifiants...",
  "user_id": "optional"
}
```

**Response:**
```json
{
  "is_fraud": true,
  "confidence": 0.92,
  "phishing_type": "banking",
  "risk_factors": ["Domaine suspect"],
  "sender_verified": false,
  "spf_valid": false,
  "dkim_valid": false,
  "action": "warn",
  "response_time_ms": 89
}
```

## Flux de Données

### Exemple: Appel entrant (Android)

```
1. CallScreeningService intercepte
2. App extrait phone_number
3. POST /api/v1/phone/check-phone
4. Backend:
   a. Rate limit check (Redis)
   b. Cache lookup (Redis) - 10ms
   c. Si miss: DB lookup (PostgreSQL) - 50ms
   d. Si miss: ML prediction - 100ms
5. Réponse JSON
6. App Android: bloquer ou permettre
7. Log asynchrone dans PostgreSQL
```

### Exemple: SMS reçu

```
1. BroadcastReceiver intercepte SMS
2. App extrait content + sender
3. POST /api/v1/sms/analyze-sms
4. Backend:
   a. ML rule-based (urgence, argent, liens)
   b. ML classique (TF-IDF + Random Forest)
   c. Si incertain: RAG similarity search
5. Réponse avec risk_factors
6. App marque SMS + bloque liens
7. Log dans PostgreSQL
```

## Sécurité

### Privacy
- Hash SHA-256 pour email/téléphone
- Content hash pour reports
- Pas de stockage données sensibles
- Chiffrement AES-256 (futur)

### Rate Limiting
- Redis-based
- 100 requêtes/minute par défaut
- Configurable par utilisateur

### CORS
- Configurable via .env
- Production: whitelist strict

### JWT (futur)
- Authentification utilisateurs
- Refresh tokens
- Expiration configurable

## Monitoring (futur)

### Métriques
- Prometheus exporters
- Grafana dashboards
- Alertes Sentry

### KPIs
- Response time p50/p95/p99
- Accuracy ML par type
- False positive rate
- Cache hit rate
- Throughput (req/s)

## Scalabilité

### Phase 1 (MVP - 1M req/jour)
- Docker Compose
- 1 instance API
- PostgreSQL standalone
- Redis standalone

### Phase 2 (10M req/jour)
- Kubernetes
- API auto-scaling (3-10 pods)
- PostgreSQL avec replicas
- Redis cluster

### Phase 3 (100M+ req/jour)
- Multi-region
- CDN
- Load balancer géographique
- Sharding PostgreSQL
- ML models distribués

## Développement

### Local Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Tests
```bash
pytest tests/ -v --cov=app
```

### Migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Docker
```bash
docker-compose up --build
docker-compose logs -f api
docker-compose down
```

## Roadmap Technique

### Q1 2025
- MVP Backend API
- Base 100K numéros frauduleux
- ML rule-based
- App Android MVP

### Q2 2025
- ML modèles entraînés
- RAG implémenté
- Extension Chrome
- App iOS MVP

### Q3 2025
- Crowdsourcing actif
- 1M+ numéros
- Kubernetes production
- API B2B

### Q4 2025
- Multi-region
- 10M+ numéros
- ML avancé (Deep Learning)
- Analytics avancés
