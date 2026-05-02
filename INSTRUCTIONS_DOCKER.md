# Comment utiliser tout ça

## Pour lancer le projet depuis zéro

```bash
# 1. Construire et démarrer tous les services
docker compose up --build

# 2. (Premier lancement) Télécharger le modèle Ollama
docker exec -it vulnops-ollama ollama pull gemma4:31b-cloud
```

## Ce qui a été créé

| Fichier | Rôle |
| :--- | :--- |
| `backend/Dockerfile` | Image Python 3.13 + dépendances Django |
| `frontend/Dockerfile` | Image Node 20 + Vite dev server |
| `docker-compose.yml` | Orchestre tous les services |

## Services dans le docker-compose

| Service | Port | Description |
| :--- | :--- | :--- |
| `postgres` | 5432 | Base de données PostgreSQL |
| `redis` | 6379 | Cache + queue Celery |
| `backend` | 8000 | Django (migrate auto au démarrage) |
| `celery` | — | Worker Celery |
| `frontend` | 5173 | React/Vite |
| `ollama` | 11434 | LLM local (modèle IA) |

## Points importants

- Le `backend/.env` est chargé automatiquement — les variables `DB_HOST`, `CELERY_BROKER_URL` et `OLLAMA_API_URL` sont surchargées pour pointer vers les containers (pas localhost).
- Les données Postgres et Ollama sont persistées dans des volumes Docker (survie aux `docker compose down`).
- Pour tout supprimer proprement : `docker compose down -v`
