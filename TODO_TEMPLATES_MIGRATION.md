# ⏳ TODO — Migration templates vers extends (fichier temporaire)

> À supprimer une fois la migration finie. Réf. archi : `TEMPLATES_ARCHITECTURE.md`.
> Templates à migrer : `plumber-simple`, `plumber-signature`, `plumber-atelier`, `plumber-cuivre`, `electrician-lumen`.
> Règle d'or : **ne rien casser dans le tunnel** — demo-host doit continuer à servir les démos à chaque étape.

---

## Phase 0 — Organisation & outillage

- [ ] Créer l'organisation GitHub **`devleadhunter`**
- [ ] Définir la visibilité des repos (privés → prévoir un token `GIGET_AUTH` pour les `extends`)
- [ ] Créer un **Personal Access Token** GitHub (scope repo) pour dev local + CI
- [ ] Choisir la convention de tags : `vMAJOR.MINOR.PATCH` (semver)

## Phase 1 — Repo starter `devleadhunter-website-template-starter`

- [ ] Créer le repo dans l'orga et le marquer **Template Repository** (Settings → Template repository)
- [ ] `npx nuxi init .` → **Nuxt 4** (+ Vue 3.5)
- [ ] Ajouter **Tailwind v4** (`@tailwindcss/vite` + plugin vite, comme demo-host/prepeers)
- [ ] Config layer : `nuxt.config.ts` avec `main: ./nuxt.config.ts`, `components` **préfixés** (ou racine seule + sections en relatif)
- [ ] **Linters** : ESLint (`@nuxt/eslint` + stylistic + typescript-eslint + jsdoc + unused-imports) + Prettier (reprendre la config prepeers-chat-ui)
- [ ] **Husky** + **commitlint** (conventional commits) + lint-staged
- [ ] `tsconfig.json` strict (aligné standards de code)
- [ ] Déclarer les **fonts dans la template** (plus dans un `<head>` partagé)
- [ ] Créer le **`.playground/`** : `app.vue` qui rend le composant racine avec un mock `SiteContent`
- [ ] Scripts `package.json` : `dev` / `build` / `generate` / `preview` ciblant `.playground` (modèle prepeers-chat-ui)
- [ ] Section d'exemple + `TemplateRoot.vue` d'exemple (props typées `SiteContent`)
- [ ] `README.md` : comment cloner → renommer → dev en isolé
- [ ] Vérifier : `npm run dev` sur le `.playground` fonctionne en isolé

## Phase 2 — Type content commun `@devleadhunter/website-content`

- [ ] Créer le repo **`devleadhunter-website-content`** (types-only)
- [ ] Définir l'interface **`SiteContent`** — **toutes les clés optionnelles** (clé vide = section masquée)
- [ ] Exporter `emptySiteContent(): SiteContent`
- [ ] Recenser les champs réels utilisés par les 5 templates + les schémas Storyblok existants → n'inclure que le **transverse**
- [ ] Build/export propre des `.d.ts` (consommable via `github:` ou npm privé)
- [ ] Tag `v1.0.0`
- [ ] Le starter dépend de ce package (pour typer les props)

### Sans rien casser côté API

- [ ] Vérifier que le `content_json` produit par `api/services/templates/*.py` **est déjà conforme** à `SiteContent` (ou l'ajuster champ par champ)
- [ ] Refléter `SiteContent` côté Python (mirror manuel) — pas de JSON Schema pour l'instant
- [ ] Ajouter un test léger : « le content_json d'une template valide bien le shape `SiteContent` »

## Phase 3 — Un repo par template (× 5)

> Pour **chaque** template ci-dessous : « Use this template » depuis le starter → `devleadhunter-template-<id>`, copier les sections + `index.vue` depuis `demo-host/app/components/templates/<id>/`, typer avec `SiteContent`, mock dans `content.ts`, valider en `.playground`, tagger `v1.0.0`.

- [ ] `devleadhunter-template-plumber-simple`
- [ ] `devleadhunter-template-plumber-signature`
- [ ] `devleadhunter-template-plumber-atelier`
- [ ] `devleadhunter-template-plumber-cuivre`
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
