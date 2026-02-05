
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
Migration initiale:
```bash
docker-compose exec api alembic upgrade head
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

cd ~/Bureau/workspace/dyleth-project/backend
python3.11 -m venv venv
source venv/bin/activate.fish
pip install -r requirements.txt

# 3. Services
sudo systemctl start postgresql redis
docker run -d -p 6333:6333 qdrant/qdrant

# 4. Base de données
sudo -u postgres psql -c "CREATE DATABASE dyleth;"
sudo -u postgres psql -c "CREATE USER dyleth WITH PASSWORD 'dyleth123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dyleth TO dyleth;"

# 6. Migrations
alembic upgrade head
python scripts/seed_db.py

# 7. Démarrer
uvicorn app.main:app --reload
