# 🧹 Standards de code & Architecture — PrePeers B2C

> Ce document est la **source de vérité** pour la qualité de code, l'outillage, et les conventions d'architecture.
> Toute modification du projet doit respecter ces règles.
>
> Ces règles permettent de **coder plus simplement** grâce à des suggestions et une autocomplétion IDE **beaucoup plus performantes** (typage strict, conventions homogènes, structure claire). Elles garantissent aussi un projet **viable sur le long terme**, facilement **maintenable** et évolutif, pour éviter qu'il ne devienne "jetable" au bout d'un certain temps.

## Sommaire

- [Stack & versions](#-stack--versions)
- [Architecture du projet](#️-architecture-du-projet)
- [TypeScript — Ultra Strict](#-typescript--ultra-strict)
- [CSS & styling](#-css--styling)
- [Commentaires & JSDoc](#-commentaires--jsdoc)
- [Internationalisation (i18n)](#-internationalisation-i18n)
- [SEO](#-seo)
- [Configuration des outils](#-configuration-des-outils)
- [Conventions des composants Vue](#-conventions-des-composants-vue)
- [Conventional Commits](#-conventional-commits)
- [Résumé des règles "hard"](#-résumé-des-règles-hard)

---

## 📦 Stack & versions

Toujours installer la **dernière version stable** de chaque package. Avant d'installer, vérifier :

- Nuxt → [https://nuxt.com](https://nuxt.com)
- Vue → [https://vuejs.org](https://vuejs.org)
- TypeScript → [https://www.typescriptlang.org](https://www.typescriptlang.org)
- @nuxtjs/i18n → [https://i18n.nuxtjs.org](https://i18n.nuxtjs.org)
- @nuxtjs/sitemap → [https://nuxtseo.com/sitemap](https://nuxtseo.com/sitemap)
- @nuxtjs/robots → [https://nuxtseo.com/robots](https://nuxtseo.com/robots)
- ESLint → [https://eslint.org](https://eslint.org)
- Prettier → [https://prettier.io](https://prettier.io)
- Husky → [https://typicode.github.io/husky](https://typicode.github.io/husky)
- commitlint → [https://commitlint.js.org](https://commitlint.js.org)
- vue-tsc → [https://github.com/vuejs/language-tools](https://github.com/vuejs/language-tools)

**Versions minimales (tout en gardant l'objectif d'installer la dernière stable) :**

| Package      | Min version |
| ------------ | ----------- |
| nuxt         | 4.x         |
| vue          | 3.5.x       |
| typescript   | 5.x         |
| @nuxtjs/i18n | 10.x        |
| eslint       | 9.x         |
| prettier     | 3.x         |
| husky        | 9.x         |
| vue-tsc      | 3.x         |

---

## 🏗️ Architecture du projet

Le projet suit la convention **Nuxt 4 avec le dossier `app/`**. Le code applicatif vit dans `app/`.

```
prepeers-front-b2c/
├── app/
│   ├── assets/
│   │   └── prepeers-design-system.css   # CSS global / design system
│   ├── components/
│   │   ├── ui/                   # Composants UI réutilisables (cards, accordion, etc.)
│   │   ├── home/                 # Sections/Composants de la home
│   │   ├── blog/                 # Blog (article, catégories, etc.)
│   │   ├── chat/                 # UI chat (panels, input, etc.)
│   │   ├── moi/                  # Espace "moi" / onboarding / profil utilisateur
│   │   ├── aca/                  # Écoles / programmes / campus
│   │   ├── search/               # Recherche (schools/programs)
│   │   ├── profil/               # Profil (progress, etc.)
│   │   ├── AppHeader.vue
│   │   └── AppFooter.vue
│   ├── composables/              # useXxx() composables — typed, no any
│   ├── layouts/                  # Nuxt layouts
│   ├── pages/                    # Nuxt file-based routing
│   ├── plugins/                  # Nuxt plugins (client/server)
│   ├── types/                    # Shared TypeScript interfaces & types
│   └── utils/                    # Pure utility functions (no Vue, no Nuxt)
├── i18n/                         # (prévu) ressources i18n, même si pas encore en place
│   └── locales/                  # ex: fr.json / en.json / es.json
├── public/                       # Static assets
├── .husky/
│   └── pre-commit
├── .env.example
├── .gitignore
├── .prettierignore
├── commitlint.json
├── eslint.config.mjs
├── nuxt.config.ts
├── package.json
├── prettier.config.js
└── tsconfig.json
```

### Responsabilités des dossiers

- `**app/components/**`: composants Vue, rangés par domaine/écran. Les composants "purs UI" vont dans `ui/`.
- `**app/composables/**`: logique réutilisable (Composition API), toujours typée.
- `**app/types/**`: types et interfaces partagés (à garder).
- `**app/utils/**`: fonctions utilitaires pures (sans dépendre de Vue/Nuxt).
- `**i18n/**`: dossier à conserver dans l'architecture même si le contenu n'est pas encore finalisé (à garder).

---

## 🔷 TypeScript — Ultra Strict

### Règles

- `any` est **INTERDIT**. Utiliser `unknown` puis "narrow", ou définir un type correctement.
- Chaque `const` contenant un primitif ou un object literal doit être **explicitement typé** (ne pas compter sur l'inférence pour les "constantes") : `const pageSize: number = 20`
- Chaque `ref()` doit être explicitement typé **sur la variable** et **sur le generic** :
  - `const count: Ref<number> = ref<number>(0)`
- Chaque `computed()` doit être typé sur la variable via `ComputedRef<T>` importé depuis `vue` :
  - `const isReady: ComputedRef<boolean> = computed(() => …)`
  - Ne pas utiliser `computed<T>(() => …)` comme unique mécanisme : la variable doit être un `ComputedRef<T>`.
- Les callbacks de `watch` / `watchEffect` doivent typer leurs paramètres et retourner `void` si applicable :
  - `watch(isOpen, (open: boolean): void => { … })`
- Les hooks de cycle de vie Vue doivent typer leurs callbacks :
  - `onMounted((): void => { … })`
  - `onBeforeUnmount((): void => { … })`
- Chaque paramètre de fonction doit être typé : `function foo(id: number, name: string): void`
- Chaque type de retour de fonction doit être explicite
- Chaque variable réactive, prop, emit et inject doit être typé
- Utiliser `interface` pour les objets extensibles, `type` pour les unions et primitives
- Aucun `any` implicite (si TS infère `any`, on ajoute le type)

### tsconfig.json

```json
{
  "files": [],
  "references": [
    { "path": "./.nuxt/tsconfig.app.json" },
    { "path": "./.nuxt/tsconfig.server.json" },
    { "path": "./.nuxt/tsconfig.shared.json" },
    { "path": "./.nuxt/tsconfig.node.json" }
  ]
}
```

> Nuxt 4 gère le mode strict via `.nuxt/tsconfig.app.json` (avec `"strict": true`).
> Ne pas l'override : l'étendre si besoin dans `nuxt.config.ts` via `typescript.tsConfig`.
> Lancer `npm run lint:ts` (vue-tsc --noEmit) pour valider les types avant de commit.

### Exemples

```ts
// ✅ OK
import type { ComputedRef, Ref } from 'vue'

const pageSize: number = 20
const count: Ref<number> = ref(0)
const schools: Ref<School[]> = ref([])
const isLoading: ComputedRef<boolean> = computed(() => schools.value.length === 0)

function fetchSchool(id: number): Promise<School> {
  return schoolService.getById(id)
}

// ❌ INTERDIT
const count = ref(0) // inférence implicite — ajouter un type explicite
const data = ref<any>(null) // `any` est interdit
function doSomething(x) {} // paramètre non typé
```

---

## 🎨 CSS & styling

- Le projet **n'utilise pas TailwindCSS**.
- Le styling se fait :
  - soit via des **fichiers `.css`** (ex: `app/assets/prepeers-design-system.css`)
  - soit via des **blocs `<style scoped>`** dans les composants Vue quand c'est pertinent
- Éviter les styles inline (`style=""`) sauf cas exceptionnel (valeurs réellement dynamiques).

### Convention de nommage des classes (recommandé)

Utiliser un pattern proche BEM :

- **Bloc**: `author-badge`
- **Élément**: `author-badge__avatar`
- **Modifier**: `author-badge--compact`

```vue
<template>
  <div class="author-badge author-badge--compact">
    <img
      class="author-badge__avatar"
      :src="avatarUrl"
      alt="" />
    <span class="author-badge__name">{{ name }}</span>
  </div>
</template>

<style scoped>
.author-badge {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}
</style>
```

---

## 💬 Commentaires & JSDoc

- Les commentaires en **français sont autorisés**.
- Au-dessus de chaque fonction/méthode (composables, utils, etc.), ajouter un **bloc JSDoc**.
- Le JSDoc doit inclure `@param`, `@returns`, et `@throws` si pertinent.
- Les commentaires inline sont autorisés si ils apportent une vraie valeur (intention, contrainte, edge case).

```ts
import type { ComputedRef } from 'vue'

/**
 * Récupère une école via son identifiant unique.
 * @param id - Identifiant unique de l'école.
 * @returns Une promesse résolue avec les données de l'école.
 * @throws Lance une erreur si la requête réseau échoue.
 */
async function fetchSchoolById(id: number): Promise<School> {
  return await schoolService.getById(id)
}

/**
 * Indique si l'utilisateur a terminé l'onboarding.
 * @returns `true` si l'onboarding est terminé, sinon `false`.
 */
const hasCompletedOnboarding: ComputedRef<boolean> = computed(() => {
  // Vérifie le profil et les préférences pour déterminer la complétion
  return user.value?.profile !== null && user.value?.preferences !== null
})
```

---

## 🌍 Internationalisation (i18n)

- Utiliser la dernière version de `@nuxtjs/i18n`
- Langues supportées : **FR** (défaut), **EN**, **ES**
- Fichiers de traductions : `i18n/locales/fr.json`, `en.json`, `es.json`
- Stratégie : `prefix_except_default` (FR sans préfixe, EN → `/en/`, ES → `/es/`)
- **Ne jamais hardcoder de texte utilisateur** : utiliser `$t('key')` ou `useI18n().t('key')`
- **Préférer `$t('key')` dans les templates** plutôt que `const { t } = useI18n()` si le script n'en a pas besoin.
  - Garder `useI18n()` dans le script uniquement quand nécessaire (computed, validateurs, `useHead`, etc.).
- Les clés doivent être **namespacées** par section : `hero.title`, `features.cta`, `pricing.perMonth`

```vue
<!-- ✅ OK -->
<h1>{{ $t('hero.title') }}</h1>

<!-- ❌ INTERDIT -->
<h1>Trouvez vos futurs étudiants</h1>
```

---

## 🔍 SEO

- Utiliser `@nuxtjs/sitemap` et `@nuxtjs/robots`
- Utiliser `useHead()` ou `useSeoMeta()` dans chaque page pour définir les metas
- Chaque page doit définir : `title`, `description`, `og:title`, `og:description`, `og:image`
- Le sitemap et robots doivent exclure les routes privées/admin si elles existent
- Le SSR doit rester activé (`ssr: true` dans `nuxt.config.ts`)

---

## 🔧 Configuration des outils

### ESLint — `eslint.config.mjs`

Doit inclure (selon les besoins du projet) :

- `@typescript-eslint` (strict)
- `eslint-plugin-vue`
- `eslint-plugin-jsdoc` (forcer JSDoc au-dessus des fonctions)
- `eslint-plugin-unused-imports` (interdire imports/variables inutilisés)
- `eslint-plugin-prettier` (exécuter Prettier comme règle ESLint)
- `eslint-config-prettier` (désactiver les règles en conflit avec Prettier)
- Règle : `@typescript-eslint/no-explicit-any: error` (`any` est une erreur)
- Règle : `@typescript-eslint/explicit-function-return-type: error`
- Règle : `@typescript-eslint/no-unused-vars: error`
- Règle : `vue/component-name-in-template-casing: ['error', 'PascalCase']`

### Prettier — `prettier.config.js`

```js
export default {
  semi: false,
  singleQuote: true,
  trailingComma: 'all',
  printWidth: 120,
  tabWidth: 2,
}
```

### commitlint — `commitlint.json`

```json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "ci", "docs", "style", "refactor", "test", "chore", "perf", "revert", "build"]
    ]
  }
}
```

### Husky pre-commit — `.husky/pre-commit`

```sh
npm run lint
```

Le script `lint` doit s'exécuter séquentiellement :

1. `prettier --check .`
2. `eslint .`
3. `vue-tsc --noEmit`

Les trois doivent passer avant d'autoriser un commit.

### Scripts `package.json`

```json
{
  "scripts": {
    "dev": "nuxt dev",
    "build": "nuxt build",
    "generate": "nuxt generate",
    "preview": "nuxt preview",
    "postinstall": "nuxt prepare",
    "lint:prettier": "prettier --check .",
    "lint:prettier:fix": "prettier --write .",
    "lint:eslint": "eslint .",
    "lint:eslint:fix": "eslint . --fix",
    "lint:ts": "vue-tsc --noEmit",
    "lint": "npm run lint:prettier && npm run lint:eslint && npm run lint:ts",
    "lint:fix": "npm run lint:prettier:fix && npm run lint:eslint:fix"
  }
}
```

---

## 🧱 Conventions des composants Vue

### Ordre des blocs d'un SFC (Single-File Component)

Chaque fichier `.vue` **doit** déclarer ses blocs dans l'ordre suivant :

1. `<template>` en **premier**
2. `<script lang="ts" setup>` juste après `</template>`
3. `<style scoped>` (optionnel) en dernier, si nécessaire

```vue
<!-- ✅ OK -->
<template>
  <button :class="baseClass">{{ props.label }}</button>
</template>

<script lang="ts" setup>
import type { PrePeersButtonProps } from '~/types/PrePeersButton'

/**
 * Définit les props du composant.
 */
const props: PrePeersButtonProps = defineProps({
  label: { type: String, required: true },
})
</script>
```

```vue
<!-- ❌ INTERDIT — script avant template -->
<script lang="ts" setup>
// ...
</script>

<template>
  <!-- ... -->
</template>
```

Le tag d'ouverture `<script>` **doit** utiliser `lang="ts" setup` dans cet ordre exact.

### Ordre interne du `<script setup>`

Dans `<script lang="ts" setup>`, suivre cet ordre :

1. imports (types en premier via `import type { … }`)
2. props (`defineProps`) & emits (`defineEmits`)
3. composables (`useI18n()`, `useRoute()`, composables internes…)
4. refs & état réactif (`ref<T>(…)`, `reactive<T>(…)`)
5. computed (`const x: ComputedRef<T> = computed(() => …)`)
6. méthodes/fonctions (chacune précédée d'un bloc JSDoc — français autorisé et recommandé)
7. watchers (`watch`, `watchEffect`) — callbacks entièrement typés
8. hooks de cycle de vie (`onMounted`, `onBeforeUnmount`…) — callbacks entièrement typés

**Règles de lisibilité / regroupement :**

- Regrouper les déclarations liées (tous les refs ensemble, tous les computed ensemble, toutes les fonctions ensemble).
- Éviter de dupliquer les hooks quand un seul hook peut gérer proprement le teardown (fusionner les `onBeforeUnmount`).

### Nommage des composants

- Nom de fichier : **PascalCase** → `PrePeersHeroSection.vue`, `PrePeersButton.vue`
- Utilisation dans le template : **PascalCase** → `<PrePeersHeroSection />`, `<PrePeersButton />`

### Nommage des composants (préfixe PrePeers)

- Le préfixe `PrePeers` **n'est pas obligatoire**, mais il est **recommandé** (cohérence et réduction des collisions).
- Chaque composant vit **directement** dans son dossier de catégorie (pas de sous-dossier par composant) :
  - `app/components/ui/` → UI atoms (button, input, badge…)
  - `app/components/home/` → home
  - `app/components/blog/` → blog
  - `app/components/chat/` → chat
  - `app/components/moi/` → "moi"
  - `app/components/aca/` → écoles / programmes / campus
  - `app/components/search/` → recherche
  - `app/components/profil/` → profil
- Le préfixe de chemin d'auto-import est désactivé (`pathPrefix: false` dans `nuxt.config.ts`) : un composant est donc référencé par son nom de fichier. Le préfixe `PrePeers` peut aider à éviter des collisions.

### Props — typées via `defineProps({…})` runtime + interface importée

Chaque composant déclare ses props via **l'API runtime** de `defineProps`, couplée à une `**interface` dédiée exportée depuis `app/types/`\*\*. Ce pattern est requis car il impose des `default` explicites, la validation runtime Vue, et un type partagé unique par composant.

**1) Déclarer l'interface de props dans `app/types/<ComponentName>.ts`** (un fichier par composant, nommé comme le composant) :

```ts
// app/types/PrePeersButton.ts

/**
 * Variante visuelle du composant PrePeersButton.
 */
export type PrePeersButtonVariant = 'dark' | 'outline' | 'ghost'

/**
 * Taille du composant PrePeersButton.
 */
export type PrePeersButtonSize = 'sm' | 'md'

/**
 * Props du composant PrePeersButton.
 */
export interface PrePeersButtonProps {
  label: string
  to?: string
  variant?: PrePeersButtonVariant
  size?: PrePeersButtonSize
}
```

**2) Utiliser le runtime `defineProps({…})` et appliquer le type sur la variable retournée :**

```vue
<script lang="ts" setup>
import type { PropType } from 'vue'
import type {
  PrePeersButtonProps,
  PrePeersButtonSize,
  PrePeersButtonVariant,
} from '~/types/PrePeersButton'

/**
 * Définit les props du composant PrePeersButton.
 */
const props: PrePeersButtonProps = defineProps({
  label: {
    type: String,
    required: true,
  },
  to: {
    type: String,
    default: undefined,
  },
  variant: {
    type: String as PropType<PrePeersButtonVariant>,
    default: 'outline',
  },
  size: {
    type: String as PropType<PrePeersButtonSize>,
    default: 'md',
  },
})
</script>
```

Règles :

- L'`interface` vit dans `app/types/<ComponentName>.ts` et doit être `export`ée.
- Le nom de l'interface suit le pattern `<ComponentName>Props`.
- Utiliser `as PropType<…>` pour les props union / string-literal / objet afin que Vue conserve le type précis au runtime.
- Chaque prop optionnelle **doit** définir un `default` (utiliser `default: undefined` pour les optionnelles "nullables").
- Chaque prop requise **doit** définir `required: true`.
- Un bloc JSDoc (français autorisé et recommandé) **doit** précéder l'appel à `defineProps`.
- `**withDefaults(defineProps<…>())` est INTERDIT\*\*. Les defaults doivent vivre dans l'objet runtime `defineProps({ … })` (voir l'exemple ci-dessus).

```ts
// ❌ INTERDIT — defineProps générique uniquement, sans validation/defaults runtime
const props = defineProps<Props>()

// ❌ INTERDIT — interface inline, type importé manquant
const props = defineProps({ label: { type: String, required: true } })

// ❌ INTERDIT — withDefaults + props génériques
const props = withDefaults(defineProps<Props>(), { variant: 'blue' })
```

### Emits — toujours typés via `defineEmits<{}>()`

```ts
const emit = defineEmits<{
  (e: 'submit', value: string): void
  (e: 'close'): void
}>()
```

### Pas d'Options API

Utiliser uniquement la **Composition API avec `<script setup>`**. L'Options API est interdite.

---

## 📝 Conventional Commits (messages de commit)

Chaque commit doit respecter la spécification Conventional Commits :

```
<type>(<scope>): <short description>

Types : feat | fix | ci | docs | style | refactor | test | chore | perf | revert | build
```

Exemples :

```
feat(landing): add hero section with i18n support
fix(seo): correct og:image meta tag on landing page
chore(deps): upgrade nuxt to latest stable version
refactor(composables): extract useSchools logic into a dedicated composable
```

---

## 🚫 Résumé des règles "hard"

| Règle                                                                                            | Statut      |
| ------------------------------------------------------------------------------------------------ | ----------- |
| Type `any`                                                                                       | ❌ INTERDIT |
| CSS via fichiers `.css` ou `<style scoped>`                                                      | ✅ REQUIS   |
| Textes "user-facing" hardcodés                                                                   | ❌ INTERDIT |
| Options API                                                                                      | ❌ INTERDIT |
| Commentaires en français                                                                         | ✅ AUTORISÉ |
| Refs/computed/props non typés                                                                    | ❌ INTERDIT |
| `withDefaults(defineProps<…>())`                                                                 | ❌ INTERDIT |
| Styles inline (non dynamiques)                                                                   | ❌ INTERDIT |
| Commit sans lint qui passe                                                                       | ❌ INTERDIT |
| `<script>` placé avant `<template>` dans un `.vue`                                               | ❌ INTERDIT |
| `defineProps<Props>()` générique uniquement (sans defaults runtime)                              | ❌ INTERDIT |
| JSDoc au-dessus de chaque fonction                                                               | ✅ REQUIS   |
| Types de retour explicites                                                                       | ✅ REQUIS   |
| Conventional commits                                                                             | ✅ REQUIS   |
| Ordre des blocs : `<template>` puis `<script lang="ts" setup>` (puis `<style scoped>` si besoin) | ✅ REQUIS   |
| Interface de props exportée depuis `app/types/<ComponentName>.ts`                                | ✅ REQUIS   |
