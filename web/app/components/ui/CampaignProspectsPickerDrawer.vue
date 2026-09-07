<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
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
            <UIcon name="i-lucide-user-plus" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Ajouter des prospects</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              Sélectionnez les prospects à intégrer à cette campagne
            </p>
          </div>
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <div v-if="isLoading" class="flex items-center justify-center py-16">
            <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-ink-soft)]" />
          </div>

          <div v-else-if="availableProspects.length === 0" class="py-14 text-center">
            <span
              class="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--app-line)]"
            >
              <UIcon name="i-lucide-users" class="h-5 w-5 text-[var(--app-ink-soft)]" />
            </span>
            <p class="text-sm font-medium text-[var(--app-ink)]">Aucun prospect disponible</p>
            <p class="text-muted mx-auto mt-1 max-w-xs text-xs">
              Tous vos prospects sont déjà dans cette campagne, ou vous n'en avez pas encore.
            </p>
          </div>

          <template v-else>
            <div class="relative">
              <UIcon
                name="i-lucide-search"
                class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
              />
              <input v-model="query" type="text" placeholder="Rechercher un prospect…" class="app-input w-full pl-9" />
            </div>

            <UiSelectField
              v-if="showCategoryFilter"
              v-model="categoryFilter"
              :options="categoryOptions"
              placeholder="Tous les métiers"
            />

            <div class="flex items-center justify-between text-xs">
              <button
                type="button"
                class="font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                @click="toggleSelectAllFiltered"
              >
                {{ areAllFilteredSelected ? 'Tout désélectionner' : 'Tout sélectionner' }}
              </button>
              <span class="text-[var(--app-ink-soft)] tabular-nums">
                {{ selectedIds.length }} sélectionné{{ selectedIds.length !== 1 ? 's' : '' }}
              </span>
            </div>

            <p v-if="filteredProspects.length === 0" class="text-muted py-8 text-center text-sm">
              Aucun prospect ne correspond à votre recherche.
            </p>

            <div v-else class="space-y-1">
              <div
                v-for="prospect in filteredProspects"
                :key="prospect.id"
                class="flex cursor-pointer items-center gap-3 rounded-lg border border-transparent p-2.5 transition-colors hover:bg-[var(--app-surface-2)]"
                :class="selectedIds.includes(prospect.id) ? 'border-[var(--app-line)] bg-[var(--app-surface-2)]' : ''"
                @click="toggleProspect(prospect.id)"
              >
                <span class="pointer-events-none">
                  <UiCheckbox :model-value="selectedIds.includes(prospect.id)" />
                </span>
                <div class="min-w-0">
                  <p class="truncate text-sm text-[var(--app-ink)]">{{ prospect.name }}</p>
                  <p v-if="prospectLocationLabel(prospect)" class="text-muted truncate text-xs">
                    {{ prospectLocationLabel(prospect) }}
                  </p>
                  <div
                    v-if="prospect.contacted || membershipsFor(prospect.id).length > 0"
                    class="mt-1 flex flex-wrap items-center gap-1"
                  >
                    <span
                      v-if="prospect.contacted"
                      class="app-badge app-badge--success"
                      title="Déjà contacté par email"
                    >
                      <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
                      Contacté
                    </span>
                    <span
                      v-for="membership in membershipsFor(prospect.id)"
                      :key="membership.id"
                      class="app-badge app-badge--info"
                      :title="`Déjà dans la campagne « ${membership.name} »`"
                    >
                      <UIcon name="i-lucide-megaphone" class="h-3 w-3" />
                      {{ membership.name }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div class="flex flex-col gap-2 border-t border-[var(--app-line)] px-5 py-4 sm:flex-row">
          <button
            type="button"
            class="app-btn-secondary w-full sm:flex-1"
            :disabled="isSubmitting"
            @click="emit('close')"
          >
            Annuler
          </button>
          <button
            type="button"
            class="app-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50 sm:flex-1"
            :disabled="selectedIds.length === 0 || isSubmitting"
            @click="submit"
          >
            <UIcon v-if="isSubmitting" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            {{ submitLabel }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type {
  UiCampaignProspectsPickerDrawerEmits,
  UiCampaignProspectsPickerDrawerProps,
} from '~/types/UiCampaignProspectsPickerDrawer'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { Prospect } from '~/types'
import type { SelectFieldOption } from '~/types/SelectField'
import type {
  CampaignDetailResponse,
  CampaignEnqueueOutcome,
  CampaignProspectMembership,
  CampaignSkippedProspect,
} from '~/services/campaignService'
import { CampaignService } from '~/services/campaignService'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

/** Drawer to attach existing prospects to a campaign. */
const props: UiCampaignProspectsPickerDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  campaignId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  existingProspectIds: {
    type: Array as PropType<number[]>,
    default: () => [],
  },
})

