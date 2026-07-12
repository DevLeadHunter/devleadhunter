<template>
  <div>
    <!-- Header -->
    <div class="mb-5">
      <NuxtLink
        to="/dashboard/automations"
        class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Automatisations
      </NuxtLink>
      <div class="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Automatisation
        </p>
        <h1 class="app-page-title">Créer une automatisation</h1>
        <p class="text-sm text-[var(--app-ink-soft)]">
          Trouver → générer les sites → {{ form.mode === 'semi_auto' ? 'valider' : 'auto' }} → démarcher.
        </p>
      </div>
    </div>

    <div class="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)]">
      <!-- Rail: stepper + live recap -->
      <aside class="sticky top-6 hidden space-y-5 lg:block">
        <DemoSitesWizardStepper
          :steps="steps"
          :current-step="currentStep"
          orientation="vertical"
          @navigate="handleStepNavigate"
        />
        <div class="app-card p-4">
          <p class="app-label mb-3">Récapitulatif</p>
          <dl class="space-y-2.5">
            <div v-for="entry in recapItems" :key="entry.label">
              <dt class="text-[10px] text-[var(--app-ink-soft)]">{{ entry.label }}</dt>
              <dd class="truncate text-sm font-medium text-[var(--app-ink)]">{{ entry.value || '—' }}</dd>
            </div>
          </dl>
        </div>
      </aside>

      <div class="min-w-0">
        <!-- Horizontal stepper (mobile / tablet) -->
        <div class="mb-5 lg:hidden">
          <DemoSitesWizardStepper :steps="steps" :current-step="currentStep" @navigate="handleStepNavigate" />
        </div>

        <!-- ══════════ Step 1 · Cible ══════════ -->
        <div v-if="currentStep === 1" key="step-1" class="wizard-step space-y-5">
          <div class="app-card space-y-5 p-5 md:p-6">
            <div>
              <h2 class="text-base font-semibold text-[var(--app-ink)]">Cible</h2>
              <p class="mt-1 text-sm text-[var(--app-ink-soft)]">Nomme l'automatisation et choisis son mode.</p>
            </div>

            <div>
              <label class="app-label mb-1.5 block">Nom de l'automatisation *</label>
              <input v-model="form.name" type="text" class="app-input w-full" placeholder="Plombiers — Rennes" />
            </div>

            <div class="flex gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] p-1">
              <button type="button" :class="segmentClass(form.mode === 'semi_auto')" @click="form.mode = 'semi_auto'">
                <UIcon name="i-lucide-hand" class="h-3.5 w-3.5" />
                Semi-auto
              </button>
              <button type="button" :class="segmentClass(form.mode === 'full_auto')" @click="form.mode = 'full_auto'">
                <UIcon name="i-lucide-bot" class="h-3.5 w-3.5" />
                Full-auto
              </button>
            </div>
            <p class="text-xs text-[var(--app-ink-soft)]">
              {{
                form.mode === 'semi_auto'
                  ? 'Tu sélectionnes les prospects et tu valides les sites avant tout envoi.'
                  : 'Tu donnes un métier + une ville + un objectif en jours — la machine fait tout, sans validation.'
              }}
            </p>
          </div>

          <!-- Semi-auto: prospect selection -->
          <template v-if="form.mode === 'semi_auto'">
            <div class="app-card p-4">
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <div>
                  <label class="app-label mb-1.5 block">Rechercher</label>
                  <input v-model="searchQuery" type="text" placeholder="Nom, ville, email…" class="app-input" />
                </div>
                <div>
                  <label class="app-label mb-1.5 block">Site web</label>
                  <UiSelectField v-model="filterWebsite" :options="websiteFilterOptions" />
                </div>
                <div>
                  <label class="app-label mb-1.5 block">Ville</label>
                  <UiCitySelect v-model="filterCity" placeholder="Toutes les villes" />
                </div>
                <div>
                  <label class="app-label mb-1.5 block">Métier</label>
                  <input v-model="filterCategory" type="text" placeholder="Ex : plombier" class="app-input" />
                </div>
                <div class="flex items-end">
                  <button class="app-btn-secondary w-full" @click="clearFilters">Réinitialiser</button>
                </div>
              </div>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="text-sm text-[var(--app-ink-soft)]">
                <span class="font-semibold text-[var(--app-ink)]">{{ selectedProspectIds.length }}</span> prospect(s)
                sélectionné(s) · {{ filteredProspects.length }} disponible(s)
              </p>
              <div class="flex items-center gap-2">
                <button class="app-btn-secondary h-8 px-3 text-xs" @click="selectAllFiltered">Tout sélectionner</button>
                <NuxtLink to="/dashboard/search-prospects" class="app-btn-secondary h-8 px-3 text-xs">
                  <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
                  Chercher plus
                </NuxtLink>
              </div>
            </div>

            <div v-if="isLoadingProspects" class="flex items-center justify-center py-16">
              <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-accent)]" />
            </div>
            <div v-else-if="filteredProspects.length === 0" class="app-card px-6 py-12 text-center">
              <LandingAsterisk class="text-3xl text-[var(--app-accent)]" />
              <p class="mt-4 text-sm text-[var(--app-ink-soft)]">
                Aucun prospect disponible — ceux déjà pris par une automatisation sont masqués.
              </p>
              <NuxtLink to="/dashboard/search-prospects" class="app-btn-primary mt-5 inline-flex">
                Trouver des prospects
              </NuxtLink>
            </div>
            <div v-else class="app-card overflow-hidden">
              <UiProspectTable
                :prospects="paginatedProspects"
                :selected-prospects="selectedProspectIds"
                @view-prospect="openProspectDrawer"
                @delete-prospect="handleDeleteProspect"
                @toggle-select="toggleSelect"
                @toggle-select-all="toggleSelectAll"
              />
              <div
                v-if="totalPages > 1"
                class="flex items-center justify-between border-t border-[var(--app-line)] bg-[var(--app-surface-2)]/50 px-4 py-3"
              >
                <span class="font-label text-xs text-[var(--app-ink-soft)]"
                  >Page {{ currentPage }} / {{ totalPages }}</span
                >
                <div class="flex items-center gap-2">
                  <button
                    :disabled="currentPage === 1"
                    class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:opacity-50"
                    @click="currentPage -= 1"
                  >
                    Précédent
                  </button>
                  <button
                    :disabled="currentPage === totalPages"
                    class="app-btn-secondary h-8 min-h-8 px-3 text-xs disabled:opacity-50"
                    @click="currentPage += 1"
                  >
                    Suivant
                  </button>
                </div>
              </div>
            </div>
          </template>

          <!-- Full-auto: query -->
          <div v-else class="app-card space-y-5 p-5 md:p-6">
            <div class="grid gap-5 md:grid-cols-2">
              <div>
                <label class="app-label mb-1.5 block">Métier(s) *</label>
                <input
                  v-model="form.metiers"
                  type="text"
                  class="app-input w-full"
                  placeholder="plombier, électricien"
                />
              </div>
              <div>
                <label class="app-label mb-1.5 block">Ville(s) *</label>
                <input v-model="form.villes" type="text" class="app-input w-full" placeholder="Rennes, Iffendic" />
              </div>
              <div>
                <label class="app-label mb-1.5 block">Objectif — jours de démarchage *</label>
                <input v-model.number="form.targetDays" type="number" min="1" max="90" class="app-input w-full" />
              </div>
              <label class="flex items-center gap-2 self-end pb-2.5 text-sm text-[var(--app-ink-soft)]">
                <input v-model="form.onlyWithoutWebsite" type="checkbox" class="h-4 w-4 accent-(--app-accent)" />
                Uniquement sans site web
              </label>
            </div>
            <p
              class="flex items-start gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5 text-xs text-[var(--app-ink-soft)]"
            >
              <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
              La machine pioche dans tes prospects non-utilisés correspondants. S'il en manque, elle te préviendra de
              lancer une recherche pour compléter.
            </p>
          </div>

          <div class="flex justify-end">
            <button type="button" class="app-btn-primary" :disabled="!canContinue" @click="goToStep(2)">
              Continuer<UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <!-- ══════════ Step 2 · Site ══════════ -->
        <div v-else-if="currentStep === 2" key="step-2" class="wizard-step space-y-6">
          <div>
            <h2 class="text-base font-semibold text-[var(--app-ink)]">Template de site</h2>
            <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
              Un modèle pour tous les prospects — tu pourras en changer par prospect à la validation.
            </p>
          </div>
          <DemoSitesTemplatePicker
            v-model="form.templateId"
            :templates="templates"
            :theme="form.theme"
            @update:theme="form.theme = $event"
          />
          <div class="flex justify-between border-t border-[var(--app-line-soft)] pt-5">
            <button type="button" class="app-btn-secondary" @click="goToStep(1)">
              <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />Retour
            </button>
            <button type="button" class="app-btn-primary" @click="goToStep(3)">
              Continuer<UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <!-- ══════════ Step 3 · Emails ══════════ -->
        <div v-else-if="currentStep === 3" key="step-3" class="wizard-step app-card space-y-5 p-5 md:p-6">
          <div>
            <h2 class="text-base font-semibold text-[var(--app-ink)]">Démarchage</h2>
            <p class="mt-1 text-sm text-[var(--app-ink-soft)]">Le cold email envoyé avec le lien de démo.</p>
          </div>

          <label
            class="flex cursor-pointer items-start gap-3.5 rounded-xl border p-4 transition-colors"
            :class="
              form.autoCampaign
                ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]/60'
                : 'border-[var(--app-line)] bg-[var(--app-bg)] hover:border-[var(--app-ink-soft)]'
            "
          >
            <input v-model="form.autoCampaign" type="checkbox" class="mt-0.5 h-4 w-4 accent-(--app-accent)" />
            <span>
              <span class="text-sm font-medium text-[var(--app-ink)]">Démarcher les prospects par email</span>
              <span class="mt-1 block text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Décoche pour seulement générer les sites (sans envoi).
              </span>
            </span>
          </label>

          <div v-if="form.autoCampaign" class="grid gap-5 md:grid-cols-2">
            <div>
              <label class="app-label mb-1.5 block">Modèle A — envoi initial *</label>
              <UiTemplateSelect
                :model-value="form.emailA"
                :templates="emailTemplates"
                @update:model-value="form.emailA = $event"
              />
            </div>
            <div>
              <label class="app-label mb-1.5 block">Modèle B — test A/B (optionnel)</label>
              <UiTemplateSelect
                :model-value="form.emailB"
                :templates="emailTemplates"
                @update:model-value="form.emailB = $event"
              />
            </div>
          </div>

          <p v-if="form.autoCampaign" class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
            <UIcon name="i-lucide-clock" class="h-3.5 w-3.5" />
            La cadence d'envoi suit tes
            <NuxtLink to="/dashboard/settings/sending" class="underline underline-offset-2 hover:text-[var(--app-ink)]">
              réglages d'envoi </NuxtLink
            >.
          </p>

          <div class="flex justify-between border-t border-[var(--app-line-soft)] pt-5">
            <button type="button" class="app-btn-secondary" @click="goToStep(2)">
              <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />Retour
            </button>
            <button type="button" class="app-btn-primary" :disabled="!canContinue" @click="goToStep(4)">
              Continuer<UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <!-- ══════════ Step 4 · Lancer ══════════ -->
        <div v-else key="step-4" class="wizard-step app-card space-y-5 p-5 md:p-6">
          <div>
            <h2 class="text-base font-semibold text-[var(--app-ink)]">Récapitulatif</h2>
            <p class="mt-1 text-sm text-[var(--app-ink-soft)]">Vérifie puis lance l'automatisation.</p>
          </div>
          <dl class="grid gap-3 sm:grid-cols-2">
            <div
              v-for="entry in recapItems"
              :key="entry.label"
              class="rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5"
            >
              <dt class="app-label">{{ entry.label }}</dt>
              <dd class="mt-1 text-sm font-medium text-[var(--app-ink)]">{{ entry.value || '—' }}</dd>
            </div>
          </dl>
          <p
            v-if="form.mode === 'semi_auto'"
            class="flex items-start gap-2 rounded-xl border border-[var(--app-blue)] bg-[var(--app-blue-soft)] p-3.5 text-xs text-[var(--app-ink)]"
          >
            <UIcon name="i-lucide-clipboard-check" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-blue)]" />
            La machine génère les sites puis <strong class="mx-1">s'arrête pour ta validation</strong> avant tout envoi.
          </p>
          <div class="flex justify-between border-t border-[var(--app-line-soft)] pt-5">
            <button type="button" class="app-btn-secondary" @click="goToStep(3)">
              <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />Retour
            </button>
            <button type="button" class="app-btn-primary" :disabled="isCreating || !canLaunch" @click="launch">
              <UIcon
                :name="isCreating ? 'i-lucide-loader-circle' : 'i-lucide-rocket'"
                :class="['h-3.5 w-3.5', isCreating && 'animate-spin']"
              />
              {{ isCreating ? 'Lancement…' : "Lancer l'automatisation" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref, watch } from 'vue'
import type { AutomationMode } from '~/types/Automation'
import type { Prospect } from '~/types'
import type { TemplateSelectOption } from '~/types/TemplateSelect'
import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'
import { createAutomation, getUsedProspectIds } from '~/services/automationsService'
import { deleteProspect as deleteProspectApi, listProspects } from '~/services/prospectsService'
import { getEmailTemplates } from '~/services/emailTemplatesService'
import { listDemoSiteTemplates } from '~/services/demoSiteService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

/** A wizard step. */
interface WizardStep {
  id: number
  label: string
}

/** A recap row. */
interface RecapItem {
  label: string
  value: string
}

/** Local wizard form. */
interface TunnelForm {
  name: string
  mode: AutomationMode
  templateId: string
  theme: DemoSiteTheme
  autoCampaign: boolean
  emailA: number
  emailB: number
  metiers: string
  villes: string
  targetDays: number
  onlyWithoutWebsite: boolean
}

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()
const route = useRoute()
const drawerStack = useDrawerStackStore()

const defaultTheme: DemoSiteTheme = { primary: '#0284c7', secondary: '#0f172a', accent: '#f59e0b' }

/** Wizard steps. */
const steps: WizardStep[] = [
  { id: 1, label: 'Cible' },
  { id: 2, label: 'Site' },
  { id: 3, label: 'Emails' },
  { id: 4, label: 'Lancer' },
]

/** Current step (1-based). */
const currentStep: Ref<number> = ref<number>(1)
/** Whether the create request is in flight. */
const isCreating: Ref<boolean> = ref<boolean>(false)
/** Whether prospects are loading. */
const isLoadingProspects: Ref<boolean> = ref<boolean>(false)
/** Selectable prospects (unused only). */
const prospects: Ref<Prospect[]> = ref<Prospect[]>([])
/** Email templates for the A/B selectors. */
const emailTemplates: Ref<TemplateSelectOption[]> = ref<TemplateSelectOption[]>([])
/** Demo-site templates. */
const templates: Ref<DemoSiteTemplate[]> = ref<DemoSiteTemplate[]>([])
/** Selected prospect ids (as strings, matching UiProspectTable). */
const selectedProspectIds: Ref<string[]> = ref<string[]>([])

// Filters
const searchQuery: Ref<string> = ref<string>('')
const filterWebsite: Ref<'all' | 'yes' | 'no'> = ref<'all' | 'yes' | 'no'>('no')
const filterCity: Ref<string> = ref<string>('')
const filterCategory: Ref<string> = ref<string>('')
const currentPage: Ref<number> = ref<number>(1)
const pageSize: number = 25

/** Website filter options. */
const websiteFilterOptions: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'all', label: 'Tous' },
  { value: 'yes', label: 'Avec site' },
  { value: 'no', label: 'Sans site' },
]

