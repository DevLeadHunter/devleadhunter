# Installation et Lancement

## 1. Installation des dépendances

```bash
cd server
pip install -r requirements.txt
```

## 2. Configuration

Créez un fichier `.env` dans le dossier `server` avec le contenu suivant :

```
ENV=development
DEBUG=true
API_VERSION=v1
API_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 3. Lancement du serveur

### Option 1 : Avec Python (Recommandé pour développement)

```bash
python main.py
```

### Option 2 : Avec Uvicorn directement

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Accéder à l'API

- **API Root**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Test rapide

```bash
# Health check
curl http://localhost:8000/health

# Recherche de prospects
curl -X POST http://localhost:8000/api/v1/prospects/search \
  -H "Content-Type: application/json" \
  -d '{"category":"restaurant","city":"Paris","max_results":10}'
```

