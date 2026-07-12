<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- Header -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-search" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Trouver des prospects</h2>
            <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">Métier + ville → artisans qui correspondent</p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <form id="search-prospects-form" class="space-y-4" @submit.prevent="submit">
            <div>
              <label for="sp-category" class="app-label mb-1.5 block">
                Métier recherché <span class="text-[var(--app-accent)]">*</span>
              </label>
              <div class="relative">
                <UIcon
                  name="i-lucide-hammer"
                  class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
                />
                <input
                  id="sp-category"
                  v-model="form.category"
                  type="text"
                  placeholder="Plombier, électricien…"
                  required
                  class="app-input w-full pl-9"
                />
              </div>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <button
                  v-for="quick in QUICK_CATEGORIES"
                  :key="quick"
                  type="button"
                  class="cursor-pointer rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-1 text-xs text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
                  @click="form.category = quick"
                >
                  {{ quick }}
                </button>
              </div>
            </div>

            <div>
              <label for="sp-city" class="app-label mb-1.5 block">
                Ville <span class="text-[var(--app-accent)]">*</span>
              </label>
              <UiCityAutocompleteInput v-model="form.city" input-id="sp-city" required show-icon />
            </div>

            <div>
              <label for="sp-max" class="app-label mb-1.5 block">Nombre maximum de résultats</label>
              <input
                id="sp-max"
                v-model.number="form.maxResults"
                type="number"
                min="1"
                max="100"
                required
                class="app-input w-full"
              />
            </div>

            <div>
              <label for="sp-source" class="app-label mb-1.5 block">Source</label>
              <select id="sp-source" v-model="form.source" class="app-input w-full">
                <option
                  v-for="option in PROSPECT_SOURCE_SEARCH_OPTIONS"
                  :key="option.value || 'all'"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="space-y-3 border-t border-[var(--app-line-soft)] pt-4">
              <UiCheckbox
                id="sp-only-without-website"
                v-model="form.onlyWithoutWebsite"
                label="Uniquement les prospects sans site web (recommandé)"
              />
              <UiCheckbox
                id="sp-skip-duplicates"
                v-model="form.skipDuplicates"
                label="Ignorer les prospects déjà enregistrés (recommandé)"
              />
            </div>
          </form>

          <!-- Live status (compact) -->
          <div v-if="store.currentJob" class="rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5">
            <div class="mb-1.5 flex items-center justify-between text-xs">
              <span class="font-medium text-[var(--app-ink)]">
                {{ store.currentJob.status === 'completed' ? 'Recherche terminée' : 'Recherche en cours…' }}
              </span>
              <span class="text-[var(--app-ink-soft)] tabular-nums">
                {{ store.liveProgress.current }} / {{ store.liveProgress.total || store.currentJob.max_results }}
              </span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]">
              <div
                class="h-full rounded-full bg-[var(--app-ink)] transition-all"
                :style="{ width: Math.min(store.liveProgress.percentage, 100) + '%' }"
              />
            </div>
            <p v-if="store.liveProgress.current_prospect" class="mt-2 truncate text-[11px] text-[var(--app-ink-soft)]">
              {{ store.liveProgress.current_prospect }}
            </p>
            <NuxtLink
              v-if="store.currentJob.status === 'completed'"
              to="/dashboard/my-prospects"
              class="mt-2.5 inline-flex items-center gap-1 text-[11px] font-medium text-[var(--app-ink)] hover:underline"
              @click="emit('close')"
            >
              Voir mes prospects <UIcon name="i-lucide-arrow-right" class="h-3 w-3" />
            </NuxtLink>
          </div>

          <!-- Comment ça marche (below the form) -->
          <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-4">
            <p class="app-label mb-3">Comment ça marche</p>
            <ol class="space-y-2.5">
              <li v-for="(text, index) in SEARCH_STEPS" :key="text" class="flex items-start gap-2.5">
                <span
                  class="font-label flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[0.6rem] font-semibold text-[var(--app-ink)]"
                >
                  {{ index + 1 }}
                </span>
                <p class="text-[11px] leading-relaxed text-[var(--app-ink-soft)]">{{ text }}</p>
              </li>
            </ol>
            <p
              class="mt-3 flex items-center gap-2 border-t border-[var(--app-line-soft)] pt-3 text-[11px] text-[var(--app-ink-soft)]"
            >
              <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]" />
              Chaque prospect trouvé consomme des crédits selon vos paramètres.
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="app-btn-secondary flex-1" @click="emit('close')">Fermer</button>
          <button
            type="submit"
            form="search-prospects-form"
            class="app-btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="store.isStarting || store.isSearching"
          >
            <UIcon
              :name="store.isStarting || store.isSearching ? 'i-lucide-loader-circle' : 'i-lucide-search'"
              :class="['h-4 w-4', (store.isStarting || store.isSearching) && 'animate-spin']"
            />
            {{ store.isSearching ? 'Recherche…' : 'Lancer la recherche' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import type { SearchProspectsDrawerProps } from '~/types/SearchProspectsDrawer'
import { PROSPECT_SOURCE_SEARCH_OPTIONS } from '~/constants/prospectSources'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { useToast } from '~/composables/useToast'

/** Local search form state. */
interface SearchFormState {
  category: string
  city: string
  maxResults: number
  source: string
  skipDuplicates: boolean
  onlyWithoutWebsite: boolean
}

const STORAGE_KEY: string = 'devleadhunter-search-form'

/**
 * Defines the component props.
 */
const props: SearchProspectsDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

const store = useProspectSearchStore()
const toast = useToast()

/** Quick-pick trades. */
const QUICK_CATEGORIES: ReadonlyArray<string> = [
  'Plombier',
  'Électricien',
  'Menuisier',
  'Restaurant',
  'Coiffeur',
  'Garagiste',
  'Serrurier',
  'Paysagiste',
]

/** "How it works" steps. */
const SEARCH_STEPS: ReadonlyArray<string> = [
  'Saisissez un métier et une ville, puis lancez la recherche.',
  'DevLeadHunter parcourt les sources et ajoute les artisans trouvés à vos prospects.',
  'Les nouveaux prospects sont disponibles dans vos listes et automatisations.',
]

/**
 * Default form state.
 * @returns A fresh form.
 */
function defaultForm(): SearchFormState {
  return { category: '', city: '', maxResults: 50, source: '', skipDuplicates: true, onlyWithoutWebsite: true }
}

/** The editable form. */
const form: Ref<SearchFormState> = ref<SearchFormState>(defaultForm())

/** Load the persisted form (client only). */
function loadForm(): void {
  if (import.meta.server) return
  try {
    const raw: string | null = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      form.value = { ...defaultForm(), ...(JSON.parse(raw) as Partial<SearchFormState>) }
    }
  } catch {
    form.value = defaultForm()
  }
}

/**
 * Start the search via the shared store.
 * @returns A promise resolved once the job starts.
 */
async function submit(): Promise<void> {
  if (import.meta.client) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(form.value))
  }
  try {
    await store.startSearch({
      category: form.value.category.trim(),
      city: form.value.city.trim(),
      maxResults: form.value.maxResults,
      source: form.value.source,
      skipDuplicates: form.value.skipDuplicates,
      onlyWithoutWebsite: form.value.onlyWithoutWebsite,
    })
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur au lancement de la recherche')
  }
}

// Load the saved form each time the drawer opens.
watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) loadForm()
  },
  { immediate: true },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
