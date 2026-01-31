# DYLETH - Instructions d'Installation

## Prérequis

- Docker 20.10+
- Docker Compose 2.0+
- Git
- 4GB RAM minimum
- 10GB espace disque

## Installation Rapide

### 1. Extraire le projet
```bash
cd dyleth-project
```

### 2. Lancer l'installation automatique
```bash
cd backend
cp .env.example .env
docker-compose up -d
```

### 3. Attendre le démarrage (30 secondes)
```bash
docker-compose logs -f api
```

Attendre le message: "Application startup complete"

### 4. Exécuter les migrations
```bash
docker-compose exec api alembic upgrade head
```

### 5. Insérer les données de test
```bash
docker-compose exec api python /app/scripts/seed_db.py
```

### 6. Tester l'API
```bash
curl http://localhost:8000/health
```

Réponse attendue:
```json
{"status": "healthy", "version": "1.0.0"}
```

## Accès aux Services

- **API**: http://localhost:8000
- **Documentation Swagger**: http://localhost:8000/docs
- **Documentation ReDoc**: http://localhost:8000/redoc
- **PostgreSQL**: localhost:5432 (user: dyleth, pass: dyleth123, db: dyleth)
- **Redis**: localhost:6379
- **Qdrant**: http://localhost:6333

## Structure du Projet

```
dyleth-project/
├── README.md                    # Documentation principale
├── QUICKSTART.md               # Guide démarrage rapide
│
├── backend/                    # API Backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # Endpoints REST
│   │   ├── core/              # Configuration
│   │   ├── db/                # Base de données
│   │   ├── models/            # Models SQLAlchemy
│   │   ├── schemas/           # Schemas Pydantic
│   │   ├── services/          # Logique métier
│   │   ├── ml/                # Machine Learning
│   │   └── rag/               # RAG + Embeddings
│   ├── alembic/               # Migrations DB
│   ├── scripts/               # Scripts utilitaires
│   ├── requirements.txt       # Dépendances Python
│   ├── Dockerfile             # Image Docker
│   └── docker-compose.yml     # Stack complète
│
├── mobile/                     # Applications mobiles (futur)
│   ├── android/               # App Android (Kotlin)
│   └── ios/                   # App iOS (Swift)
│
├── extension/                  # Extension navigateur (futur)
│
├── docs/                      # Documentation
│   └── ARCHITECTURE.md        # Architecture détaillée
│
└── scripts/                   # Scripts d'installation
    ├── install.sh             # Installation auto
    └── test_api.sh            # Tests API
```

## Fichiers Importants

### Backend

**app/main.py**
- Point d'entrée FastAPI
- Configuration CORS
- Lifecycle events

**app/core/config.py**
- Configuration centralisée
- Variables d'environnement
- Settings Pydantic

**app/services/detection.py**
- Service principal de détection
- Orchestration 3 niveaux
- Cache + ML + RAG

**app/models/**
- user.py: Utilisateurs
- fraud.py: Numéros/domaines frauduleux
- report.py: Signalements + logs

**app/api/v1/endpoints/**
- phone.py: Vérification téléphone
- sms.py: Analyse SMS
- email.py: Analyse email

### Configuration

**.env**
```env
DATABASE_URL=postgresql+asyncpg://dyleth:dyleth123@postgres:5432/dyleth
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
SECRET_KEY=change-in-production
FRAUD_CONFIDENCE_THRESHOLD=0.7
```

### Docker

**docker-compose.yml**
- PostgreSQL 15
- Redis 7
- Qdrant latest
- API FastAPI

## Commandes Utiles

### Docker
```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Logs
docker-compose logs -f api

# Redémarrer un service
docker-compose restart api

# Rebuild
docker-compose up -d --build
```

### Base de données
```bash
# Accéder à PostgreSQL
docker-compose exec postgres psql -U dyleth -d dyleth

# Migrations
docker-compose exec api alembic upgrade head
docker-compose exec api alembic revision --autogenerate -m "description"

# Seed data
docker-compose exec api python /app/scripts/seed_db.py
```

### Tests
```bash
# Health check
curl http://localhost:8000/health

# Test téléphone
curl -X POST http://localhost:8000/api/v1/phone/check-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "+33756123456", "country": "FR"}'

# Test SMS
curl -X POST http://localhost:8000/api/v1/sms/analyze-sms \
  -H "Content-Type: application/json" \
  -d '{"content": "URGENT! Payez maintenant", "sender": "+33612345678"}'

# Test email
curl -X POST http://localhost:8000/api/v1/email/analyze-email \
  -H "Content-Type: application/json" \
  -d '{"sender": "test@fake.com", "subject": "Urgent", "body": "Cliquez ici"}'
```

## Développement Local (sans Docker)

### 1. Installation Python
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
```

### 2. Démarrer services externes
```bash
# PostgreSQL (installer localement ou Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dyleth123 postgres:15

# Redis
docker run -d -p 6379:6379 redis:7

# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant
```

### 3. Configuration
```bash
cp .env.example .env
# Modifier DATABASE_URL, REDIS_URL, QDRANT_URL pour localhost
```

### 4. Migrations
```bash
alembic upgrade head
```

### 5. Lancer l'API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Erreur: "Cannot connect to database"
```bash
# Vérifier PostgreSQL
docker-compose logs postgres

# Redémarrer
docker-compose restart postgres
```

### Erreur: "Redis connection refused"
```bash
# Vérifier Redis
docker-compose logs redis

# Tester
docker-compose exec redis redis-cli ping
```

### Erreur: "Port already in use"
```bash
# Trouver le processus
lsof -i :8000

# Tuer le processus
kill -9 <PID>
```

### Logs détaillés
```bash
# API
docker-compose logs -f api

# Tous les services
docker-compose logs -f

# PostgreSQL
docker-compose logs postgres
```

## Performance

### Temps de réponse attendus
- Cache hit: 10-20ms
- Database hit: 40-60ms
- ML prediction: 80-120ms

### Capacité
- MVP: 1M requêtes/jour
- Target: 100M requêtes/jour

## Sécurité

### Production
1. Changer SECRET_KEY dans .env
2. Configurer CORS_ORIGINS (whitelist)
3. Activer HTTPS
4. Limiter accès PostgreSQL
5. Activer authentification Redis
6. Configurer firewall

## Support

- Documentation: /docs/ARCHITECTURE.md
- Swagger: http://localhost:8000/docs
- Tests: scripts/test_api.sh

## Next Steps

1. Tester l'API avec Swagger
2. Développer app mobile Android
3. Créer extension Chrome
4. Entraîner modèles ML
5. Implémenter crowdsourcing
6. Déployer en production