/** Wizard state. */
const form: Ref<TunnelForm> = ref<TunnelForm>({
  name: '',
  mode: 'semi_auto',
  templateId: '',
  theme: { ...defaultTheme },
  autoCampaign: true,
  emailA: 0,
  emailB: 0,
  metiers: '',
  villes: '',
  targetDays: 10,
  onlyWithoutWebsite: true,
})

/** Prospects matching every filter. */
const filteredProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  let list: Prospect[] = prospects.value
  const query: string = searchQuery.value.trim().toLowerCase()
  if (query) {
    list = list.filter(
      (p: Prospect): boolean =>
        p.name.toLowerCase().includes(query) ||
        (p.city ?? '').toLowerCase().includes(query) ||
        (p.email ?? '').toLowerCase().includes(query),
    )
  }
  if (filterCity.value) {
    const city: string = filterCity.value.toLowerCase()
    list = list.filter((p: Prospect): boolean => (p.city ?? '').toLowerCase().includes(city))
  }
  if (filterCategory.value) {
    const cat: string = filterCategory.value.toLowerCase()
    list = list.filter((p: Prospect): boolean => p.category.toLowerCase().includes(cat))
  }
  if (filterWebsite.value === 'yes') list = list.filter((p: Prospect): boolean => Boolean(p.website))
  else if (filterWebsite.value === 'no') list = list.filter((p: Prospect): boolean => !p.website)
  return list
})

