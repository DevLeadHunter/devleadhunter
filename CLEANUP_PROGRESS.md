# Cleanup B2B — suivi de progression

> Mis à jour au fil de l'exécution. ✅ = relu + corrigé + lint/tests OK sur le lot.

## Lots

| Lot | Scope | Statut |
|-----|-------|--------|
| A | Racine + `docs/` — ménage structurel | ✅ |
| B | `web/app/types/**` — `interface` → `type` | ✅ |
| C | `web/app/**` — `Ref<T>` manquant sur `ref()` | ✅ |
| D | `web/app/**/*.vue` — JSDoc fonctions (ESLint activé) | ✅ |
| E | `api/**` — Pydantic v2 `ConfigDict` | ✅ |
| F | `api/services/**` — classes (`DemoSiteCleanupRunner`, `DemoIdentityResolver`) | ✅ |
| G | `npm run lint` + `pytest` | ✅ |

## Notes

- `CLEANUP_PLAN.md` supprimé (remplacé par ce fichier + `QUALITE_B2B_PROGRESS.md`).
- Commit unique recommandé : ménage structurel + passe qualité B2B.
