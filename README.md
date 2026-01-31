# DYLETH - Protection Anti-Fraude 3-en-1

Application de protection contre fraudes (Appels + SMS + Emails) avec IA/ML.

## Architecture

- Backend: FastAPI + PostgreSQL + Redis + Qdrant
- ML: Scikit-learn + XGBoost + Sentence Transformers
- Mobile: Kotlin (Android) + Swift (iOS)
- Extension: JavaScript

## Installation

### Prérequis

- Docker & Docker Compose
- Python 3.11+

### Démarrage rapide

```bash
cd backend
cp .env.example .env
docker-compose up -d
```

L'API sera disponible sur http://localhost:8000

### Documentation API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints principaux

### Vérification téléphone
```bash
POST /api/v1/phone/check-phone
{
  "phone": "+33612345678",
  "country": "FR",
  "user_id": "optional-uuid"
}
```

### Analyse SMS
```bash
POST /api/v1/sms/analyze-sms
{
  "content": "URGENT! Payez 2€ maintenant: bit.ly/abc",
  "sender": "+33612345678",
  "user_id": "optional-uuid"
}
```

### Analyse Email
```bash
POST /api/v1/email/analyze-email
{
  "sender": "noreply@bank.com",
  "subject": "Action requise",
  "body": "Confirmez vos identifiants...",
  "user_id": "optional-uuid"
}
```

## Base de données

Migration initiale:
```bash
docker-compose exec api alembic upgrade head
```

## Structure projet

```
dyleth-project/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── ml/
│   │   └── rag/
│   ├── alembic/
│   ├── tests/
│   └── docker-compose.yml
├── mobile/
│   ├── android/
│   └── ios/
└── extension/
```

## Développement

Installation locale:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
uvicorn app.main:app --reload
```

## Tests

```bash
pytest tests/
```

## Production

Pour production, modifier .env:
- Changer SECRET_KEY
- Configurer CORS_ORIGINS
- Activer HTTPS

## License

Propriétaire - DYLETH 2025