/** Total filtered pages. */
const totalPages: ComputedRef<number> = computed((): number =>
  Math.max(1, Math.ceil(filteredProspects.value.length / pageSize)),
)

/** Prospects on the current page. */
const paginatedProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  const start: number = (currentPage.value - 1) * pageSize
  return filteredProspects.value.slice(start, start + pageSize)
})

/** Name of the selected template. */
const selectedTemplateName: ComputedRef<string> = computed(
  (): string =>
    templates.value.find((t: DemoSiteTemplate): boolean => t.id === form.value.templateId)?.name ?? 'Par défaut',
)

/** Recap rows. */
const recapItems: ComputedRef<RecapItem[]> = computed((): RecapItem[] => {
  const target: string =
    form.value.mode === 'full_auto'
      ? `${form.value.metiers || '—'} · ${form.value.villes || '—'} · ${form.value.targetDays} j`
      : `${selectedProspectIds.value.length} prospect(s)`
  return [
    { label: 'Nom', value: form.value.name },
    { label: 'Mode', value: form.value.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto' },
    { label: 'Cible', value: target },
    { label: 'Template', value: selectedTemplateName.value },
    { label: 'Démarchage', value: form.value.autoCampaign ? (form.value.emailB ? 'A/B' : 'Modèle A') : 'Sites seuls' },
  ]
})

/** Whether the current step can advance. */
const canContinue: ComputedRef<boolean> = computed((): boolean => {
  if (currentStep.value === 1) {
    if (!form.value.name.trim()) return false
    if (form.value.mode === 'semi_auto') return selectedProspectIds.value.length > 0
    return Boolean(form.value.metiers.trim() && form.value.villes.trim() && form.value.targetDays > 0)
  }
  if (currentStep.value === 3 && form.value.autoCampaign) return form.value.emailA > 0
  return true
})

/** Whether the automatisation can be launched. */
const canLaunch: ComputedRef<boolean> = computed((): boolean => {
  if (form.value.mode === 'semi_auto') return selectedProspectIds.value.length > 0
  return Boolean(form.value.metiers.trim() && form.value.villes.trim() && form.value.targetDays > 0)
})

/**
 * Classes for a segmented-control button.
 * @param active - Whether the segment is selected.
 * @returns Tailwind classes.
 */
function segmentClass(active: boolean): string {
  const base: string =
    'flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors'
  return active
    ? `${base} bg-[var(--app-btn-bg)] text-[var(--app-btn-text)]`
    : `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Navigate to a step and scroll to top.
 * @param step - Target step (1-based).
 */
function goToStep(step: number): void {
  currentStep.value = step
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

/**
 * Stepper node clicked — only allow going back.
 * @param stepId - Target step id.
 */
function handleStepNavigate(stepId: number): void {
  if (stepId < currentStep.value) goToStep(stepId)
}

/** Reset the filters. */
function clearFilters(): void {
  searchQuery.value = ''
  filterCity.value = ''
  filterCategory.value = ''
  filterWebsite.value = 'no'
  currentPage.value = 1
}

/**
 * Toggle a prospect in the selection.
 * @param prospect - The prospect toggled.
 */
function toggleSelect(prospect: Prospect): void {
  const id: string = String(prospect.id)
  const idx: number = selectedProspectIds.value.indexOf(id)
  if (idx === -1) selectedProspectIds.value = [...selectedProspectIds.value, id]
  else selectedProspectIds.value = selectedProspectIds.value.filter((x: string): boolean => x !== id)
}

/**
 * Select or clear every prospect on the current page.
 * @param checked - True to add the page's rows.
 */
function toggleSelectAll(checked: boolean): void {
  const pageIds: string[] = paginatedProspects.value.map((p: Prospect): string => String(p.id))
  if (checked) {
    selectedProspectIds.value = Array.from(new Set<string>([...selectedProspectIds.value, ...pageIds]))
  } else {
    const pageSet: Set<string> = new Set<string>(pageIds)
    selectedProspectIds.value = selectedProspectIds.value.filter((id: string): boolean => !pageSet.has(id))
  }
}

/** Select every filtered prospect (across pages). */
function selectAllFiltered(): void {
  const ids: string[] = filteredProspects.value.map((p: Prospect): string => String(p.id))
  selectedProspectIds.value = Array.from(new Set<string>([...selectedProspectIds.value, ...ids]))
}

/**
 * Open the prospect detail drawer.
 * @param prospect - The prospect to inspect.
 */
function openProspectDrawer(prospect: Prospect): void {
  drawerStack.push({ kind: 'prospect', prospect })
}

/**
 * Delete a prospect from the pool.
 * @param prospect - The prospect to delete.
 * @returns A promise resolved once deleted.
 */
async function handleDeleteProspect(prospect: Prospect): Promise<void> {
  try {
    await deleteProspectApi(prospect.id)
    prospects.value = prospects.value.filter((p: Prospect): boolean => p.id !== prospect.id)
    selectedProspectIds.value = selectedProspectIds.value.filter((id: string): boolean => id !== String(prospect.id))
    toast.success(`Prospect « ${prospect.name} » supprimé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  }
}

