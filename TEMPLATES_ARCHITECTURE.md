# Architecture des templates de sites — DevLeadHunter

> Comment sont organisées, développées, versionnées et rendues les templates de site
> web vendues aux artisans. Ce document est la **source de vérité** de la logique
> « un repo par template + Nuxt layers (extends) ».

## TL;DR

- **1 template = 1 repo GitHub** dans l'organisation `devleadhunter`, autonome et buildable seul.
- Chaque repo template est un **Nuxt layer** ; il ne connaît **rien** du tunnel (ni Storyblok, ni PostHog, ni slug, ni base de données). Il reçoit un `content` typé en props et rend un beau site. C'est tout.
- **demo-host** (dans ce repo) est le **host** : il possède toute l'intégration (Storyblok, PostHog, fetch par slug) et `extends` les templates depuis GitHub, versionnées par tag.
- **Un seul type `SiteContent`** partagé par toutes les templates, **toutes les clés optionnelles** (clé vide = section masquée).
- Ajouter une template = 1 ligne dans les `extends` + 1 module Python. La supprimer = supprimer le repo + retirer la ligne + retirer le module.

## Pourquoi ce découpage

L'ancien modèle mettait **toutes** les templates dans `demo-host/app/components/templates/`. Problèmes : tout redéployait ensemble, pas de dev isolé, et supprimer une template = chirurgie dans un dossier partagé.

Le nouveau modèle vise **un maximum de séparation** :

| Besoin | Réglé par |
|---|---|
| 1 repo par template dans l'orga | repos GitHub indépendants |
| Build isolé (que cette template) | `.playground` par repo |
| Supprimer une template = simple | delete repo + 1 ligne + 1 module Python |
| Modifier une template = 1 seul endroit | son repo |
| Pas de duplication de la logique qui bouge | Storyblok / PostHog centralisés dans demo-host |
| Mises à jour maîtrisées | pinning `#vX.Y.Z` sur les `extends` |

### L'idée clé : inverser la dépendance

Avant, la template « connaissait » le tunnel (elle vivait à côté du bridge Storyblok et du tracking). **On inverse :**

> Une template ne sait **rien** de Storyblok, PostHog, du slug, de la base. C'est une app
> Nuxt **pure** : `content` typé en entrée → site rendu en sortie.

Toute l'intégration (bridge Storyblok, tracking démo, fetch par slug, type `DemoSitePublic`, CSP…) vit **une seule fois** dans `demo-host`. Conséquence directe : le code qui **bouge et où un bug coûte cher** n'est jamais dupliqué → **aucun problème de propagation**. Les repos templates ne contiennent que du code **à faible churn** (scaffold Nuxt, lint, leurs propres composants) ; s'il diverge d'un repo à l'autre, ce n'est pas grave.

## Les repos

### 1. Le starter — `devleadhunter-website-template-starter`

GitHub **Template Repository** (bouton « Use this template »). C'est le « init Nuxt 4 à jour » :

- Nuxt 4 + Vue 3.5 + Tailwind v4
- eslint / prettier / tsconfig / husky / commitlint (les standards de code)
- dépendance vers `@devleadhunter/website-content` (le type partagé)
- un `.playground/` prêt à dev/build en isolé
- une section d'exemple + un `index.vue` racine d'exemple
- les fonts déclarées **dans la template** (plus dans un `<head>` partagé)

Créer une nouvelle template = « Use this template » → nouveau repo `devleadhunter-template-<id>`.

### 2. Une template — `devleadhunter-template-<id>`

Exemples : `devleadhunter-template-plumber-cuivre`, `devleadhunter-template-electrician-lumen`.

À la fois une **app Nuxt autonome** et un **layer** (`main: ./nuxt.config.ts`). Contient **uniquement** :

```
devleadhunter-template-plumber-cuivre/
  nuxt.config.ts            # layer : components préfixés, fonts, css
  app/
    components/
      PlumberCuivreRoot.vue  # LE composant racine, seul point d'entrée public
      sections/…             # sections importées en RELATIF (jamais globales)
  content.ts                # un MOCK de SiteContent pour le playground (pas un type)
  .playground/
    app.vue                 # rend PlumberCuivreRoot avec le mock → dev/build isolé
  package.json
  eslint.config.mjs …
```

- Ne dépend **jamais** de `demo-host` ni de l'API.
- Dépend de `@devleadhunter/website-content` pour typer ses props.
- `npm run dev` / `npm run build` dans le `.playground` **ne build que cette template**.
- Supprimer la template = **supprimer le repo**.

### 3. Le contrat partagé — `@devleadhunter/website-content`

Mini-repo `devleadhunter-website-content` (types-only). Exporte :

- l'interface `SiteContent` (voir plus bas)
- un helper `emptySiteContent(): SiteContent`

Consommé par **chaque template repo** ET par **demo-host**. Une seule source de vérité, versionnée par tag → pas de drift. (On ne met **pas** ce type dans le starter, sinon il serait **copié** dans chaque template et divergerait.)

### 4. Le host — `demo-host/` (dans ce repo devleadhunter)

Possède tout le tunnel et tire les templates via les **layers Nuxt** depuis GitHub :

```ts
// demo-host/nuxt.config.ts
export default defineNuxtConfig({
  extends: [
    'github:devleadhunter/devleadhunter-template-plumber-cuivre#v1.3.0',
    'github:devleadhunter/devleadhunter-template-electrician-lumen#v1.1.0',
  ],
})
```

- `[slug].vue` fetch le site, résout le `content` (Storyblok draft ou `content_json`), et le passe **typé** au composant racine de la template.
- Le dispatch `template_id → composant racine` reste en **`defineAsyncComponent`** → chaque démo prospect n'embarque que **son** chunk de template.
- Repos privés → la CI/dev a besoin d'un token GitHub (`GIGET_AUTH`). C'est la seule plomberie.
- Ajouter une template = 1 ligne dans `extends`. La retirer = supprimer la ligne.

