# DYLETH - Guide de Démarrage Rapide

## Installation Complète en 3 Étapes

### Étape 1: Installation et démarrage
```bash
cd /home/claude/dyleth-project
./scripts/install.sh
```

Cette commande va:
- Créer le fichier .env
- Démarrer PostgreSQL, Redis, Qdrant
- Démarrer l'API FastAPI
- Créer les tables de base de données

### Étape 2: Insérer des données de test
```bash
docker-compose exec api python /app/scripts/seed_db.py
```

Insère:
- 3 numéros frauduleux
- 3 patterns SMS
- 3 domaines frauduleux

### Étape 3: Tester l'API
```bash
../scripts/test_api.sh
```

## Vérification Manuel

### 1. Vérifier que les services sont démarrés
```bash
docker-compose ps
```

Tous les services doivent être "Up".

### 2. Vérifier les logs
```bash
docker-compose logs -f api
```

### 3. Accéder à la documentation
Ouvrir dans le navigateur:
- http://localhost:8000/docs (Swagger)
- http://localhost:8000/redoc (ReDoc)

## Tests API Manuels

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Réponse attendue:
```json
{"status": "healthy", "version": "1.0.0"}
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

Réponse attendue:
```json
{
  "is_fraud": true,
  "confidence": 0.95,
  "category": "scam",
  "action": "block",
  "similar_cases": 127
}
```

### Test 3: Analyser un SMS suspect
```bash
curl -X POST http://localhost:8000/api/v1/sms/analyze-sms \
  -H "Content-Type: application/json" \
  -d '{
    "content": "URGENT! Payez 2€ pour votre colis: bit.ly/abc",
    "sender": "+33612345678"
  }'
```

Réponse attendue:
```json
{
  "is_fraud": true,
  "confidence": 0.85,
  "risk_factors": ["Urgence factice", "Demande de paiement", "Lien suspect"]
}
```

## Arrêter les services

```bash
docker-compose down
```

## Redémarrer les services

```bash
docker-compose up -d
```

## Voir les logs en temps réel

```bash
docker-compose logs -f api
```

## Accéder à PostgreSQL

```bash
docker-compose exec postgres psql -U dyleth -d dyleth
```

Commandes SQL utiles:
```sql
\dt                          -- Lister les tables
SELECT * FROM users LIMIT 5;
SELECT * FROM fraudulent_numbers;
SELECT * FROM detection_logs ORDER BY timestamp DESC LIMIT 10;
```

## Accéder à Redis CLI

```bash
docker-compose exec redis redis-cli
```

Commandes Redis:
```
KEYS *
GET phone:+33756123456
```

## Architecture des Services

```
Port 8000:  API FastAPI
Port 5432:  PostgreSQL
Port 6379:  Redis
Port 6333:  Qdrant (Vector DB)
```

## Prochaines Étapes

1. Développer les applications mobiles (Android/iOS)
2. Créer l'extension navigateur
3. Entraîner les modèles ML
4. Implémenter le système de crowdsourcing
5. Ajouter l'authentification JWT
6. Déployer en production

## Support

Pour toute question, consulter:
- Documentation API: http://localhost:8000/docs
- README principal: /home/claude/dyleth-project/README.md
