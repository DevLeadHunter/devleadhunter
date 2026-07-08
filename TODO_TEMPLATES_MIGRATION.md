# ⏳ TODO — Migration templates vers extends (fichier temporaire)

> À supprimer une fois la migration finie. Réf. archi : `TEMPLATES_ARCHITECTURE.md`.
> Templates à migrer : `plumber-simple`, `plumber-signature`, `plumber-atelier`, `plumber-cuivre`, `electrician-lumen`.
> Règle d'or : **ne rien casser dans le tunnel** — demo-host doit continuer à servir les démos à chaque étape.

> **Avancement (2026-07-07)** : Phases 0 et 1 ✅. Repo principal transféré dans l'orga + prod stabilisée
> (login desktop, CORS/500, CI Vercel demo-host, fonts). Prochaine étape : Phase 2 (package `SiteContent`).

---

## Phase 0 — Organisation & outillage ✅

- [x] Créer l'organisation GitHub **`DevLeadHunter`** (repo principal `devleadhunter` transféré dedans)
- [x] Visibilité des repos → **publics** ⇒ **pas de `GIGET_AUTH`** (les `extends` `github:` marchent sans token)
- [x] ~~Personal Access Token~~ — **inutile** (repos publics)
- [x] Convention de tags : `vMAJOR.MINOR.PATCH` (semver)

## Phase 1 — Repo starter `devleadhunter-website-template-starter` ✅

> Livré 2026-07-07 : repo `DevLeadHunter/devleadhunter-website-template-starter` (poussé sur `main`).
> Vérifié : `npm install` + `npm run lint` (0 erreur / 0 warning) + `npm run build` (playground) OK.
> ⚠️ Reste **1 action manuelle** : cocher **Settings → Template repository** dans GitHub.

- [x] Créer le repo dans l'orga — **reste à cocher « Template Repository »** (Settings → Template repository)
- [x] **Nuxt 4** (+ Vue 3.5) — scaffold manuel calqué sur `prepeers-chat-ui`
- [x] **Tailwind v4** (`@tailwindcss/vite`)
- [x] Config layer : `main: ./nuxt.config.ts` + **racine seule auto-importée + sections en relatif** (`ignore: ['**/sections/**']`)
- [x] **Linters** : ESLint (`@nuxt/eslint` + stylistic + typescript-eslint + jsdoc + unused-imports) + Prettier
- [x] **Husky** + **commitlint** (pre-commit lance `npm run lint` — pas de lint-staged, comme prepeers-chat-ui)
- [x] `tsconfig.json` strict
- [x] **Fonts dans la template** — déclarées via `useHead` dans le composant racine (scopées par template)
- [x] **`.playground/`** : `app.vue` rend le composant racine avec le mock `content.ts`
- [x] Scripts `package.json` : `dev` / `build` / `generate` / `preview` ciblant `.playground`
- [x] Section d'exemple (`HeroSection`, `ServicesSection`) + `DevLeadHunterStarterRoot.vue` (props `SiteContent`)
- [x] `README.md` : « Use this template » → renommer → dev en isolé
- [x] Vérifié en isolé (build + lint OK)
- [ ] ⚠️ **Écart assumé** : pas d'i18n (les templates rendent `SiteContent`, pas des clés de langue)
- [x] ✅ **Résolu** : `app/types/SiteContent.ts` re-exporte désormais `@devleadhunter/website-content` (plus de copie locale)

## Phase 2 — Type content commun `@devleadhunter/website-content` ✅

