#!/bin/bash

echo "DYLETH - Installation et Démarrage"
echo "===================================="
echo ""

cd /home/claude/dyleth-project/backend

echo "1. Copie du fichier .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   Fichier .env créé"
else
    echo "   .env existe déjà"
fi

echo ""
echo "2. Démarrage des services Docker..."
docker-compose up -d

echo ""
echo "3. Attente démarrage PostgreSQL (20s)..."
sleep 20

echo ""
echo "4. Exécution migrations base de données..."
docker-compose exec -T api alembic upgrade head

echo ""
echo "===================================="
echo "Installation terminée!"
echo ""
echo "API disponible sur: http://localhost:8000"
echo "Documentation: http://localhost:8000/docs"
echo ""
echo "Services:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Qdrant: localhost:6333"
echo ""
echo "Commandes utiles:"
echo "  - Logs: docker-compose logs -f api"
echo "  - Stop: docker-compose down"
echo "  - Restart: docker-compose restart api"
echo ""
