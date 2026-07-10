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

### État des templates (2026-07-11)

| `template_id` | Métier | Tag live | Notes |
|---|---|---|---|
| `plumber-signature` | Plombier (**défaut**) | **v1.0.1** | La plus riche (11 sections). v1.0.1 : footer « Propulsé par DevLeadHunter » retiré |
| `plumber-atelier` | Plombier | **v1.1.0** | DA typographique « fiche d'intervention ». v1.1.0 : rend enfin TOUT `SiteContent` (about, galerie, avis, FAQ, horaires, images) + footer retiré |
| `plumber-cuivre` | Plombier | **v1.0.2** | DA bleu eau « Source », 13 sections, marques posées (défauts, non éditables) |
| `electrician-lumen` | Électricien | **v1.0.0** | GSAP embarqué dans SES deps ; ne consomme pas `aboutImage` |

*(`plumber-simple` retiré + archivé le 2026-07-08 — trop générique.)* La migration en layers est
**terminée et en prod** depuis le 2026-07-08 ; le legacy in-repo a été supprimé.

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
- Repos **publics** → les `extends` `github:` (giget) et l'install `git+https` marchent **sans token**. (Un `GIGET_AUTH` ne serait requis que si un repo repassait privé.)
- Ajouter une template = 1 ligne dans `extends`. La retirer = supprimer la ligne.

## Le contrat entre template et tunnel

Seuls **trois** points couplent une template au reste du système (c'est l'interface, pas de la dette) :

1. le **`template_id`** (string, ex. `plumber-cuivre`)
2. le type **`SiteContent`** (dans `@devleadhunter/website-content`, importé des deux côtés)
3. le builder **`api/services/templates/<id>.py`** qui produit un `content_json` **conforme à `SiteContent`**

Storyblok et PostHog restent **côté demo-host**. La template ne les voit jamais.

### Le type `SiteContent` (partagé, tout optionnel)

**Le modèle de contenu (tranché par Léo, 2026-07-08).** On récupère TOUT le contenu réel
du prospect (photos, avis, textes, services…) **une fois**, on le range dans **un seul
`SiteContent` de même forme pour toutes les templates**. But : **switcher de template sans
re-récupérer le contenu**. **Toutes les clés sont optionnelles** — une template rend le
sous-ensemble qu'elle utilise, une clé vide/absente masque la section.

