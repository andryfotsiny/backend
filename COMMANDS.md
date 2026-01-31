# DYLETH - Commandes d'Exécution Étape par Étape

## Étape 1: Préparation

```bash
cd dyleth-project/backend
```

## Étape 2: Configuration

```bash
cp .env.example .env
```

Optionnel - Modifier .env si nécessaire:
```bash
nano .env
```

## Étape 3: Démarrer les services Docker

```bash
docker-compose up -d
```

Vérifier que tous les services sont démarrés:
```bash
docker-compose ps
```

Output attendu:
```
NAME                IMAGE                  STATUS
dyleth_api          backend-api           Up
dyleth_postgres     postgres:15-alpine    Up (healthy)
dyleth_redis        redis:7-alpine        Up (healthy)
dyleth_qdrant       qdrant/qdrant         Up (healthy)
```

## Étape 4: Vérifier les logs

```bash
docker-compose logs -f api
```

Attendre le message: "Application startup complete"
Puis Ctrl+C pour sortir

## Étape 5: Exécuter les migrations de base de données

```bash
docker-compose exec api alembic upgrade head
```

Output attendu:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial migration
```

## Étape 6: Insérer les données de test

```bash
docker-compose exec api python /app/scripts/seed_db.py
```

Output attendu:
```
Database seeded successfully!
  - 3 fraudulent numbers
  - 3 SMS patterns
  - 3 fraudulent domains
```

## Étape 7: Tester l'API

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Output attendu:
```json
{"status":"healthy","version":"1.0.0"}
```

### Test 2: Vérifier un numéro frauduleux connu
```bash
curl -X POST http://localhost:8000/api/v1/phone/check-phone \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+33756123456",
    "country": "FR"
  }'
```

Output attendu:
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

### Test 3: Analyser un SMS suspect
```bash
curl -X POST http://localhost:8000/api/v1/sms/analyze-sms \
  -H "Content-Type: application/json" \
  -d '{
    "content": "URGENT! Votre colis attend. Payez 2€ maintenant: http://bit.ly/abc123",
    "sender": "+33612345678"
  }'
```

Output attendu:
```json
{
  "is_fraud": true,
  "confidence": 0.85,
  "category": "phishing",
  "risk_factors": [
    "Urgence factice",
    "Demande de paiement",
    "Lien suspect"
  ],
  "action": "block_link",
  "similar_frauds": 0,
  "response_time_ms": 67
}
```

### Test 4: Analyser un email
```bash
curl -X POST http://localhost:8000/api/v1/email/analyze-email \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "noreply@fake-bank-secure.com",
    "subject": "Action requise sur votre compte",
    "body": "Cher client, nous avons détecté une activité suspecte. Confirmez vos identifiants immédiatement."
  }'
```

Output attendu:
```json
{
  "is_fraud": true,
  "confidence": 0.95,
  "phishing_type": "banking",
  "risk_factors": ["Domaine signalé comme frauduleux"],
  "sender_verified": false,
  "spf_valid": false,
  "dkim_valid": false,
  "action": "block",
  "response_time_ms": 89
}
```

## Étape 8: Accéder à la documentation interactive

Ouvrir dans le navigateur:

```
http://localhost:8000/docs
```

ou

```
http://localhost:8000/redoc
```

## Étape 9: Explorer la base de données

```bash
docker-compose exec postgres psql -U dyleth -d dyleth
```

Commandes SQL utiles:
```sql
-- Lister les tables
\dt

-- Voir les numéros frauduleux
SELECT * FROM fraudulent_numbers;

-- Voir les patterns SMS
SELECT * FROM fraudulent_sms_patterns;

-- Voir les domaines frauduleux
SELECT * FROM fraudulent_domains;

-- Voir les logs de détection
SELECT * FROM detection_logs ORDER BY timestamp DESC LIMIT 10;

-- Quitter
\q
```

## Étape 10: Explorer Redis

```bash
docker-compose exec redis redis-cli
```

Commandes Redis:
```
KEYS *
GET phone:+33756123456
QUIT
```

## Étape 11: Explorer Qdrant

Ouvrir dans le navigateur:
```
http://localhost:6333/dashboard
```

Ou via API:
```bash
curl http://localhost:6333/collections
```

## Commandes de Gestion

### Voir les logs en temps réel
```bash
docker-compose logs -f
```

ou pour un service spécifique:
```bash
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Redémarrer un service
```bash
docker-compose restart api
```

### Arrêter tous les services
```bash
docker-compose down
```

### Redémarrer tous les services
```bash
docker-compose down
docker-compose up -d
```

### Rebuild complet
```bash
docker-compose down
docker-compose up -d --build
```

### Supprimer volumes (attention: perte de données)
```bash
docker-compose down -v
```

## Test Automatique Complet

Utiliser le script de test:
```bash
cd ..
./scripts/test_api.sh
```

## Développement Local (sans Docker)

### 1. Installation
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
```

### 2. Démarrer services externes
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dyleth123 -e POSTGRES_USER=dyleth -e POSTGRES_DB=dyleth postgres:15
docker run -d -p 6379:6379 redis:7
docker run -d -p 6333:6333 qdrant/qdrant
```

### 3. Modifier .env
```bash
nano .env
```

Remplacer les hosts Docker par localhost:
```
DATABASE_URL=postgresql+asyncpg://dyleth:dyleth123@localhost:5432/dyleth
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
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

### Problème: Port déjà utilisé
```bash
# Trouver le processus
lsof -i :8000

# Tuer le processus
kill -9 <PID>
```

### Problème: Base de données ne démarre pas
```bash
# Vérifier les logs
docker-compose logs postgres

# Supprimer et recréer
docker-compose down -v
docker-compose up -d
```

### Problème: API ne se connecte pas à la base
```bash
# Vérifier la connexion
docker-compose exec api python -c "from app.db.session import engine; import asyncio; asyncio.run(engine.connect())"
```

### Problème: Modèles ML non chargés
C'est normal en MVP. Le système utilise le fallback rule-based qui fonctionne bien.

## Prochaines Commandes

### Créer une nouvelle migration
```bash
docker-compose exec api alembic revision --autogenerate -m "description"
docker-compose exec api alembic upgrade head
```

### Ajouter de nouvelles données frauduleuses
Modifier `backend/scripts/seed_db.py` puis:
```bash
docker-compose exec api python /app/scripts/seed_db.py
```

### Exporter la base de données
```bash
docker-compose exec postgres pg_dump -U dyleth dyleth > backup.sql
```

### Importer la base de données
```bash
cat backup.sql | docker-compose exec -T postgres psql -U dyleth dyleth
```

## Monitoring Production

### Métriques
```bash
# Nombre de requêtes traitées
docker-compose exec postgres psql -U dyleth -d dyleth -c "SELECT COUNT(*) FROM detection_logs;"

# Taux de fraude détecté
docker-compose exec postgres psql -U dyleth -d dyleth -c "SELECT is_fraud, COUNT(*) FROM detection_logs GROUP BY is_fraud;"

# Temps de réponse moyen
docker-compose exec postgres psql -U dyleth -d dyleth -c "SELECT AVG(response_time_ms) FROM detection_logs;"
```

## Conclusion

Toutes ces commandes permettent de:
1. Démarrer le projet
2. Tester l'API
3. Explorer les données
4. Débugger les problèmes
5. Développer de nouvelles fonctionnalités

Le système est maintenant opérationnel et prêt pour le développement des applications mobiles et de l'extension navigateur.
