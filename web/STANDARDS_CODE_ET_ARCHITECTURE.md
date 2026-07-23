# Standards de code & Architecture — DevLeadHunter Web

> Source de vérité pour la qualité de code, l'outillage et les conventions d'architecture de `web/` (dashboard Nuxt 4 + landing + shell Tauri).
> Aligné sur le niveau d'exigence PrePeers B2B, adapté au profil DevLeadHunter (voir skill `/relecture`, `reference/profils.md`).

## Sommaire

- [Stack & versions](#stack--versions)
- [Architecture du projet](#architecture-du-projet)
- [Architecture des composants](#architecture-des-composants--réutilisabilité-dabord)
- [TypeScript — Ultra Strict](#typescript--ultra-strict)
- [CSS & styling — Tailwind](#css--styling--tailwind)
- [Commentaires & JSDoc](#commentaires--jsdoc)
- [Internationalisation (i18n)](#internationalisation-i18n)
- [Analytics — PostHog](#analytics--posthog)
- [Configuration des outils](#configuration-des-outils)
- [Conventions des composants Vue](#conventions-des-composants-vue)
- [Nommage explicite](#nommage-explicite-et-lisible)
- [Classes & services](#classes--services--utils)
- [Conventional Commits](#conventional-commits)
- [Résumé des règles hard](#résumé-des-règles-hard)

---

## Stack & versions

| Package     | Min version |
| ----------- | ----------- |
| nuxt        | 4.x         |
| vue         | 3.5.x       |
| typescript  | 5.x         |
| tailwindcss | 4.x         |
| eslint      | 9.x         |
| prettier    | 3.x         |
| husky       | 9.x         |
| vue-tsc     | 3.x         |
| pinia       | 3.x         |
| tauri       | 2.x         |

---

## Architecture du projet

Convention **Nuxt 4 avec dossier `app/`**.

```
web/
├── app/
│   ├── assets/css/main.css       # Tokens @theme + primitives UI (--app-*)
│   ├── components/
│   │   ├── ui/                   # Composants réutilisables — préfixe Ui
│   │   ├── landing/              # Sections site vitrine
│   │   ├── email-health/         # Domaine métier
│   │   └── <domaine>/            # Autres domaines thématiques
│   ├── composables/              # useXxx() — typés, sans any
│   ├── constants/                # Données constantes typées
│   ├── layouts/
│   ├── middleware/
│   ├── pages/                    # dashboard/, login, landing…
│   ├── plugins/
│   ├── services/                 # Clients HTTP — TypeScript pur, pas de réactivité Vue
│   ├── stores/                   # Pinia
│   ├── types/                    # Un fichier par composant complexe
│   └── utils/                    # Fonctions pures ou classes statiques
├── i18n/locales/                 # FR + EN (landing uniquement)
├── public/
├── src-tauri/                    # Shell desktop Tauri 2
├── nuxt.config.ts
└── STANDARDS_CODE_ET_ARCHITECTURE.md
```

### Responsabilités

| Dossier                 | Rôle                               | Contrainte                                                        |
| ----------------------- | ---------------------------------- | ----------------------------------------------------------------- |
| `components/ui/`        | UI transverse réutilisable         | Préfixe **`Ui`** obligatoire                                      |
| `components/<domaine>/` | UI liée à un domaine métier        | Pas de préfixe `Ui`                                               |
| `services/`             | Appels API, mapping                | **Aucun** `ref` / `computed`                                      |
| `utils/`                | Logique pure                       | **Sans** Vue/Nuxt ; préférer une **classe** si ≥ 2 méthodes liées |
| `types/`                | Types partagés                     | `type` par défaut ; `interface` seulement si `extends`            |
| `constants/`            | Texte structuré, options, defaults | Sortir du `.vue` tout contenu statique volumineux                 |

L'axe de rangement est **cohérent dans le repo** : `ui/` pour le transverse, sous-dossiers par **domaine** pour le métier. Ne pas mélanger les deux logiques dans le même dossier.

---

## Architecture des composants — réutilisabilité d'abord

1. **Avant de créer un composant** : balayer le repo — existe-t-il déjà ?
2. **Un composant se justifie** s'il porte une logique ou une réutilisation transverse. Pas pour un simple habillage.
3. **Construire l'API complète dès le départ** : variantes, tailles, états (disabled, loading…).
4. **Les systèmes génériques** (steppers, drawers, tabs) exposent des **slots** ; la page injecte le contenu.
5. **Toute petite gestion / formulaire = drawer** sur la pile Pinia — jamais une page dédiée pour un CRUD léger.

### Préfixe `Ui`

- Fichier : `UiProspectDrawer.vue`, `UiEmailStatusBadge.vue`
- Template : `<UiProspectDrawer />` (PascalCase)
- Types : `app/types/UiProspectDrawer.ts` → `UiProspectDrawerProps`

---

## TypeScript — Ultra Strict

### Règles

- `any` est **INTERDIT**. Utiliser `unknown` + narrowing, ou un type précis.
- **`type` par défaut** ; `interface` uniquement si le type est réellement étendu (`extends` ou declaration merging).
- Chaque `ref()` typé **sur la variable** — **pas de generic redondant** :
  - ✅ `const count: Ref<number> = ref(0)`
  - ❌ `const count: Ref<number> = ref<number>(0)`
- Chaque `computed()` via `ComputedRef<T>` sur la variable :
  - ✅ `const isReady: ComputedRef<boolean> = computed(() => …)`
- Callbacks `watch` / hooks de cycle de vie : paramètres et retour `void` typés.
- Chaque paramètre et chaque type de retour de **fonction** doit être explicite.
- Pas de `defineProps<Props>()` générique seul ; pas de `withDefaults(defineProps<…>())`.

```ts
// ✅ OK
import type { ComputedRef, Ref } from 'vue'

const pageSize: number = 50
const logs: Ref<EmailLog[]> = ref([])
const filtered: ComputedRef<EmailLog[]> = computed((): EmailLog[] => logs.value.filter(…))

async function loadLogs(): Promise<void> {
  logs.value = await getEmailLogs()
}

// ❌ INTERDIT
const logs = ref([])
const data = ref<any>(null)
function doSomething(x) {}
```

---

## CSS & styling — Tailwind

- Styling via **classes utilitaires Tailwind** (v4, bloc `@theme` dans `main.css`).
- **Pas de fichier `.css` par composant.**
- `<style scoped>` **toléré** pour animations / keyframes non expressibles en Tailwind.
- `style=""` inline uniquement pour valeurs **dynamiques** (largeur calculée, custom properties).
- Classes conditionnelles **dans le template** via `:class` — pas de computed qui retourne des chaînes sans logique de mappage.
- Classes statiques **directement dans `class=""`** — ne pas les stocker dans une variable sans raison.
- Mappage variantes/tailles : `Record<Variant, string>` dans le script quand il y a une vraie logique.

### Thèmes

- **Dashboard** : tokens `--app-*`, thème clair papier / sombre charbon (`useAppTheme`).
- **Landing** : DA light fixe (`.landing-theme`) — ne pas hériter du thème dashboard.

---

## Commentaires & JSDoc

- **JSDoc en anglais** au-dessus de chaque **fonction**, **méthode de classe** et **classe**.
- **JSDoc obligatoire sur `defineProps`** (profil devleadhunter — divergence assumée vs B2B).
- **Pas de JSDoc** sur `defineEmits`, sur un `computed` au nom explicite, ni sur un type dont le nom parle.
- **Pas de commentaire par propriété** dans un `type`.
- **Pas de paraphrase** : si le nom suffit, silence.
- Tags : `@param` (obligatoire si paramètres), `@returns` (si non-void), `@throws` si pertinent.
- **Pas de types dans le JSDoc** (`@param {number}`) — TypeScript porte le typage.

```ts
/**
 * Resolve a campaign display name from its numeric ID.
 *
 * @param id - Campaign ID as stored on EmailLog.campaign_id (may be null).
 * @returns Campaign name, or undefined when the ID is missing or unknown.
 */
function resolveCampaignName(id: string | number | null | undefined): string | undefined { … }
```

---

## Internationalisation (i18n)

- Langues : **FR** (défaut), **EN** — site vitrine et pages publiques.
- **Dashboard** : texte en dur acceptable (outil interne, N=2 users) — mais préférer la cohérence si une clé existe déjà.
- Ne jamais mettre de **HTML** dans les messages i18n.
- Clés namespacées : `landing.hero.title`, `auth.login.submit`.
- Traduire dans le template avec `$t('key')` ; `useI18n()` dans le script seulement si `$t` n'est pas disponible.

---

## Analytics — PostHog

- **Tracker le parcours prospect** : site vitrine (`surface=marketing`), démos (`surface=demo`), page vidéo.
- **Ne pas tracker le dashboard** (décision produit explicite).
- Events custom : catalogue dans `app/constants/trackingEvents.ts`, payloads typés.
- Nommage `snake_case`, stable. Un event seulement s'il apporte une donnée métier non devinable par l'autocapture.

---

## Configuration des outils

### ESLint (`eslint.config.mjs`)

- `@typescript-eslint/no-explicit-any: error`
- `vue/block-order: ['template', 'script', 'style']`
- `jsdoc/require-jsdoc: error` sur `.ts` (hors `app/utils/**` exempté)
- `unused-imports/no-unused-imports: error`
- `vue/component-name-in-template-casing: PascalCase`

### Pre-commit (racine)

```sh
npm --prefix web run lint   # prettier → eslint → vue-tsc
```

---

## Conventions des composants Vue

### Ordre des blocs SFC

1. `<template>`
2. `<script lang="ts" setup>`
3. `<style scoped>` (si nécessaire)

### Ordre interne du `<script setup>`

1. `import type { … }`
2. `import { … }`
3. `defineProps` & `defineEmits`
4. Composables
5. `ref` / `reactive`
6. `computed`
7. Fonctions (JSDoc)
8. `watch` / `watchEffect`
9. Hooks de cycle de vie

### Props — runtime `defineProps` + type exporté

```ts
// app/types/UiMyComponent.ts
export type UiMyComponentVariant = 'primary' | 'secondary'

export type UiMyComponentProps = {
  label: string
  variant?: UiMyComponentVariant
}
```

```vue
<script lang="ts" setup>
import type { PropType } from 'vue'
import type { UiMyComponentProps, UiMyComponentVariant } from '~/types/UiMyComponent'

/**
 * Defines the component props.
 */
const props: UiMyComponentProps = defineProps({
  label: { type: String, required: true },
  variant: {
    type: String as PropType<UiMyComponentVariant>,
    default: 'primary',
  },
})
</script>
```

### Emits

```ts
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated', prospect: Prospect): void
}>()
```

### Pas d'Options API

Composition API + `<script setup>` uniquement.

---

## Nommage explicite et lisible

> En lisant le nom seul, on comprend de quoi il s'agit et à quoi ça sert.

- Éviter les mots creux seuls : `Data`, `Item`, `Panel`, `Card` sans contexte.
- Booléens : `is…`, `has…`, `can…`, `should…` + sujet explicite.
- Unions : décrire l'état (`'inProgress' | 'maxReached'`), pas une couleur abstraite.

| ❌ À éviter      | ✅ Préférer                   |
| ---------------- | ----------------------------- |
| `isComplete`     | `hasSelectedMaximumProspects` |
| `count`          | `selectedProspectCount`       |
| `variant` (seul) | `displayMode`                 |

---

## Classes, services & utils

Préférer une **classe à méthodes statiques** pour un ensemble cohérent de règles ou helpers (modèle : `FieldsValidation` côté B2B).

```ts
/**
 * Email template variable substitution helpers.
 */
export class EmailVariables {
  /**
   * Replace known placeholders in a template body.
   *
   * @param body - Raw template HTML.
   * @param context - Variable values keyed by placeholder name.
   * @returns Rendered body with placeholders replaced.
   */
  static render(body: string, context: EmailVariableContext): string { … }
}
```

- Ne pas créer un fichier `utils/` pour **une seule** fonction — inliner ou fusionner.
- Les **services** (`app/services/`) encapsulent les appels HTTP ; un fichier par ressource API.

---

## Conventional Commits

```
<type>(<scope>): <description en minuscules>
```

Types : `feat` | `fix` | `ci` | `docs` | `style` | `refactor` | `test` | `chore` | `perf` | `revert` | `build`

---

## Résumé des règles hard

| Règle                                        | Statut      |
| -------------------------------------------- | ----------- |
| `any`                                        | ❌ INTERDIT |
| Generic redondant (`ref<T>(…)` doublé)       | ❌ INTERDIT |
| `interface` pour un objet non étendu         | ❌ INTERDIT |
| `defineProps<Props>()` sans defaults runtime | ❌ INTERDIT |
| `withDefaults(defineProps<…>())`             | ❌ INTERDIT |
| `<script>` avant `<template>`                | ❌ INTERDIT |
| Options API                                  | ❌ INTERDIT |
| Styles inline non dynamiques                 | ❌ INTERDIT |
| Paramètre / retour non typés (fonctions)     | ❌ INTERDIT |
| `ref()` / `computed()` non typés             | ❌ INTERDIT |
| Commit sans lint qui passe                   | ❌ INTERDIT |
| HTML dans messages i18n                      | ❌ INTERDIT |
| JSDoc EN sur chaque fonction                 | ✅ REQUIS   |
| JSDoc sur `defineProps`                      | ✅ REQUIS   |
| Type props dans `app/types/<Component>.ts`   | ✅ REQUIS   |
| Préfixe `Ui` sur composants réutilisables    | ✅ REQUIS   |
| Tailwind pour le styling                     | ✅ REQUIS   |
| Ordre SFC template → script → style          | ✅ REQUIS   |
| Conventional commits                         | ✅ REQUIS   |
