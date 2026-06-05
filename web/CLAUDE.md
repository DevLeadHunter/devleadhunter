# 🧹 Standards de code & Architecture — DevLeadHunter (Web / Nuxt)

> Ce document est la **source de vérité** pour la qualité de code, l'outillage et les conventions d'architecture de la partie frontend.
> Toute modification du projet doit respecter ces règles.

## Sommaire

- [Stack & versions](#-stack--versions)
- [Architecture du projet](#️-architecture-du-projet)
- [TypeScript — Ultra Strict](#-typescript--ultra-strict)
- [CSS & Styling (Tailwind)](#-css--styling-tailwind)
- [Commentaires & JSDoc](#-commentaires--jsdoc)
- [Conventions des composants Vue](#-conventions-des-composants-vue)
- [Conventional Commits](#-conventional-commits)
- [Résumé des règles "hard"](#-résumé-des-règles-hard)

---

## 📦 Stack & versions

| Package     | Version min |
| ----------- | ----------- |
| nuxt        | 4.x         |
| vue         | 3.5.x       |
| typescript  | 5.x         |
| tailwindcss | 3.x         |
| eslint      | 9.x         |
| prettier    | 3.x         |
| husky       | 9.x         |
| vue-tsc     | 3.x         |

---

## 🏗️ Architecture du projet

Le projet suit la convention **Nuxt 4 avec le dossier `app/`**.

```
web/
├── app/
│   ├── assets/
│   │   └── css/main.css              # CSS global / variables Tailwind
│   ├── components/
│   │   ├── ui/                       # Composants UI réutilisables (préfixe Ui)
│   │   └── <domaine>/                # Composants métier par domaine
│   ├── composables/                  # useXxx() composables — toujours typés
│   ├── layouts/                      # Nuxt layouts
│   ├── pages/                        # Nuxt file-based routing
│   ├── plugins/                      # Nuxt plugins (client/server)
│   ├── services/                     # Clients HTTP vers l'API FastAPI
│   ├── stores/                       # Stores Pinia
│   ├── types/                        # Interfaces & types TypeScript partagés
│   │   └── <ComponentName>.ts        # Un fichier par composant ayant des props complexes
│   └── utils/                        # Fonctions utilitaires pures (sans Vue/Nuxt)
├── public/
├── nuxt.config.ts
├── tailwind.config.js
├── tsconfig.json
└── CLAUDE.md                         # Ce fichier
```

### Responsabilités

- `app/components/ui/` — composants réutilisables, préfixe **`Ui`** (`UiProspectDrawer`, `UiEmailStatusBadge`…)
- `app/types/<ComponentName>.ts` — interface de props exportée pour chaque composant qui en a besoin
- `app/utils/` — fonctions pures sans dépendance Vue/Nuxt (ex: `utils/date.ts`)
- `app/services/` — un fichier par ressource API (`prospectsService.ts`, `campaignService.ts`…)

---

## 🔷 TypeScript — Ultra Strict

### Règles absolues

- `any` est **INTERDIT**. Utiliser `unknown` + narrowing, ou définir un type précis.
- Chaque `ref()` doit être **explicitement typé** sur la variable et le générique :
  ```ts
  const count: Ref<number> = ref<number>(0)
  const prospects: Ref<Prospect[]> = ref<Prospect[]>([])
  ```
- Chaque `computed()` doit être typé via `ComputedRef<T>` :
  ```ts
  const isReady: ComputedRef<boolean> = computed((): boolean => prospects.value.length > 0)
  ```
- Les callbacks de `watch` et hooks de cycle de vie doivent typer leurs paramètres :
  ```ts
  watch(isOpen, (open: boolean): void => { … })
  onMounted((): void => { … })
  ```
- Chaque paramètre de fonction et chaque type de retour doit être explicite :
  ```ts
  function fetchData(id: number): Promise<Prospect> { … }
  ```
- Utiliser `interface` pour les objets extensibles, `type` pour les unions et primitives.
- `T | null` et `T | undefined` préférés à `Optional<T>` (style Python — on reste TypeScript ici).

### Exemples

```ts
// ✅ OK
import type { ComputedRef, Ref } from 'vue'

const pageSize: number = 50
const logs: Ref<EmailLog[]> = ref<EmailLog[]>([])
const filteredLogs: ComputedRef<EmailLog[]> = computed((): EmailLog[] => logs.value.filter(…))

async function loadLogs(): Promise<void> {
  logs.value = await getEmailLogs()
}

// ❌ INTERDIT
const logs = ref([])               // inférence implicite
const data = ref<any>(null)        // any interdit
function doSomething(x) {}         // paramètre non typé
```

---

## 🎨 CSS & Styling (Tailwind)

- Le projet utilise **Tailwind CSS** exclusivement. Pas de fichiers `.css` par composant.
- Le CSS global vit dans `app/assets/css/main.css`.
- Les styles inline (`style=""`) sont autorisés uniquement pour les **valeurs vraiment dynamiques** (ex: largeur calculée en JS).
- Les classes Tailwind arbitraires (`bg-[#1a1a1a]`) sont acceptées pour respecter la charte graphique sombre du projet.
- Les blocs `<style scoped>` sont réservés aux **animations CSS** et transitions qui ne peuvent pas être exprimées en Tailwind.

---

## 💬 Commentaires & JSDoc

- **JSDoc en anglais** au-dessus de chaque fonction, composable, service et computed.
- Les **commentaires inline** peuvent être en français si c'est plus clair pour expliquer un comportement métier.
- Le JSDoc doit inclure `@param`, `@returns`, et `@throws` si pertinent.

```ts
/**
 * Resolve a campaign display name from its numeric ID.
 *
 * @param id - Campaign ID as stored on ``EmailLog.campaign_id`` (may be null).
 * @returns Campaign name, or ``undefined`` when the ID is missing or unknown.
 */
function resolveCampaignName(id: string | number | null | undefined): string | undefined {
  if (id == null) return undefined
  const numericId: number = Number(id)
  if (Number.isNaN(numericId)) return undefined
  return campaigns.value.find((c: CampaignResponse): boolean => c.id === numericId)?.name
}
```

---

## 🧱 Conventions des composants Vue

### Ordre des blocs d'un SFC

**Toujours dans cet ordre :**

1. `<template>` en premier
2. `<script lang="ts" setup>` après `</template>`
3. `<style scoped>` en dernier (uniquement si nécessaire)

```vue
<!-- ✅ OK -->
<template>…</template>
<script lang="ts" setup>
…
</script>
<style scoped>
…
</style>

<!-- ❌ INTERDIT -->
<script lang="ts" setup>
…
</script>
<template>…</template>
```

### Ordre interne du `<script setup>`

1. `import type { … }` (types d'abord)
2. `import { … }` (valeurs ensuite)
3. `defineProps` & `defineEmits`
4. Composables (`useRoute()`, `useToast()`…)
5. `ref<T>()` et état réactif
6. `ComputedRef<T>` — computed
7. Fonctions/méthodes (chacune précédée d'un JSDoc)
8. `watch` / `watchEffect`
9. Hooks de cycle de vie (`onMounted`, `onBeforeUnmount`…)

### Props — `defineProps({…})` runtime + interface exportée

**Pattern obligatoire :**

1. Créer `app/types/<ComponentName>.ts` avec l'interface exportée
2. Utiliser `defineProps({…})` runtime avec `as PropType<…>` pour les unions

```ts
// app/types/UiMyComponent.ts
export interface UiMyComponentProps {
  label: string
  variant?: 'primary' | 'secondary'
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
  label: {
    type: String,
    required: true,
  },
  variant: {
    type: String as PropType<UiMyComponentVariant>,
    default: 'primary',
  },
})
</script>
```

**Règles :**

- `defineProps<Props>()` générique seul → **INTERDIT**
- `withDefaults(defineProps<Props>(), {…})` → **INTERDIT**
- Chaque prop optionnelle **doit** avoir un `default`
- Chaque prop requise **doit** avoir `required: true`
- Un bloc JSDoc **doit** précéder `defineProps`

### Emits

```ts
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated', prospect: Prospect): void
}>()
```

### Nommage des composants

- Fichier : **PascalCase** → `UiProspectDrawer.vue`, `UiEmailStatusBadge.vue`
- Usage template : **PascalCase** → `<UiProspectDrawer />`
- Composants UI réutilisables : préfixe **`Ui`**
- Composants de page/domaine : pas de préfixe obligatoire

### Pas d'Options API

Uniquement **Composition API avec `<script setup>`**. L'Options API est interdite.

---

## 📝 Conventional Commits

```
<type>(<scope>): <description en minuscules>

Types : feat | fix | ci | docs | style | refactor | test | chore | perf | revert | build
```

Le sujet doit être en **minuscules** (commitlint l'impose).

```
feat(campaigns): add cold email queue with rate limiting
fix(drawer): remove duplicate defineProps call in EmailLogDrawer
chore(deps): upgrade nuxt to latest stable version
```

---

## 🚫 Résumé des règles "hard"

| Règle                                                   | Statut      |
| ------------------------------------------------------- | ----------- |
| Type `any`                                              | ❌ INTERDIT |
| `defineProps<Props>()` générique sans defaults runtime  | ❌ INTERDIT |
| `withDefaults(defineProps<…>())`                        | ❌ INTERDIT |
| `<script>` avant `<template>`                           | ❌ INTERDIT |
| Options API                                             | ❌ INTERDIT |
| Styles inline non-dynamiques                            | ❌ INTERDIT |
| Paramètre de fonction non typé                          | ❌ INTERDIT |
| Type de retour de fonction absent                       | ❌ INTERDIT |
| `ref()` / `computed()` non typés                        | ❌ INTERDIT |
| Commit sans lint qui passe                              | ❌ INTERDIT |
| Tailwind CSS pour le styling                            | ✅ REQUIS   |
| JSDoc en anglais au-dessus de chaque fonction           | ✅ REQUIS   |
| Interface de props dans `app/types/<ComponentName>.ts`  | ✅ REQUIS   |
| `ComputedRef<T>` sur la variable pour chaque computed   | ✅ REQUIS   |
| `Ref<T>` sur la variable pour chaque ref                | ✅ REQUIS   |
| Ordre des blocs : `<template>` → `<script>` → `<style>` | ✅ REQUIS   |
| Conventional commits                                    | ✅ REQUIS   |
