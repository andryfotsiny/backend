# ─────────────────────────────────────────────
# DYLETH API — Dockerfile
# Python 3.11 slim
# ─────────────────────────────────────────────

FROM python:3.11-slim

# Métadonnées
LABEL maintainer="Dyleth"
LABEL version="1.0.0"

# Variables d'environnement système
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements en premier (cache Docker layer)
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Télécharger le modèle spaCy
RUN python -m spacy download fr_core_news_sm || \
    python -m spacy download en_core_web_sm || \
    echo "spaCy model download skipped"

# Copier le code source
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p /app/models/ml_models /app/data/datasets

# Port exposé
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]