> Livré 2026-07-08 : repo `DevLeadHunter/devleadhunter-website-content` (public, `main` + tag `v1.0.0`).
> Package types-only, build `tsc` → `dist/` (regénéré à l'install via `prepare`). Le starter le
> consomme via `git+https://…#v1.0.0` (public, sans token) et re-exporte le type — validé de bout
> en bout (install github: + build `prepare` + `vue-tsc`/build du starter OK).

- [x] Créer le repo **`devleadhunter-website-content`** (types-only)
- [x] Définir l'interface **`SiteContent`** — **toutes les clés optionnelles** (clé vide = section masquée)
- [x] Exporter `emptySiteContent(): SiteContent`
- [~] Recenser les champs réels des 5 templates + schémas Storyblok → **à affiner pendant le POC** (parti sur le shape transverse de l'archi ; on étend au fil des migrations)
- [x] Build/export propre des `.d.ts` (via `tsc`, `prepare` pour `github:`)
- [x] Tag `v1.0.0`
- [x] Le starter dépend de ce package (pour typer les props)

### Sans rien casser côté API — ⏭️ à faire avec le POC `plumber-cuivre` (Phase 3/4)

- [ ] Vérifier que le `content_json` produit par `api/services/templates/*.py` **est déjà conforme** à `SiteContent` (ou l'ajuster champ par champ)
- [ ] Refléter `SiteContent` côté Python (mirror manuel) — pas de JSON Schema pour l'instant
- [ ] Ajouter un test léger : « le content_json d'une template valide bien le shape `SiteContent` »

## Phase 3 — Un repo par template (× 5)

> Pour **chaque** template ci-dessous : « Use this template » depuis le starter → `devleadhunter-template-<id>`, copier les sections + `index.vue` depuis `demo-host/app/components/templates/<id>/`, typer avec `SiteContent`, mock dans `content.ts`, valider en `.playground`, tagger `v1.0.0`.

- [ ] `devleadhunter-template-plumber-simple`
- [ ] `devleadhunter-template-plumber-signature`
- [ ] `devleadhunter-template-plumber-atelier`
- [x] `devleadhunter-template-plumber-cuivre` ✅ **POC** — créé via `gh --template`, porté (13 sections + racine + `buildCuivreContent(SiteContent)`, copie générique en défauts), lint+build verts, rendu validé (13 sections, thème bleu Source, fonts OK), tag `v1.0.0`. Créé au passage : content `v1.1.0` (+ `heroImage`/`aboutImage`/`about`) + starter aligné.
- [ ] `devleadhunter-template-electrician-lumen` *(embarque GSAP → vérifier qu'il reste dans les deps de CE repo)*

Pour chaque repo, checklist unitaire :
- [ ] Sections importées en **relatif** (pas d'auto-import global) OU composants **préfixés**
- [ ] **Un seul** composant racine exposé, props `content: SiteContent` + `businessName`
- [ ] Fonts de la template déclarées dans son `nuxt.config.ts`
- [ ] `npm run build` isolé OK
- [ ] Tag `v1.0.0`

## Phase 4 — Brancher dans demo-host (extends)

- [ ] Ajouter les 5 `extends` `github:devleadhunter/devleadhunter-template-<id>#v1.0.0` dans `demo-host/nuxt.config.ts`
- [ ] `demo-host/package.json` : dépendance `@devleadhunter/website-content` + token GitHub configuré (`.npmrc` / env CI)
- [ ] Mettre à jour le dispatch dans `DemoSiteView.vue` : `template_id → composant racine` (garder `defineAsyncComponent` pour le code-split)
- [ ] `demo-host` passe un `SiteContent` typé unique (plus de typage par-template)
- [ ] **Supprimer** l'ancien dossier `demo-host/app/components/templates/` une fois les 5 migrées
- [ ] Retirer les fonts des templates du `<head>` global de `demo-host/nuxt.config.ts`

## Phase 5 — Vérification (ne rien casser)

- [ ] `demo-host` build + run OK
- [ ] Chaque template rend correctement une démo réelle (1 slug par template)
- [ ] **Visual editor Storyblok** + preview draft toujours fonctionnels
- [ ] **Tracking PostHog** démo toujours actif (status `active` uniquement)
- [ ] Vérifier le **code-split** : une démo ne charge que le chunk de sa template
- [ ] Tester l'ajout **et** la suppression d'une template (1 ligne)

## Phase 6 — Bonus (après migration de base)

- [ ] POC du **build prod dédié client** : app fine qui `extends` **une seule** template (pour Vercel per-client)
- [ ] CI par repo template (lint + build sur tag)
- [ ] Documenter le workflow de release (tag → bump du `#vX.Y.Z` dans demo-host)
- [ ] **Supprimer ce fichier** 🎉

---

### Ordre recommandé & filet de sécurité

1. Phases 0→2 d'abord (orga, starter, type). Rien ne bouge encore dans demo-host.
2. Migrer **`plumber-cuivre` en premier** comme **POC** (Phase 3 + 4 sur une seule template), valider en Phase 5.
3. Une fois le POC vert, dérouler les 4 autres templates.
4. Garder l'ancien dossier `templates/` **jusqu'à ce que les 5 soient vertes** — ne le supprimer qu'à la toute fin.