`SiteContent` ne porte que le **contenu variable du prospect**. La **copie éditoriale
générique** (titres de sections, framing craft/process/brands, badges, labels CTA, métriques
trust) vit en **défauts dans chaque template** (c'est du design) — jamais dans `SiteContent`.

**Comment Storyblok et `content_json` se combinent (mécanique réelle, corrigée 2026-07-10)** :
le site public (démo `[slug].vue` **et** site vendu par domaine `index.vue`) rend **toujours
`content_json`** (la copie en DB). Storyblok n'est lu en direct **que dans le Visual Editor**
(query `?_storyblok`, version draft, via `useStoryblokPreview`) — priorité côté demo-host :
live bridge → draft → `content_json`. Le retour se fait par **webhook** : à chaque publication
cliente, Storyblok appelle `POST /api/v1/webhooks/storyblok`, l'API re-fetch la story **publiée**
(CDN, token public du site — le payload n'est jamais cru) et la réaplatit en `SiteContent` via
`from_storyblok_site_content` (`api/services/templates/site_content.py`, miroir Python du bridge
TS `storyblokSiteContentToSiteContent.ts`). Le webhook est enregistré par space au provisioning
(`_register_publish_webhook` — skippé si `API_BASE_URL` est localhost ; secret optionnel
`STORYBLOK_WEBHOOK_SECRET`). Sans ce webhook, les éditions publiées par le client ne seraient
**jamais visibles** sur son site.

```ts
// @devleadhunter/website-content — shape actuel (tag v1.2.0)
export interface SiteContent {
  // Identité / contact
  businessName?: string
  phone?: string
  email?: string
  city?: string
  area?: string

  // Éditorial (les mots du prospect : accroche + histoire plus longue)
  subtitle?: string
  about?: string

  // Copie éditoriale ÉDITABLE PAR LE CLIENT (vide = texte par défaut du template).
  // Pré-remplie à la génération avec la vraie copie du template (voir plus bas).
  heroBadge?: string
  heroPoints?: string[]
  ctaCallLabel?: string
  ctaQuoteLabel?: string
  trustItems?: Array<{ value?: string; label?: string }>
  servicesHeading?: string
  galleryHeading?: string
  reviewsHeading?: string
  faqHeading?: string
  aboutHeading?: string
  contactHeading?: string

  // Médias (photos scrapées/enrichies)
  heroImage?: string
  aboutImage?: string
  gallery?: Array<{ url?: string; alt?: string }>

  // Design
  palette?: { primary?: string; secondary?: string; accent?: string }

  // Contenu structuré (une template rend le sous-ensemble qu'elle utilise)
  services?: Array<{ title?: string; description?: string; icon?: string }>
  reviews?: Array<{ author?: string; rating?: number; text?: string }>
  faq?: Array<{ question?: string; answer?: string }>
  zones?: string[]
  openingHours?: Array<{ day?: string; hours?: string }>
  beforeAfter?: Array<{ before?: string; after?: string; label?: string }>
  // … étendre ADDITIVEMENT (toujours optionnel) quand une template migrée a un besoin transverse
}

export function emptySiteContent(): SiteContent {
  return {}
}
```

**Règle** : on n'ajoute au type que du **transverse** (utile à plusieurs métiers), **toujours
optionnel**. Un besoin ultra-spécifique à une seule template se gère **dans la template** — pas
dans le contrat partagé, sinon `SiteContent` devient un god-object. *(Exception assumée
2026-07-11 : la copie éditoriale COMMUNE aux templates — badge, CTA, titres des 6 sections
partagées, repères de confiance — est montée dans le contrat pour être éditable par le client ;
les headings ultra-spécifiques d'une seule template — craft, process, urgence… — restent des
défauts de la template.)*

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

## Les 4 gotchas à ne pas oublier

1. **Collisions d'auto-import.** Deux templates ont chacune `HeroSection.vue`. En layer, Nuxt auto-importe et merge globalement → collision silencieuse (last-wins). **Parade** : soit chaque template préfixe ses composants (`components: [{ path, prefix: 'PlumberCuivre' }]`), soit — recommandé — la template n'expose **qu'un composant racine** et importe ses sections en **relatif** (jamais enregistrées globalement). Zéro collision par construction.

2. **Repos publics = pas de token.** Les layers `github:` passent par giget ; comme les repos sont **publics**, ni dev ni CI n'ont besoin de `GIGET_AUTH` (il ne redeviendrait nécessaire que si un repo passait privé). Le pinning `#vX.Y.Z` donne des mises à jour **contrôlées** (bump volontaire).

3. **Fonts par template.** Chaque template layer déclare **ses** fonts ; demo-host les merge via `extends`. Une template supprimée n'alourdit plus les autres. (Avant : un seul `<head>` chargeait les fonts de toutes les templates.)

4. **Dispatch par composant, jamais par nom en chaîne.** Le root d'un layer est **auto-importé** mais **pas** enregistré globalement (`app.component()`) → `<component :is="'PlumberCuivreRoot'">` (nom en **chaîne**) ne résout **rien** et rend un **élément littéral vide** (le build reste vert : bug de rendu runtime, pas de compile). **Parade** : `import { LazyPlumberCuivreRoot } from '#components'` et passer l'**objet composant** à `:is`. `Lazy*` = async → le code-split par démo est conservé. (Régression réelle corrigée le 2026-07-08.)

## Caveats connus (hérités de la migration)

- `plumber-signature` : le portage a remplacé **GSAP (parallax/scroll-scrub) par IntersectionObserver** —
  fidélité d'animation légèrement dégradée vs l'original. À revoir si l'anim exacte redevient prioritaire.
- `plumber-signature` : la section **avant/après n'a pas de champ `SiteContent`** → elle s'auto-masque.
- `plumber-cuivre` garde son `build_site_content` sur-mesure (8 services / 8 FAQ) au lieu des défauts
  génériques de `site_content.py` — choix low-risk (déjà live), pas un bug.
- La **copie éditoriale** (titres de sections, CTA, framing, marques) reste des défauts par template,
  **non éditable par le client** — c'est documenté et assumé ; l'ouvrir passerait par des clés
  transverses de `SiteContent` (voir checklist Storyblok).

## Checklists

### Ajouter une template

1. « Use this template » sur `devleadhunter-website-template-starter` → `devleadhunter-template-<id>`.
2. Construire la DA + les sections (voir `reference/templates-design.md` dans le skill).
3. Exposer **un** composant racine ; typer ses props avec `SiteContent`.
4. Fournir un mock dans `content.ts` pour le `.playground`.
5. Tag `v1.0.0`.
6. Côté demo-host : ajouter 1 ligne dans `extends` + l'entrée dans le dispatch `defineAsyncComponent`.
7. Côté API : créer `api/services/templates/<id>.py` (`TEMPLATE_ID`, `TEMPLATE_META`, **`build_site_content`** — appelle `map_prospect_and_enrichment` de `site_content.py` et ajoute ses `services`/`faq` métier) + l'ajouter à `TEMPLATE_MODULES` dans `registry.py`.
8. **Vérifier la checklist Storyblok ci-dessous** — c'est elle qui garantit que le client livré peut vraiment éditer son site.

### Checklist Storyblok d'une template (CMS client fonctionnel)

Le but produit : le client livré ouvre SON space Storyblok et modifie **le plus de choses
possibles** sur son site, seul. La template ne voit jamais Storyblok — ce qui est éditable,
c'est **exactement ce que la template consomme depuis `SiteContent`**. Donc :

1. **Consommer TOUTES les clés de `SiteContent` qui ont un sens pour le métier** — au minimum :
   `businessName`, `phone`, `email`, `city`/`area`, `subtitle`, `about`, `heroImage`,
   `gallery`, `services`, `reviews`, `faq`, `openingHours`, `palette`. Une clé non consommée
   = un champ que le client remplit dans Storyblok **sans effet visible** (contre-exemple
   historique : `plumber-atelier` n'affiche ni avis, ni FAQ, ni galerie, ni horaires — à éviter).
2. **Une clé vide/absente masque la section** (`v-if`) ou tombe sur le défaut du template —
   jamais de crash, jamais de « undefined » à l'écran.
3. **Câbler la copie éditoriale cliente** (depuis le 2026-07-11) : le contrat porte
   `heroBadge`, `heroPoints`, `ctaCallLabel`/`ctaQuoteLabel`, `trustItems` et les 6 titres de
   sections communs. La template les consomme avec fallback sur SES défauts
   (`content.heroBadge || defaults.heroBadge` ; tableaux :
   `content.trustItems?.length ? … : defaults.trustItems`). Les headings ultra-spécifiques
   d'une template (craft, process, urgence…) restent des défauts non éditables — **ne pas
   prétendre le contraire dans les commentaires**. Un besoin éditable vraiment transverse →
   nouvelle clé du contrat (point 6).
4. **Pré-remplir la copie éditoriale côté API** : le module Python de la template définit
   `_EDITORIAL_DEFAULTS` (copie EXACTE des défauts du layer : badge, points, CTA, trust items,
   headings) appliqué dans `build_site_content` — ainsi le client voit **ses vrais textes**
   dans Storyblok au lieu de champs vides à fallback invisible. Si la copie du layer change,
   synchroniser ce dict.
5. Côté Storyblok, **rien à enregistrer par template** : le space n'enregistre que la famille
   de bloks partagée `site_content` (+ `theme_palette`, `page`) — schémas dans
   `api/services/templates/site_content.py` (`SITE_CONTENT_SCHEMAS`), avec **display_name et
   description en FRANÇAIS** (c'est l'UI du client — toute nouvelle clé doit avoir son libellé
   FR + un `pos`). **Ne pas ajouter de `COMPONENT_SCHEMAS` riches par template** : ils ne sont
   plus enregistrés (ils polluaient les spaces clients). ⚠️ Les schémas ne s'appliquent qu'aux
   **nouveaux** spaces (l'API ne met pas à jour les composants existants).
6. Étendre `SiteContent` (nouvelle clé transverse) = **4 endroits, additivement et optionnel** :
   le type TS (`@devleadhunter/website-content` + tag), le blok (`SITE_CONTENT_SCHEMAS` +
   `to_storyblok_site_content` + `from_storyblok_site_content` dans `site_content.py`), le
   bridge TS demo-host (`storyblokSiteContentToSiteContent.ts`), et le builder. Les deux
   bridges (TS et Python) doivent rester des **miroirs** — y compris les pièges Storyblok
   (champ single-blok renvoyé en LISTE après édition cliente, number en string).
7. **Tester le cycle complet** : générer un site → ouvrir le Visual Editor (les champs du blok
   `site_content` s'éditent et se voient en live) → **Publish** → vérifier que le webhook
   `/webhooks/storyblok` a bien mis à jour `demo_site.content_json` et que le site public
   affiche l'édition.

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
