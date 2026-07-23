# Plan qualité B2B — DevLeadHunter

> Suivi de la passe « niveau B2B ». Mettre à jour les cases au fur et à mesure.

**Dernière mise à jour** : 23/07/2026 — passe complète validée (lint + pytest OK).

Légende : `[ ]` à faire · `[~]` en cours · `[x]` validé (lint/tests OK sur le lot)

---

## 1. `web/app/types/` — `interface` → `type`

> 3 `interface` conservées volontairement (`extends`) : `Automation.ts`, `index.ts` (`SupportTicketDetail`), `campaignService.ts` (`CampaignDetailResponse`).

| Fichier | Statut |
|---------|--------|
| Tous les fichiers `web/app/types/` | [x] |

## 2. `web/app/` — `Ref<T>` manquant sur `ref()`

| Lot | Statut |
|-----|--------|
| 9 pages/composants identifiés | [x] |

## 3. API Python — Pydantic v2 `ConfigDict`

| Lot | Statut |
|-----|--------|
| `models/*.py` (health, prospect, search, scraping_job) | [x] |
| `schemas/email_*.py` | [x] |
| `schemas/enrichment.py`, `order.py`, `demo_site.py` | [x] |
| `api/v1/routes/settings.py` | [x] |
| `Field(example=…)` → `json_schema_extra` (prospect) | [x] |

## 4. API — services à auditer (classes)

| Lot | Statut |
|-----|--------|
| `demo_site_cleanup_service.py` → `DemoSiteCleanupRunner` | [x] |
| `demo_identity.py` → `DemoIdentityResolver` | [x] |
| `api/services/*.py` (racine) — reste helpers légitimes | [x] |
| `api/services/templates/` — builders par template | [x] |
| `api/services/decision_maker/` — stratégies + resolver | [x] |

## 5. Composables / services TS (interfaces restantes)

| Lot | Statut |
|-----|--------|
| `composables/` | [x] |
| `services/` | [x] |
| `stores/` | [x] |
| `utils/` | [x] |

## 6. Validation finale

| Check | Statut |
|-------|--------|
| `npm run lint` (web) | [x] |
| `pytest` (api) | [x] |

## 7. JSDoc manquants dans `.vue`

> Règle ESLint `jsdoc/require-jsdoc` réactivée sur `**/*.vue` (23/07/2026).

| Lot | Statut |
|-----|--------|
| `app/components/` | [x] |
| `app/pages/` | [x] |
| `app/composables/` | [x] (déjà linté via `.ts`) |
