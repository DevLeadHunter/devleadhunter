# Développement local (parité prod)

Stack locale identique à la prod, avec **base de données locale** et **demo-host local**.

## Prérequis

- MySQL local (`localhost:3310`) — voir `api/INSTALL.md`
- Node.js 20+
- Python 3.11+

## Configuration (`api/.env`)

```env
ENV=development
DATABASE_URL=mysql+pymysql://root:root@localhost:3310/devleadhunter
FRONTEND_URL=http://localhost:3000
DEMO_HOST_BASE_URL=http://localhost:3001
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:1420

# Storyblok : token de DEV (compte séparé de la prod) ou vide = mode mock
STORYBLOK_MANAGEMENT_TOKEN=
STORYBLOK_REGION=eu
```

**Prod** : `DEMO_HOST_BASE_URL=https://demo.dibodev.fr` (GitHub Actions / secrets serveur).

## Lancer tout d'un coup

```bash
# À la racine du monorepo
npm install
npm run dev
```

Ou manuellement (3 terminaux) :

| Terminal | Commande | URL |
|----------|----------|-----|
| 1 | `cd api && python run_dev.py` | http://localhost:8000 |
| 2 | `cd web && npm run dev` | http://localhost:3000 |
| 3 | `cd demo-host && npm run dev` | http://localhost:3001 |

## Flux demo sites en local

1. Créer un site depuis http://localhost:3000/dashboard/demo-sites/create
2. L'API enregistre en **DB locale** et appelle Storyblok (si token configuré)
3. URL générée : `http://localhost:3001/{slug}`
4. Ouvrir cette URL → demo-host local lit l'API locale

## Storyblok

- **Avec token** : espaces Storyblok réels (utiliser un token/compte **dev**)
- **Sans token** : mode mock — `content_json` en DB, pas d'espace Storyblok
- **Éditeur visuel Storyblok** : nécessite une URL publique (ngrok) car Storyblok ne peut pas joindre `localhost`

## Migrations

```bash
cd api && python migrations/run_migrations.py
```

## Playwright (recherche / enrichissement Google Maps)

Requis pour la recherche de prospects et l'enrichissement depuis Google Maps :

```bash
cd api
pip install playwright
playwright install chromium
```