/**
 * Split a comma/newline separated field into a clean string list.
 * @param raw - Raw input.
 * @returns Trimmed non-empty entries.
 */
function splitList(raw: string): string[] {
  return raw
    .split(/[,\n]/)
    .map((s: string): string => s.trim())
    .filter((s: string): boolean => s.length > 0)
}

/**
 * Create the automatisation then open its detail page.
 * @returns A promise resolved once created.
 */
async function launch(): Promise<void> {
  isCreating.value = true
  try {
    const detail = await createAutomation({
      name: form.value.name.trim(),
      mode: form.value.mode,
      prospect_ids:
        form.value.mode === 'semi_auto' ? selectedProspectIds.value.map((id: string): number => Number(id)) : [],
      search_metiers: form.value.mode === 'full_auto' ? splitList(form.value.metiers) : [],
      search_villes: form.value.mode === 'full_auto' ? splitList(form.value.villes) : [],
      target_days: form.value.mode === 'full_auto' ? form.value.targetDays : null,
      only_without_website: form.value.onlyWithoutWebsite,
      auto_enrich: true,
      auto_generate: true,
      template_id: form.value.templateId || null,
      theme: form.value.theme,
      auto_campaign: form.value.autoCampaign,
      email_template_id_a: form.value.autoCampaign ? form.value.emailA || null : null,
      email_template_id_b: form.value.autoCampaign ? form.value.emailB || null : null,
      send_delay_minutes: 20,
      follow_ups: [],
    })
    toast.success('Automatisation lancée')
    await navigateTo(`/dashboard/automations/${detail.id}`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du lancement')
  } finally {
    isCreating.value = false
  }
}

// Reset pagination when filters change.
watch([searchQuery, filterCity, filterCategory, filterWebsite], (): void => {
  currentPage.value = 1
})

onMounted(async (): Promise<void> => {
  isLoadingProspects.value = true
  try {
    const [prospectList, usedIds, emailList, demoList] = await Promise.all([
      listProspects(),
      getUsedProspectIds(),
      getEmailTemplates(),
      listDemoSiteTemplates(),
    ])
    const used: Set<number> = new Set<number>(usedIds)
    prospects.value = prospectList.filter((p: Prospect): boolean => !used.has(p.id))
    emailTemplates.value = emailList.map((t): TemplateSelectOption => ({ id: t.id, name: t.name, subject: t.subject }))
    templates.value = demoList
    const first: DemoSiteTemplate | undefined = demoList[0]
    if (first) {
      form.value.templateId = first.id
      form.value.theme = { ...first.default_theme }
    }
  } catch {
    // Non-critical — the wizard still works with what loaded.
  } finally {
    isLoadingProspects.value = false
  }

  // Pre-select a prospect passed via ?prospect= (single-site shortcut).
  const raw: string | undefined = Array.isArray(route.query.prospect) ? route.query.prospect[0] : route.query.prospect
  if (raw && !Number.isNaN(Number(raw))) {
    selectedProspectIds.value = [raw]
  }
})
</script>

<style scoped>
.wizard-step {
  animation: wizard-step-in 0.3s ease;
}
@keyframes wizard-step-in {
  from {
    opacity: 0;
    transform: translateX(18px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .wizard-step {
    animation: none;
  }
}
</style>
