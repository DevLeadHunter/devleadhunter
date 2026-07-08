# ⏳ TODO — Migration templates vers extends (fichier temporaire)

> À supprimer une fois la migration finie. Réf. archi : `TEMPLATES_ARCHITECTURE.md`.
> Templates actuelles (4) : `plumber-signature` (défaut), `plumber-atelier`, `plumber-cuivre`, `electrician-lumen`. *(`plumber-simple` retiré + repo archivé le 2026-07-08 — jugé trop générique.)*
> Règle d'or : **ne rien casser dans le tunnel** — demo-host doit continuer à servir les démos à chaque étape.

> ## 🟢 ÉTAT AU 2026-07-08 — migration TERMINÉE, déployée, legacy retiré, `plumber-simple` supprimé
>
> **Les 4 templates sont migrées en Nuxt layers, branchées dans le tunnel, mergées sur `main`,
> déployées et VALIDÉES visuellement** (rendu vérifié bout-en-bout sur les 5 avec un vrai prospect,
> screenshots à l'appui). **Le legacy a été retiré** (Léo a confirmé aucun site vendu d'avant en ligne) —
> il ne reste que des **bonus optionnels** (Phase 6). ⚠️ La validation avait révélé et **corrigé un bug de
> rendu prod** — voir ci-dessous.
>
> **Fait ✅**
> - Phase 0 (orga + outillage) et 1 (prod stabilisée : login desktop, CORS/500, CI Vercel, fonts).
> - Phase 2 : package `@devleadhunter/website-content` (type `SiteContent`, types-only, tag **v1.1.0**),
>   consommé par demo-host + les 5 repos template via `git+https://…#v1.1.0`.
> - Phase 3 : les **5 repos template** créés dans l'orga + taggés :
>   `plumber-simple` **v1.0.0**, `plumber-signature` **v1.0.0**, `plumber-atelier` **v1.0.0**,
>   `plumber-cuivre` **v1.0.1**, `electrician-lumen` **v1.0.0**. Chacun = 1 root auto-registered
>   (`PlumberSimpleRoot`, `PlumberSignatureRoot`, `PlumberAtelierRoot`, `PlumberCuivreRoot`,
>   `ElectricianLumenRoot`) + sections en imports relatifs (`ignore: ['**/sections/**']`). **Pas de
>   `modules` dans les `nuxt.config.ts` des layers** (le `@nuxt/eslint` dev-only vit dans `.playground`).
> - Phase 4 : `demo-host/nuxt.config.ts` = les **5 `extends`** ; `DemoSiteView.vue` = **dispatch généralisé**
>   (`MIGRATED_ROOTS` = template_id→nom du root ; `LEGACY_COMPONENTS` = fallback in-repo pour les vieilles
>   démos rich-content pendant leur TTL 14 j ; rend le root migré **si** le contenu est un `SiteContent`,
>   sinon le legacy). `richCuivreToSiteContent.ts` supprimé.
> - Phase 4b : l'**API produit le `SiteContent` plat** pour les 5. Module partagé
>   `api/services/templates/site_content.py` (schémas Storyblok natifs `site_content*`, mapper
>   prospect+enrichment, défauts éditoriaux par métier). Les 5 modules exposent `build_site_content(...)`
>   → `registry.uses_site_content()` route dessus ; `storyblok_service.build_content_json` bascule
>   auto. Sanity-check : **5/5 PASS**, schéma `site_content` dédupliqué à **1** (63 schémas, tous uniques).
> - **Commit poussé** sur `feat/wire-4-templates-into-demo-host` (8 fichiers : site_content.py + 4 modules
>   API + demo-host nuxt.config + DemoSiteView + suppression richCuivre). demo-host build vert (5 layers).
>
> **Fait depuis ✅**
> - Mergé sur `main` (`4ad9191` + merge `25ce674`), deploys API (VPS) + demo-host (Vercel) verts.
> - 🔴→🟢 **Bug de rendu prod corrigé** (`38c46f0`) : `DemoSiteView` passait un **nom en chaîne** à
>   `<component :is>` — or les composants Nuxt auto-importés ne sont pas résolvables par chaîne →
>   **toute démo migrée rendait vide**. Fix : import des `Lazy*Root` depuis `#components` (objets
>   composant, code-split conservé). Le build Vercel vert ne l'attrapait pas (bug runtime). Voir
>   mémoire `demo-host-template-dispatch-components` + gotcha n°4 de `TEMPLATES_ARCHITECTURE.md`.
> - **Validation des 5** via le harnais `/preview-layers?t=<id>` (vrai `DemoSiteView` + `SiteContent`
>   généré par l'API, vrai prospect **Plomberie Roche** / **Breizh Electrik**) : dispatch OK, palette
>   par template OK, contenu métier OK, **0 erreur console** (dont GSAP lumen), code-split confirmé au build.
> - Starter marqué **GitHub Template repository** (`is_template=true` via `gh api`).
>
> **Fait encore depuis ✅**
> - 🧹 **Legacy retiré (2026-07-08)** — Léo a confirmé « aucun site vendu d'avant en ligne ». Supprimés :
>   `demo-host/app/components/templates/*`, les entrées `LEGACY_COMPONENTS` (+ `DemoSiteView` simplifié au
>   seul chemin `SiteContent`), les fonts globales du `<head>` (chaque layer déclare les siennes), et les
>   5 pages `preview-*` legacy. Build Vercel vert, bundle **−0,4 MB**. Harnais `/preview-layers` conservé.
>
> **Reste à faire ⏳**
> 1. (Optionnel) Bonus Phase 6 : build prod dédié client, CI par repo template, doc du workflow de release.
> 2. Supprimer ce fichier quand tu veux — la migration est **fonctionnellement terminée**.
>
> **📸 Observation produit** : 3 templates sur 5 affichent la photo hero du prospect (signature, cuivre,
> lumen) ; **simple** (hero dégradé) et **atelier** (DA typographique « Fiche d'intervention ») ne
> l'affichent pas — choix de design, mais les photos enrichies n'y sont pas valorisées. À arbitrer.
>
> **⚠️ Caveats connus**
> - `plumber-signature` : le portage a **remplacé GSAP (parallax/scroll-scrub) par IntersectionObserver** —
>   fidélité d'anim légèrement dégradée vs l'original. À revoir si Léo veut l'anim exacte.
> - `plumber-signature` : la section **avant/après n'a pas de champ `SiteContent`** → elle s'auto-masque.
> - `plumber-cuivre` **non refactorisé** vers le module partagé (garde son `build_site_content`/`_SERVICE_ITEMS`/
>   `_FAQ_ITEMS` sur-mesure, 8 services / 8 FAQ) — choix low-risk car il est déjà live. Les 4 autres
>   utilisent les défauts génériques `site_content.py` (6 services / 5 FAQ par métier).

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

- [x] Créer le repo dans l'orga + **coché « Template Repository »** (`is_template=true` via `gh api`, 2026-07-08)
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

- [x] `content_json` conforme à `SiteContent` — les 5 modules produisent un `SiteContent` plat (`build_site_content`)
- [x] `SiteContent` reflété côté Python (mirror manuel dans `site_content.py` + `to_storyblok_site_content`)
- [~] Test léger de conformité — couvert par le harnais `/preview-layers` + le sanity-check (5/5 PASS) ; pytest formel = optionnel

## Phase 3 — Un repo par template (× 5)

> Pour **chaque** template ci-dessous : « Use this template » depuis le starter → `devleadhunter-template-<id>`, copier les sections + `index.vue` depuis `demo-host/app/components/templates/<id>/`, typer avec `SiteContent`, mock dans `content.ts`, valider en `.playground`, tagger `v1.0.0`.

- [x] ~~`devleadhunter-template-plumber-simple`~~ ✅ v1.0.0 — **retiré du système + repo archivé le 2026-07-08** (trop générique)
- [x] `devleadhunter-template-plumber-signature` ✅ v1.0.0
- [x] `devleadhunter-template-plumber-atelier` ✅ v1.0.0
- [x] `devleadhunter-template-plumber-cuivre` ✅ **POC** — créé via `gh --template`, porté (13 sections + racine + `buildCuivreContent(SiteContent)`, copie générique en défauts), lint+build verts, rendu validé (13 sections, thème bleu Source, fonts OK), tag `v1.0.0`. Créé au passage : content `v1.1.0` (+ `heroImage`/`aboutImage`/`about`) + starter aligné.
- [x] `devleadhunter-template-electrician-lumen` ✅ v1.0.0 *(GSAP embarqué dans les deps de CE repo)*

Pour chaque repo, checklist unitaire :
- [x] Sections importées en **relatif** (`ignore: ['**/sections/**']`) — vérifié dans les 5 layers
- [x] **Un seul** composant racine exposé (`<Id>Root`), props `content: SiteContent`
- [x] Fonts de la template déclarées via `useHead` dans le root (ex. `PlumberSignatureRoot` → Archivo + Bricolage)
- [x] `npm run build` isolé OK (+ build demo-host agrégé vert)
- [x] Tag `v1.0.0` (cuivre `v1.0.1`)

## Phase 4 — Brancher dans demo-host (extends)

- [x] Ajouter les 5 `extends` `github:DevLeadHunter/devleadhunter-template-<id>#vX.Y.Z` dans `demo-host/nuxt.config.ts`
- [x] `demo-host/package.json` : dépendance `@devleadhunter/website-content` (repos publics → **pas de token**)
- [x] Mettre à jour le dispatch dans `DemoSiteView.vue` : `template_id → composant racine` (`MIGRATED_ROOTS`, `defineAsyncComponent` conservé)
- [x] `demo-host` passe un `SiteContent` typé unique (plus de typage par-template)
- [x] **Supprimé** l'ancien dossier `demo-host/app/components/templates/` + entrées `LEGACY_COMPONENTS` (2026-07-08)
- [x] Retiré les fonts globales du `<head>` de `demo-host/nuxt.config.ts` (chaque layer déclare les siennes)

## Phase 5 — Vérification (ne rien casser)

- [x] `demo-host` build + run OK (build Vercel preset vert + dev run)
- [x] Chaque template rend correctement (5/5 validés via `/preview-layers`, vrai prospect, screenshots)
- [ ] **Visual editor Storyblok** + preview draft toujours fonctionnels *(non re-testé — nécessite un space Storyblok)*
- [ ] **Tracking PostHog** démo toujours actif (status `active` uniquement) *(inchangé ; à confirmer sur une vraie démo)*
- [x] Vérifier le **code-split** : une démo ne charge que le chunk de sa template (chunks de sections séparés au build)
- [~] Tester l'ajout **et** la suppression d'une template *(ajout prouvé ×5 ; suppression = retirer 1 extends + 1 dispatch + 1 module, non exécuté)*

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
