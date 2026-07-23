# Documentation DevLeadHunter

Documentation produit et technique du monorepo. Le code applicatif vit dans `web/`, `api/` et `demo-host/`.

| Document | Description |
| -------- | ----------- |
| [BUSINESS_PLAN.md](./BUSINESS_PLAN.md) | Modèle économique, funnel, projections |
| [TEMPLATES_ARCHITECTURE.md](./TEMPLATES_ARCHITECTURE.md) | Architecture des templates (layers Nuxt, Storyblok, registre API) |
| [LOCAL_DEV.md](./LOCAL_DEV.md) | Développement local (API, web, demo-host, Docker) |
| [STRIPE_SETUP.md](./STRIPE_SETUP.md) | Configuration Stripe (crédits + commandes website) |
| [R2_STORAGE_PLAN.md](./R2_STORAGE_PLAN.md) | Plan stockage Cloudflare R2 (vidéos, médias) |
| [INTEGRATION_MAQUETTE_DEVLEADHUNTER.txt](./INTEGRATION_MAQUETTE_DEVLEADHUNTER.txt) | Notes d'intégration maquette |

## Standards de code par module

| Module | Fichier |
| ------ | ------- |
| Web (Nuxt 4 + Tauri) | [`../web/STANDARDS_CODE_ET_ARCHITECTURE.md`](../web/STANDARDS_CODE_ET_ARCHITECTURE.md) |
| API (FastAPI) | [`../api/STANDARDS_CODE_ET_ARCHITECTURE.md`](../api/STANDARDS_CODE_ET_ARCHITECTURE.md) |
| Demo host (Nuxt renderer) | [`../demo-host/STANDARDS_CODE_ET_ARCHITECTURE.md`](../demo-host/STANDARDS_CODE_ET_ARCHITECTURE.md) |