const emit: EmitFn<UiCampaignProspectsPickerDrawerEmits> = defineEmits<UiCampaignProspectsPickerDrawerEmits>()

const toast: UseToastReturn = useToast()

const allProspects: Ref<Prospect[]> = ref([])
const memberships: Ref<Record<number, CampaignProspectMembership[]>> = ref({})
const selectedIds: Ref<number[]> = ref([])
const query: Ref<string> = ref('')
const categoryFilter: Ref<string> = ref('')
const isLoading: Ref<boolean> = ref(false)
const isSubmitting: Ref<boolean> = ref(false)

/** Prospects not already in the campaign — the pool the picker offers. */
const availableProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  const taken: Set<number> = new Set(props.existingProspectIds)
  return allProspects.value.filter((prospect: Prospect): boolean => !taken.has(prospect.id))
})

/** Trade options for the filter, derived from the trades actually present in the pool. */
const categoryOptions: ComputedRef<SelectFieldOption<string>[]> = computed((): SelectFieldOption<string>[] => {
  const distinct: Set<string> = new Set()
  for (const prospect of availableProspects.value) {
    const category: string = prospect.category?.trim() ?? ''
    if (category) distinct.add(category)
  }
  const sorted: string[] = [...distinct].sort((first: string, second: string): number =>
    first.localeCompare(second, 'fr'),
  )
  return [
    { label: 'Tous les métiers', value: '' },
    ...sorted.map((category: string): SelectFieldOption<string> => ({ label: category, value: category })),
  ]
})

/** Show the trade filter only when the pool spans more than one trade. */
const showCategoryFilter: ComputedRef<boolean> = computed((): boolean => categoryOptions.value.length > 2)

/** Available prospects narrowed by the trade filter, then the search query (name, city or trade). */
const filteredProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  const needle: string = query.value.trim().toLowerCase()
  const category: string = categoryFilter.value
  return availableProspects.value.filter((prospect: Prospect): boolean => {
    if (category && prospect.category !== category) return false
    if (!needle) return true
    const haystack: string = `${prospect.name} ${prospect.city ?? ''} ${prospect.category}`.toLowerCase()
    return haystack.includes(needle)
  })
})

/** True when every currently listed prospect is already selected. */
const areAllFilteredSelected: ComputedRef<boolean> = computed((): boolean => {
  return (
    filteredProspects.value.length > 0 &&
    filteredProspects.value.every((prospect: Prospect): boolean => selectedIds.value.includes(prospect.id))
  )
})

const submitLabel: ComputedRef<string> = computed((): string => {
  if (isSubmitting.value) return 'Ajout…'
  const count: number = selectedIds.value.length
  if (count === 0) return 'Ajouter des prospects'
  return `Ajouter ${count} prospect${count !== 1 ? 's' : ''}`
})

/**
 * Build the secondary line under a prospect name (city and trade).
 * @param prospect - Prospect to describe.
 * @returns A `Ville · métier` label, or an empty string when both are missing.
 */
function prospectLocationLabel(prospect: Prospect): string {
  return [prospect.city, prospect.category].filter(Boolean).join(' · ')
}

/**
 * Campaigns a prospect already belongs to, for the picker badges.
 * @param prospectId - Prospect to look up.
 * @returns The campaigns already containing this prospect, or an empty list.
 */