## Le contrat entre template et tunnel

Seuls **trois** points couplent une template au reste du système (c'est l'interface, pas de la dette) :

1. le **`template_id`** (string, ex. `plumber-cuivre`)
2. le type **`SiteContent`** (dans `@devleadhunter/website-content`, importé des deux côtés)
3. le builder **`api/services/templates/<id>.py`** qui produit un `content_json` **conforme à `SiteContent`**

Storyblok et PostHog restent **côté demo-host**. La template ne les voit jamais.

### Le type `SiteContent` (partagé, tout optionnel)

Un seul modèle pour toutes les templates (elles rendent le même genre de site artisan ;
seule la DA change). **Toutes les clés sont optionnelles** — une clé vide/absente masque
la section correspondante.

```ts
// @devleadhunter/website-content
export interface SiteContent {
  businessName?: string
  phone?: string
  email?: string
  city?: string
  area?: string
  subtitle?: string
  palette?: { primary?: string; secondary?: string; accent?: string }

  services?: Array<{ title?: string; description?: string; icon?: string }>
  reviews?: Array<{ author?: string; rating?: number; text?: string }>
  faq?: Array<{ question?: string; answer?: string }>
  gallery?: Array<{ url?: string; alt?: string }>
  zones?: string[]
  openingHours?: Array<{ day?: string; hours?: string }>
  // … étendre ici quand un besoin transverse apparaît, toujours optionnel
}

export function emptySiteContent(): SiteContent {
  return {}
}
```

**Règle** : on n'ajoute au type que ce qui est **transverse** (utile à plusieurs métiers). Un besoin ultra-spécifique à une seule template se gère à l'intérieur de cette template, pas dans le contrat partagé — sinon `SiteContent` devient un god-object.

### Le seam TS ↔ Python

Python ne peut pas importer le type TS. Le builder Python **reflète** `SiteContent` à la main (comme aujourd'hui). Si le drift devient pénible plus tard, passer à une **JSON Schema** comme source de vérité unique, d'où dérivent et le type TS et la validation Python. **Pour l'instant : mirror manuel, c'est suffisant.**

## Build & déploiement — quel bundle contient quoi ?

Deux contextes distincts :

### A. demo-host partagé (phase démo)

- `extends` **toutes** les templates → le **déploiement** contient tout (obligatoire : un seul host sert tous les prospects par slug).
- Grâce au `defineAsyncComponent`, chaque **visiteur** ne télécharge que le **chunk de sa template**.
- ⇒ *Le déploiement contient tout ; le visiteur ne charge que la sienne.*

### B. Site prod dédié au client (après vente)

- Une app **fine** qui `extends` **une seule** template (paramétrée par `template_id` au build).
- ⇒ *Le build ne contient QUE la template du client.* Petit, rapide, propre.
- C'est le bon modèle pour la mise en prod Vercel par client (meilleur que déployer le demo-host complet).

## Les 3 gotchas à ne pas oublier

1. **Collisions d'auto-import.** Deux templates ont chacune `HeroSection.vue`. En layer, Nuxt auto-importe et merge globalement → collision silencieuse (last-wins). **Parade** : soit chaque template préfixe ses composants (`components: [{ path, prefix: 'PlumberCuivre' }]`), soit — recommandé — la template n'expose **qu'un composant racine** et importe ses sections en **relatif** (jamais enregistrées globalement). Zéro collision par construction.

2. **Repos privés = token.** Les layers `github:` passent par giget. Repos privés → `GIGET_AUTH` (token GitHub) en dev **et** en CI. Le pinning `#vX.Y.Z` donne des mises à jour **contrôlées** (bump volontaire).

3. **Fonts par template.** Chaque template layer déclare **ses** fonts ; demo-host les merge via `extends`. Une template supprimée n'alourdit plus les autres. (Avant : un seul `<head>` chargeait les fonts de toutes les templates.)

## Checklists

### Ajouter une template

1. « Use this template » sur `devleadhunter-website-template-starter` → `devleadhunter-template-<id>`.
2. Construire la DA + les sections (voir `reference/templates-design.md` dans le skill).
3. Exposer **un** composant racine ; typer ses props avec `SiteContent`.
4. Fournir un mock dans `content.ts` pour le `.playground`.
5. Tag `v1.0.0`.
6. Côté demo-host : ajouter 1 ligne dans `extends` + l'entrée dans le dispatch `defineAsyncComponent`.
7. Côté API : créer `api/services/templates/<id>.py` (`TEMPLATE_ID`, `TEMPLATE_META`, `build_content` produisant du `SiteContent`) + l'ajouter à `TEMPLATE_MODULES` dans `registry.py`.

### Supprimer une template

1. Supprimer (ou archiver) le repo `devleadhunter-template-<id>`.
2. Retirer sa ligne des `extends` + son entrée du dispatch dans demo-host.
3. Retirer son module de `TEMPLATE_MODULES` dans `api/services/templates/registry.py`.

### Mettre à jour une template

1. Commit + tag `vX.Y.Z` sur le repo template.
2. Bump du `#vX.Y.Z` correspondant dans les `extends` de demo-host.

## Conventions de nommage

- Organisation GitHub : `devleadhunter`
- Starter : `devleadhunter-website-template-starter`
- Templates : `devleadhunter-template-<id>` (ex. `devleadhunter-template-plumber-cuivre`)
- Contrat de contenu : `devleadhunter-website-content` → package `@devleadhunter/website-content`
- `template_id` : identique côté repo, côté dispatch demo-host, et côté module Python.
