# Standards de code & Architecture — DevLeadHunter Demo Host

> Source de vérité pour `demo-host/` — renderer Nuxt 4 des sites démo et sites vendus (`demo.dibodev.fr/{slug}` + domaines clients).
> Même niveau d'exigence que `web/`, adapté au rôle de **renderer public** et aux **Nuxt layers** (templates externes).

## Sommaire

- [Rôle dans le monorepo](#rôle-dans-le-monorepo)
- [Stack](#stack)
- [Architecture](#architecture)
- [Templates & SiteContent](#templates--sitecontent)
- [TypeScript](#typescript)
- [CSS & styling](#css--styling)
- [Commentaires & JSDoc](#commentaires--jsdoc)
- [Tracking PostHog](#tracking-posthog)
- [Conventions Vue](#conventions-vue)
- [Outillage](#outillage)
- [Règles hard](#règles-hard)

---

## Rôle dans le monorepo

`demo-host` est **déployé seul sur Vercel**. Il :

1. Résout un slug ou un domaine custom vers un `DemoSite` via l'API publique.
2. Charge le `content_json` / Storyblok (mode éditeur uniquement en iframe).
3. Dispatche `template_id` → composant racine du **Nuxt layer** correspondant (`extends` dans `nuxt.config.ts`).

Ne pas y mettre de logique dashboard, d'auth utilisateur, ni d'appels API privés.

---

## Stack

| Package     | Version |
| ----------- | ------- |
| nuxt        | 4.x     |
| vue         | 3.5.x   |
| typescript  | 5.x     |
| tailwindcss | 4.x     |

Chaque template vit dans **son propre repo GitHub** (`devleadhunter-template-<id>`), consommé comme layer. Voir `docs/TEMPLATES_ARCHITECTURE.md`.

---

## Architecture

```
demo-host/
├── app/
│   ├── components/
│   │   └── DemoSiteView.vue                  # Dispatch template_id → layer root
│   ├── composables/
│   │   ├── useDemoTracking.ts                # PostHog surface=demo
│   │   └── useDemoVideoTracking.ts
│   ├── pages/
│   │   ├── [slug].vue                        # Démo TTL
│   │   ├── index.vue                         # Site vendu (host → slug)
│   │   ├── preview-layers.vue                # Harnais DEV — layers sur SiteContents figés
│   │   └── v/[slug].vue                      # Player vidéo prospection
│   ├── types/                                # Un fichier par composant/contrat
│   └── utils/
│       ├── DemoVideoEngagementTracker.ts     # Classe — tracking du player
│       └── StoryblokSiteContentBridge.ts     # Classe — bloks Storyblok → SiteContent plat
├── eslint.config.mjs
├── prettier.config.js
├── nuxt.config.ts                            # extends: un entry par template (tag pinné)
└── STANDARDS_CODE_ET_ARCHITECTURE.md
```

Un ensemble cohérent de helpers se range dans une **classe à méthodes statiques** nommée comme son fichier (`StoryblokSiteContentBridge`), pas en fonctions module éparses. Une classe qui porte un état de session s'instancie (`new DemoVideoEngagementTracker(player, capture).start()`).

### Responsabilités

| Zone                              | Rôle                                                          |
| --------------------------------- | ------------------------------------------------------------- |
| `app/components/`                 | Glue DevLeadHunter uniquement — pas de markup de template ici |
| Layers externes                   | Tout le rendu métier template (hero, sections, footer…)       |
| `app/composables/useDemoTracking` | Events `demo_*`, session replay masqué                        |
| `preview-layers.vue`              | Outil dev local — iframe des layers avec mocks                |

---

## Templates & SiteContent

- Contrat partagé : type `SiteContent` (`@devleadhunter/website-content`).
- Le site public lit **toujours** `demo_site.content_json` synchronisé par webhook Storyblok.
- Ajouter une template = 1 repo layer + 1 ligne `extends` + 1 module Python registry + 1 entrée dans `DemoSiteView`.
- **Ne jamais** coller de JSX/React — templates en Vue 3 `<script setup>` uniquement.
- Images statiques : vérifier que chaque `src` pointe vers un fichier existant (sinon build Vercel cassé).

---

## TypeScript

Mêmes règles que `web/STANDARDS_CODE_ET_ARCHITECTURE.md` :

- `any` interdit
- `type` par défaut, `interface` seulement si étendu
- Pas de generic redondant sur `ref` / `computed`
- Types de retour explicites sur les fonctions
- Props via `defineProps({…})` runtime + type dans `app/types/` si le composant est non trivial

---

## CSS & styling

- **Tailwind v4** dans les layers et le glue local.
- `<style scoped>` toléré pour animations.
- Pas de design system dashboard (`--app-*`) — chaque template porte sa DA.
- Footer « Propulsé par DevLeadHunter » : **retiré** sur les templates livrées.

---

## Commentaires & JSDoc

- JSDoc **en anglais** sur chaque fonction et classe.
- Pas de commentaire qui paraphrase le code.
- Pas de référence à d'autres repos Léo dans les commentaires.

---

## Tracking PostHog

- Actif sur les pages démo et `/v/{slug}` — **pas** de bandeau cookies (décision produit).
- Super-prop `surface: 'demo'`, `demo_slug` sur les events.
- Events : `demo_section_view`, `demo_engaged`, `demo_outbound_click`, `demo_video_*`…
- Ne pas tracker l'éditeur Storyblok ni les routes internes de dev.

---

## Conventions Vue

- Ordre SFC : `<template>` → `<script lang="ts" setup>` → `<style scoped>` si besoin
- Composition API uniquement
- Nommage PascalCase pour les composants locaux (`DemoSiteView.vue`)
- Les composants de template suivent la convention de leur layer (pas de préfixe `Ui` imposé côté layer)
- Props via `defineProps({…})` runtime + type exporté depuis `app/types/<Composant>.ts`, JSDoc au-dessus (même profil que `web/`)

---

## Outillage

```sh
npm --prefix demo-host run lint       # prettier → eslint → vue-tsc
npm --prefix demo-host run lint:fix
```

Les trois passent avant tout commit — le hook `.husky/pre-commit` lance `web` **et** `demo-host`.

Config alignée sur `web/` : `@typescript-eslint/no-explicit-any: error`, `vue/block-order`, `jsdoc/require-jsdoc`, `unused-imports`, Prettier en règle ESLint. Les tags de type JSDoc (`require-param-type`…) sont **off partout** : le typage vient de TypeScript. `no-extraneous-class` est **off** — une classe de méthodes statiques est le style maison.

---

## Règles hard

| Règle                                      | Statut      |
| ------------------------------------------ | ----------- |
| Logique métier dashboard dans demo-host    | ❌ INTERDIT |
| Appels API authentifiés / privés           | ❌ INTERDIT |
| Code React / JSX dans les layers           | ❌ INTERDIT |
| `any`                                      | ❌ INTERDIT |
| Image statique manquante (casse build)     | ❌ INTERDIT |
| Commentaire par propriété de type          | ❌ INTERDIT |
| Commentaire de plus de 2 lignes hors JSDoc | ❌ INTERDIT |
| Commit sans `npm run lint` qui passe       | ❌ INTERDIT |
| JSDoc EN sur fonctions et méthodes         | ✅ REQUIS   |
| Rendu depuis `content_json` public         | ✅ REQUIS   |
| Dispatch centralisé via `DemoSiteView`     | ✅ REQUIS   |