function membershipsFor(prospectId: number): CampaignProspectMembership[] {
  return memberships.value[prospectId] ?? []
}

/**
 * Fetch the user's prospects to populate the picker.
 * @returns A promise resolved once the prospects are loaded.
 */
async function loadProspects(): Promise<void> {
  isLoading.value = true
  try {
    allProspects.value = await ProspectsService.listProspects()
  } catch {
    toast.error('Impossible de charger vos prospects')
    allProspects.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * Fetch the prospect→campaigns map so the picker can flag prospects already in a campaign.
 * @returns A promise resolved once the memberships are loaded (best-effort — badges just hide on failure).
 */
async function loadMemberships(): Promise<void> {
  try {
    memberships.value = await CampaignService.getProspectMemberships()
  } catch {
    memberships.value = {}
  }
}

/**
 * Toggle a single prospect in the selection.
 * @param prospectId - Prospect id whose row was clicked.
 */
function toggleProspect(prospectId: number): void {
  const index: number = selectedIds.value.indexOf(prospectId)
  if (index === -1) selectedIds.value.push(prospectId)
  else selectedIds.value.splice(index, 1)
}

/** Select every listed prospect, or clear them when all are already selected. */
function toggleSelectAllFiltered(): void {
  if (areAllFilteredSelected.value) {
    const listed: Set<number> = new Set(filteredProspects.value.map((prospect: Prospect): number => prospect.id))
    selectedIds.value = selectedIds.value.filter((id: number): boolean => !listed.has(id))
    return
  }
  const merged: Set<number> = new Set(selectedIds.value)
  for (const prospect of filteredProspects.value) merged.add(prospect.id)
  selectedIds.value = [...merged]
}

/**
 * Attach the selected prospects to the campaign, then notify the host.
 * @returns A promise resolved once the prospects are added.
 */
async function submit(): Promise<void> {
  if (props.campaignId === null || selectedIds.value.length === 0) return
  isSubmitting.value = true
  try {
    const count: number = selectedIds.value.length
    const updated: CampaignDetailResponse = await CampaignService.addProspects(props.campaignId, selectedIds.value)
    toast.success(`${count} prospect${count !== 1 ? 's' : ''} ajouté${count !== 1 ? 's' : ''}`)
    warnAboutProspectsLeftOutOfQueue(updated.enqueue_outcome ?? null)
    emit('added')
  } catch {
    toast.error("Erreur lors de l'ajout des prospects")
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Warn when newcomers joined a launched campaign but not its send queue yet (no live demo / no video).
 * @param outcome - Enqueue outcome returned by the add call, or null when the campaign is not launched.
 */
function warnAboutProspectsLeftOutOfQueue(outcome: CampaignEnqueueOutcome | null): void {
  if (!outcome) return
  if (outcome.skipped_no_demo.length > 0) {
    const several: boolean = outcome.skipped_no_demo.length > 1
    toast.warning(
      `Pas encore en file d'attente (pas de site démo actif) : ${skippedProspectNames(outcome.skipped_no_demo)}. ` +
        `Génère ${several ? 'leurs démos : ils rejoindront' : 'sa démo : il rejoindra'} la file à ${several ? 'leur' : 'sa'} position.`,
    )
  }
  if (outcome.skipped_no_video.length > 0) {
    toast.warning(
      `Pas encore en file d'attente (pas de vidéo prête) : ${skippedProspectNames(outcome.skipped_no_video)}.`,
    )
  }
}

/**
 * Comma-separated names of prospects left out of the queue, for the warning toasts.
 * @param prospects - The skipped prospects.
 * @returns Their names joined by commas.
 */
function skippedProspectNames(prospects: CampaignSkippedProspect[]): string {
  return prospects.map((prospect: CampaignSkippedProspect): string => prospect.name).join(', ')
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (!open) return
    selectedIds.value = []
    query.value = ''
    categoryFilter.value = ''
    void loadProspects()
    void loadMemberships()
  },
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
