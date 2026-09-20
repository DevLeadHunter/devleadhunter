<template>
  <div>
    <div class="mb-5">
      <button
        type="button"
        class="inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
        @click="leaveTunnel"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        {{ originLink.label }}
      </button>
      <h1 class="app-page-title mt-3">{{ isSiteMode ? 'Créer des sites démo' : 'Créer une automatisation' }}</h1>
    </div>

    <UiWizardStepper :model-value="currentStep" :steps="steps" class="mb-6" @update:model-value="goToStep" />

    <div class="min-w-0">
      <div v-if="activeStepKey === 'target'" key="step-target" class="wizard-step space-y-5 pb-20">
        <div class="app-card space-y-5 p-5 md:p-6">
          <div>
            <label class="app-label mb-1.5 block">Nom de l'automatisation</label>
            <input
              v-model="form.name"
              type="text"
              class="app-input w-full"
              placeholder="Plombiers — Rennes (optionnel)"
            />
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
        </div>

        <template v-if="form.mode === 'semi_auto'">
          <div class="app-card p-4">
            <div class="grid grid-cols-1 gap-4 @sm:grid-cols-2 @5xl:grid-cols-5">
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
              <button type="button" class="app-btn-secondary h-8 px-3 text-xs" @click="openSearchDrawer">
                <UIcon name="i-lucide-search" class="h-3.5 w-3.5" />
                Chercher plus
              </button>
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
            <button type="button" class="app-btn-primary mt-5 inline-flex" @click="openSearchDrawer">
              Trouver des prospects
            </button>
          </div>
          <div v-else class="app-card overflow-hidden">
            <UiProspectTable
              :prospects="paginatedProspects"
              :selected-prospects="selectedProspectIds"
              @view-prospect="openProspectDrawer"
              @edit-prospect="openProspectEditDrawer"
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

        <div v-else class="app-card space-y-5 p-5 md:p-6">
          <div class="grid gap-5 @2xl:grid-cols-2">
            <div>
              <label class="app-label mb-1.5 block">Métier(s) *</label>
              <input v-model="form.metiers" type="text" class="app-input w-full" placeholder="plombier, électricien" />
            </div>
            <div>
              <label class="app-label mb-1.5 block">Ville(s) *</label>
              <input v-model="form.villes" type="text" class="app-input w-full" placeholder="Rennes, Iffendic" />
            </div>
            <div>
              <label class="app-label mb-1.5 block">Objectif — jours de démarchage *</label>
              <input
                v-model.number="form.targetDays"
                type="number"
                min="1"
                max="90"
                class="app-input w-full"
                placeholder="15"
              />
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
      </div>

      <div v-else-if="activeStepKey === 'site'" key="step-site" class="wizard-step space-y-6 pb-20">
        <div>
          <h2 class="text-base font-semibold text-[var(--app-ink)]">Template de site</h2>
          <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
            Un modèle pour tous les prospects — tu pourras en changer par prospect à la validation.
          </p>
        </div>
        <DemoSitesTemplatePicker
          :model-value="form.templateId"
          :templates="templates"
          :theme="form.theme"
          :recommended-trade="recommendedTrade"
          @update:model-value="selectTemplate"
          @update:theme="form.theme = $event"
        />
      </div>

      <div
        v-else-if="activeStepKey === 'emails'"
        key="step-emails"
        class="wizard-step app-card space-y-5 p-5 pb-20 md:p-6"
      >
        <div>
          <h2 class="text-base font-semibold text-[var(--app-ink)]">Démarchage</h2>
          <p class="mt-1 text-sm text-[var(--app-ink-soft)]">Le cold email envoyé avec le lien de démo.</p>
        </div>

        <div
          class="flex items-center justify-between gap-4 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
        >
          <div class="flex min-w-0 items-start gap-3">
            <UIcon name="i-lucide-send" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
            <div class="min-w-0">
              <p class="text-sm font-semibold text-[var(--app-ink)]">Démarcher les prospects par email</p>
              <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Désactivez pour seulement générer les sites, sans aucun envoi.
              </p>
            </div>
          </div>
          <UiSwitch id="automation-auto-campaign" v-model="form.autoCampaign" />
        </div>

        <div v-if="form.autoCampaign" class="space-y-5">
          <div>
            <label class="app-label mb-1.5 block">
              Modèle A — envoi initial <span class="text-[var(--app-accent)]">*</span>
            </label>
            <UiTemplateSelect
              :model-value="form.emailA"
              :templates="emailTemplates"
              allow-create
              @update:model-value="form.emailA = $event"
              @create="openCreate((id) => (form.emailA = id))"
              @preview="openPreview"
            />
          </div>
          <div>
            <label class="app-label mb-1.5 block">Modèle B — test A/B (optionnel)</label>
            <UiTemplateSelect
              :model-value="form.emailB"
              :templates="emailTemplates"
              allow-create
              @update:model-value="form.emailB = $event"
              @create="openCreate((id) => (form.emailB = id))"
              @preview="openPreview"
            />
          </div>

          <div
            class="flex items-start justify-between gap-4 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
          >
            <div class="min-w-0">
              <label class="text-sm font-medium text-[var(--app-ink)]" for="automation-auto-follow-up">
                Envoyer une relance
              </label>
              <p class="mt-0.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Un second email part aux prospects restés silencieux, au délai fixé dans votre cadence d'envoi.
              </p>
            </div>
            <UiSwitch id="automation-auto-follow-up" v-model="form.autoFollowUp" />
          </div>

          <div v-if="form.autoFollowUp">
            <label class="app-label mb-1.5 block">Modèle de relance</label>
            <UiTemplateSelect
              :model-value="form.followUpTemplate"
              :templates="emailTemplates"
              allow-create
              @update:model-value="form.followUpTemplate = $event"
              @create="openCreate((id) => (form.followUpTemplate = id))"
              @preview="openPreview"
            />
          </div>
        </div>

        <UiCallout v-if="form.autoCampaign && !form.emailA" variant="warning">
          Choisissez un modèle A pour continuer — c'est l'email qui porte le lien de démo. Sans lui, l'automatisation
          n'a rien à envoyer.
        </UiCallout>

        <div
          v-if="form.autoCampaign"
          class="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs text-[var(--app-ink-soft)]"
        >
          <span class="flex items-center gap-1.5">
            <UIcon name="i-lucide-clock" class="h-3.5 w-3.5" />
            La cadence d'envoi suit tes réglages.
          </span>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-1 font-medium text-[var(--app-ink)] transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]"
            @click="openSendPolicyDrawer"
          >
            <UIcon name="i-lucide-sliders-horizontal" class="h-3.5 w-3.5" />
            Réglages d'envoi
          </button>
        </div>
      </div>

      <div v-else key="step-launch" class="wizard-step app-card space-y-5 p-5 pb-20 md:p-6">
        <UiCelebrationHero
          class="pt-2"
          icon="i-lucide-rocket"
          title="Tout est prêt"
          :subtitle="
            isSiteMode
              ? 'Un dernier coup d’œil, puis la machine génère les sites.'
              : 'Un dernier coup d’œil, puis la machine prend le relais.'
          "
        />

        <dl class="grid gap-3 @sm:grid-cols-2">
          <div
            v-for="(entry, index) in recapItems"
            :key="entry.label"
            class="recap-reveal rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-3.5"
            :style="{ '--recap-order': index + 1 }"
          >
            <dt class="app-label flex items-center gap-1.5">
              <UIcon :name="entry.icon" class="h-3 w-3 text-[var(--app-accent-ink)]" />
              {{ entry.label }}
            </dt>
            <dd class="mt-1.5 text-sm font-medium text-[var(--app-ink)]">{{ entry.value }}</dd>
            <dd v-if="entry.detail" class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              {{ entry.detail }}
            </dd>
          </div>
        </dl>

        <p
          v-if="form.mode === 'semi_auto'"
          class="recap-reveal flex items-start gap-2 rounded-xl border border-[var(--app-blue)] bg-[var(--app-blue-soft)] p-3.5 text-xs text-[var(--app-ink)]"
          :style="{ '--recap-order': recapItems.length + 1 }"
        >
          <UIcon name="i-lucide-clipboard-check" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-blue)]" />
          La machine génère les sites puis <strong class="mx-1">s'arrête pour votre validation</strong> avant tout
          envoi.
        </p>
      </div>

      <div
        class="sticky bottom-[calc(1rem+env(safe-area-inset-bottom))] z-10 mt-5 flex items-center justify-between gap-3 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]/90 px-3 py-2 shadow-lg backdrop-blur"
      >
        <button
          v-if="currentStep > 1"
          type="button"
          class="app-btn-secondary"
          :disabled="isCreating"
          @click="goToStep(currentStep - 1)"
        >
          <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />Précédent
        </button>
        <span v-else />
        <button
          v-if="currentStep < steps.length"
          type="button"
          class="app-btn-primary"
          :disabled="!canContinue"
          @click="goToStep(currentStep + 1)"
        >
          Continuer<UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
        </button>
        <button
          v-else
          type="button"
          :class="['app-btn-primary', canLaunch && !isCreating && 'app-btn-celebrate']"
          :disabled="isCreating || !canLaunch"
          @click="launch"
        >
          <UIcon
            :name="isCreating ? 'i-lucide-loader-circle' : 'i-lucide-rocket'"
            :class="['h-3.5 w-3.5', isCreating && 'animate-spin']"
          />
          {{ launchLabel }}
        </button>
      </div>
    </div>

    <UiConfirmModal
      ref="leaveConfirmModal"
      title="Quitter le tunnel ?"
      message="Votre configuration est enregistrée : vous la retrouverez en revenant. Quitter maintenant ?"
      confirm-text="Quitter"
      cancel-text="Rester"
      @confirm="discardDraftAndLeave"
    />
  </div>
</template>

<script lang="ts" setup>
import type { LocationQueryValue } from 'vue-router'
import type { EmailTemplate } from '~/types/index'
import type { AutomationDetail, SendPolicy } from '~/types/Automation'
import type { UseDashboardScrollReturn, UseToastReturn } from '~/types/Composables'
import type {
  AutomationDraft,
  AutomationOriginLink,
  AutomationRecapRow,
  AutomationStepDefinition,
  AutomationStepKey,
  TunnelForm,
} from '~/types/AutomationCreatePage'
import { formatSendPolicySummary } from '~/utils/sendPolicy'
import { SendPolicyService } from '~/services/sendPolicyService'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref, watch } from 'vue'
import type { Prospect } from '~/types'
import type { TemplateSelectOption } from '~/types/TemplateSelect'
import type { UiWizardStep } from '~/types/UiWizardStepper'
import type { BulkGenerateItemResult, BulkGenerateResult, DemoSiteTemplate } from '~/services/demoSiteService'
import { AutomationsService } from '~/services/automationsService'
import { ProspectsService } from '~/services/prospectsService'
import { EmailTemplatesService } from '~/services/emailTemplatesService'
import { DEFAULT_DEMO_SITE_THEME, DemoSiteService } from '~/services/demoSiteService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { useDashboardScroll } from '~/composables/useDashboardScroll'
import { useToast } from '~/composables/useToast'
import { sortTemplatesByRecommendation } from '~/utils/templateRecommendation'
import { ProspectWebsite } from '~/utils/prospectWebsite'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast: UseToastReturn = useToast()
const route: ReturnType<typeof useRoute> = useRoute()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const searchStore: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const { scrollToTop }: UseDashboardScrollReturn = useDashboardScroll()

/** Every wizard step, in order; the emails one is dropped when the tunnel targets sites only. */
const ALL_STEPS: AutomationStepDefinition[] = [
  { key: 'target', label: 'Cible', hint: 'Prospects ou métier + ville' },
  { key: 'site', label: 'Site', hint: 'Template des sites' },
  { key: 'emails', label: 'Emails', hint: 'Cold email A/B' },
  { key: 'launch', label: 'Lancer', hint: 'Vérifier & démarrer' },
]

/** sessionStorage key holding the tunnel draft, so leaving the page loses nothing. */
const TUNNEL_DRAFT_STORAGE_KEY: string = 'dlh-automation-draft'

/** How many prospects are named in the recap before it falls back to a count. */
const NAMED_PROSPECTS_IN_RECAP: number = 3

/** Current step (1-based position among the visible steps). */
const currentStep: Ref<number> = ref(1)
/** Whether the user picked a template himself — stops the recommended default from overriding him. */
const hasPickedTemplate: Ref<boolean> = ref(false)
/** The user's effective sending cadence, shown in the recap. */
const sendPolicy: Ref<SendPolicy | null> = ref(null)
const leaveConfirmModal: Ref<{ open: () => void } | null> = ref(null)
/** Whether the create request is in flight. */
const isCreating: Ref<boolean> = ref(false)
/** Whether prospects are loading. */
const isLoadingProspects: Ref<boolean> = ref(false)
/** Selectable prospects (unused only). */
const prospects: Ref<Prospect[]> = ref([])
/** Email templates for the A/B selectors. */
const emailTemplates: Ref<TemplateSelectOption[]> = ref([])
/** Demo-site templates. */
const templates: Ref<DemoSiteTemplate[]> = ref([])
/** Selected prospect ids (as strings, matching UiProspectTable). */
const selectedProspectIds: Ref<string[]> = ref([])

// Filters
const searchQuery: Ref<string> = ref('')
const filterWebsite: Ref<'all' | 'yes' | 'no'> = ref('all')
const filterCity: Ref<string> = ref('')
const filterCategory: Ref<string> = ref('')
const currentPage: Ref<number> = ref(1)
const pageSize: number = 25

/** Website filter options — un site mort ou annuaire compte comme « sans site ». */
const websiteFilterOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Tous' },
  { value: 'yes', label: 'Avec site' },
  { value: 'no', label: 'Sans site (ou site mort)' },
]

/** Wizard state. */
const form: Ref<TunnelForm> = ref({
  name: '',
  mode: 'semi_auto',
  templateId: '',
  theme: { ...DEFAULT_DEMO_SITE_THEME },
  autoCampaign: true,
  autoFollowUp: true,
  followUpTemplate: 0,
  emailA: 0,
  emailB: 0,
  metiers: '',
  villes: '',
  targetDays: 10,
  onlyWithoutWebsite: true,
})

const { openCreate, openPreview }: EmailTemplateCreator = useEmailTemplateCreator(emailTemplates, reloadEmailTemplates)

/** Entered from « Sites démo » : the tunnel generates sites, so the cold-email step is dropped. */
const isSiteMode: ComputedRef<boolean> = computed((): boolean => route.query.from === 'sites')

/** Steps actually shown, renumbered so the stepper stays 1..n. */
const steps: ComputedRef<UiWizardStep[]> = computed((): UiWizardStep[] =>
  ALL_STEPS.filter((step: AutomationStepDefinition): boolean => !isSiteMode.value || step.key !== 'emails').map(
    (step: AutomationStepDefinition, index: number): UiWizardStep => ({
      id: index + 1,
      label: step.label,
      hint: step.hint,
    }),
  ),
)

/** Which step the current position stands for. */
const activeStepKey: ComputedRef<AutomationStepKey> = computed((): AutomationStepKey => {
  const visible: AutomationStepDefinition[] = ALL_STEPS.filter(
    (step: AutomationStepDefinition): boolean => !isSiteMode.value || step.key !== 'emails',
  )
  return visible[currentStep.value - 1]?.key ?? 'target'
})

const originLink: ComputedRef<AutomationOriginLink> = computed(
  (): AutomationOriginLink =>
    isSiteMode.value
      ? { to: '/dashboard/demo-sites', label: 'Sites démo' }
      : { to: '/dashboard/automations', label: 'Automatisations' },
)

const launchLabel: ComputedRef<string> = computed((): string => {
  if (isCreating.value) return 'Lancement…'
  return isSiteMode.value ? 'Générer les sites' : "Lancer l'automatisation"
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
  if (filterWebsite.value === 'yes')
    list = list.filter((prospect: Prospect): boolean => ProspectWebsite.hasWorkingWebsite(prospect))
  else if (filterWebsite.value === 'no')
    list = list.filter((prospect: Prospect): boolean => !ProspectWebsite.hasWorkingWebsite(prospect))
  return list
})

/** Trade guiding the template recommendation: targeted métier, or the first selected prospect's category. */
const recommendedTrade: ComputedRef<string | null> = computed((): string | null => {
  if (form.value.mode === 'full_auto') {
    const firstTrade: string = (form.value.metiers.split(',')[0] ?? '').trim()
    return firstTrade || null
  }
  const firstSelectedId: string | undefined = selectedProspectIds.value[0]
  if (!firstSelectedId) return null
  const prospect: Prospect | undefined = prospects.value.find(
    (candidate: Prospect): boolean => String(candidate.id) === firstSelectedId,
  )
  return prospect?.category ?? null
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

/** The cadence that will actually apply, read from the user's send policy. */
const sendPolicySummary: ComputedRef<string> = computed((): string => formatSendPolicySummary(sendPolicy.value))

/** Prospects picked in step 1, resolved to their full record. */
const selectedProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  const picked: Set<string> = new Set<string>(selectedProspectIds.value)
  return prospects.value.filter((prospect: Prospect): boolean => picked.has(String(prospect.id)))
})

/** The targeted prospects, named — truncated once the list gets long. */
const targetDetail: ComputedRef<string> = computed((): string => {
  if (form.value.mode === 'full_auto') return 'La machine pioche elle-même dans vos prospects non-utilisés.'
  const names: string[] = selectedProspects.value.map((prospect: Prospect): string => prospect.name)
  if (names.length === 0) return ''
  if (names.length <= NAMED_PROSPECTS_IN_RECAP) return names.join(', ')
  const shown: string[] = names.slice(0, NAMED_PROSPECTS_IN_RECAP)
  return `${shown.join(', ')} et ${names.length - shown.length} autre(s)`
})

/**
 * Name of an email template picked in step 3.
 * @param templateId - Identifier held by the form, 0 when none is picked.
 * @returns The template name, or an empty string.
 */
function emailTemplateName(templateId: number): string {
  return emailTemplates.value.find((template: TemplateSelectOption): boolean => template.id === templateId)?.name ?? ''
}

/** The A/B templates actually chosen, spelled out. */
const outreachDetail: ComputedRef<string> = computed((): string => {
  if (!form.value.autoCampaign) return 'Aucun email ne partira — les sites sont générés puis la machine s’arrête.'
  const names: string[] = [emailTemplateName(form.value.emailA), emailTemplateName(form.value.emailB)].filter(Boolean)
  return names.length > 1 ? `A : ${names[0]} · B : ${names[1]}` : (names[0] ?? '')
})

const recapItems: ComputedRef<AutomationRecapRow[]> = computed((): AutomationRecapRow[] => {
  const rows: AutomationRecapRow[] = [
    {
      label: 'Nom',
      value: resolvedName(),
      icon: 'i-lucide-tag',
      detail: form.value.name.trim() ? undefined : 'Nom généré automatiquement.',
    },
    {
      label: 'Cible',
      value:
        form.value.mode === 'full_auto'
          ? `${form.value.metiers || '—'} · ${form.value.villes || '—'}`
          : `${selectedProspectIds.value.length} prospect(s)`,
      icon: 'i-lucide-users',
      detail: targetDetail.value,
    },
    {
      label: 'Mode',
      value: form.value.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto',
      icon: form.value.mode === 'full_auto' ? 'i-lucide-bot' : 'i-lucide-hand',
      detail:
        form.value.mode === 'full_auto'
          ? `Objectif de ${form.value.targetDays} jours de démarchage.`
          : 'Vous validez avant tout envoi.',
    },
    {
      label: 'Site',
      value: selectedTemplateName.value,
      icon: 'i-lucide-app-window',
      detail: 'Modifiable prospect par prospect à la validation.',
    },
  ]

  if (!isSiteMode.value) {
    rows.push({
      label: 'Démarchage',
      value: form.value.autoCampaign ? (form.value.emailB ? 'Test A/B' : 'Modèle unique') : 'Sites seuls',
      icon: 'i-lucide-send',
      detail: outreachDetail.value,
    })
    rows.push({
      label: 'Cadence',
      value: sendPolicySummary.value,
      icon: 'i-lucide-timer',
      detail: 'Réglable dans vos paramètres d’envoi.',
    })
  }

  return rows
})

/** Whether the current step can advance. */
const canContinue: ComputedRef<boolean> = computed((): boolean => {
  if (activeStepKey.value === 'target') {
    if (form.value.mode === 'semi_auto') return selectedProspectIds.value.length > 0
    return Boolean(form.value.metiers.trim() && form.value.villes.trim() && form.value.targetDays > 0)
  }
  if (activeStepKey.value === 'emails' && form.value.autoCampaign) return form.value.emailA > 0
  return true
})

/** Whether the tunnel holds enough choices to be worth warning about before leaving. */
const hasMeaningfulDraft: ComputedRef<boolean> = computed(
  (): boolean =>
    currentStep.value > 1 ||
    selectedProspectIds.value.length > 0 ||
    Boolean(form.value.name.trim() || form.value.metiers.trim() || form.value.villes.trim()),
)

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
  scrollToTop()
}

/** Persist the tunnel state so leaving the page never loses the configuration. */
function saveDraft(): void {
  if (!import.meta.client) return
  const draft: AutomationDraft = {
    form: form.value,
    selectedProspectIds: selectedProspectIds.value,
    currentStep: currentStep.value,
    hasPickedTemplate: hasPickedTemplate.value,
  }
  try {
    sessionStorage.setItem(TUNNEL_DRAFT_STORAGE_KEY, JSON.stringify(draft))
  } catch {
    // Quota plein ou storage indisponible : la sauvegarde est best-effort.
  }
}

/** Restore a draft left by a previous visit, if any. */
function restoreDraft(): void {
  if (!import.meta.client) return
  try {
    const raw: string | null = sessionStorage.getItem(TUNNEL_DRAFT_STORAGE_KEY)
    if (!raw) return
    const draft: AutomationDraft = JSON.parse(raw) as AutomationDraft
    form.value = draft.form
    selectedProspectIds.value = draft.selectedProspectIds
    currentStep.value = draft.currentStep
    hasPickedTemplate.value = draft.hasPickedTemplate
  } catch {
    // Brouillon illisible : on repart d'un tunnel vierge.
  }
}

/** Drop the saved draft — the tunnel was launched, or explicitly abandoned. */
function clearDraft(): void {
  if (import.meta.client) sessionStorage.removeItem(TUNNEL_DRAFT_STORAGE_KEY)
}

/** Leave the tunnel, asking first once the configuration holds real choices. */
function leaveTunnel(): void {
  if (hasMeaningfulDraft.value) {
    leaveConfirmModal.value?.open()
    return
  }
  void navigateTo(originLink.value.to)
}

/** Confirmed exit: forget the draft and go back to the origin section. */
function discardDraftAndLeave(): void {
  clearDraft()
  void navigateTo(originLink.value.to)
}

/**
 * Apply the user's template choice and stop defaulting to the recommended one.
 * @param templateId - Identifier of the template picked in the list.
 */
function selectTemplate(templateId: string): void {
  hasPickedTemplate.value = true
  form.value.templateId = templateId
}

/**
 * Preselect the first template recommended for the targeted trade, until the user picks one.
 */
function applyRecommendedTemplate(): void {
  if (hasPickedTemplate.value || templates.value.length === 0) return
  const best: DemoSiteTemplate | undefined = sortTemplatesByRecommendation(templates.value, recommendedTrade.value)[0]
  if (!best || best.id === form.value.templateId) return
  form.value.templateId = best.id
  form.value.theme = { ...best.default_theme }
}

/** Reset the filters. */
function clearFilters(): void {
  searchQuery.value = ''
  filterCity.value = ''
  filterCategory.value = ''
  filterWebsite.value = 'all'
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
 * Open the prospect drawer straight on its edit form.
 * @param prospect - The prospect to edit.
 */
function openProspectEditDrawer(prospect: Prospect): void {
  drawerStack.push({ kind: 'prospect', prospect, startInEdit: true })
}

/**
 * Delete a prospect from the pool.
 * @param prospect - The prospect to delete.
 * @returns A promise resolved once deleted.
 */
async function handleDeleteProspect(prospect: Prospect): Promise<void> {
  try {
    await ProspectsService.deleteProspect(prospect.id)
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
 * The automatisation name — the typed one, or a sensible default when left blank.
 * @returns A non-empty name.
 */
function resolvedName(): string {
  const typed: string = form.value.name.trim()
  if (typed) return typed
  if (form.value.mode === 'full_auto') {
    const metier: string = splitList(form.value.metiers)[0] ?? 'Prospection'
    const ville: string = splitList(form.value.villes)[0] ?? ''
    return ville ? `${metier} — ${ville}` : metier
  }
  return `Sélection — ${selectedProspectIds.value.length} prospect(s)`
}

/**
 * Site mode: generate the demo sites directly (no automation), then land on the site (a single one)
 * or the demo-sites list (several). Uses the prospects' stored enrichment — enrich them beforehand.
 */
async function launchSites(): Promise<void> {
  const result: BulkGenerateResult = await DemoSiteService.createDemoSitesBulk({
    prospect_ids: selectedProspectIds.value.map((id: string): number => Number(id)),
    template_id: form.value.templateId || 'artisan-edito',
    theme: form.value.theme,
  })
  clearDraft()
  const createdIds: number[] = result.results
    .map((item: BulkGenerateItemResult): number | undefined => item.demo_site_id)
    .filter((id: number | undefined): id is number => typeof id === 'number')
  if (result.skipped_no_email.length > 0 || result.failed > 0) {
    toast.info(
      `${result.created} site(s) créé(s) · ${result.skipped_no_email.length} sans email · ${result.failed} échec(s)`,
    )
  } else {
    toast.success(result.created > 1 ? `${result.created} sites démo générés` : 'Site démo généré')
  }
  await navigateTo(createdIds.length === 1 ? `/dashboard/demo-sites/${createdIds[0]}` : '/dashboard/demo-sites')
}

/**
 * Create the automatisation — or, in site mode, generate the sites — then navigate to the result.
 * @returns A promise resolved once created.
 */
async function launch(): Promise<void> {
  isCreating.value = true
  try {
    if (isSiteMode.value) {
      await launchSites()
      return
    }
    const detail: AutomationDetail = await AutomationsService.createAutomation({
      name: resolvedName(),
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
      follow_ups:
        form.value.autoCampaign && form.value.autoFollowUp && form.value.followUpTemplate
          ? [{ template_id: form.value.followUpTemplate }]
          : [],
    })
    clearDraft()
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

/** Open the prospect-search drawer (scraping) without leaving the tunnel. */
function openSearchDrawer(): void {
  drawerStack.push({ kind: 'search-prospects' })
}

/** Open the send-policy drawer without leaving the tunnel. */
function openSendPolicyDrawer(): void {
  drawerStack.push({ kind: 'send-policy' })
}

/**
 * Reload the email templates feeding the A/B selectors.
 * @returns A promise resolved once the templates are reloaded.
 */
async function reloadEmailTemplates(): Promise<void> {
  const emailList: EmailTemplate[] = await EmailTemplatesService.getEmailTemplates()
  emailTemplates.value = emailList.map(
    (t: EmailTemplate): TemplateSelectOption => ({ id: t.id, name: t.name, subject: t.subject }),
  )
}

/**
 * Reload the selectable prospects (unused only), preserving the selection.
 * @returns A promise resolved once reloaded.
 */
async function reloadProspects(): Promise<void> {
  isLoadingProspects.value = true
  try {
    const [prospectList, usedIds]: [Prospect[], number[]] = await Promise.all([
      ProspectsService.listProspects(),
      AutomationsService.getUsedProspectIds(),
    ])
    const used: Set<number> = new Set<number>(usedIds)
    prospects.value = prospectList.filter((p: Prospect): boolean => !used.has(p.id))
  } catch {
    // Non-critical.
  } finally {
    isLoadingProspects.value = false
  }
}

// A search launched from the « Chercher plus » drawer just finished — refresh.
watch(
  (): number => searchStore.completedSignal,
  (): void => {
    void reloadProspects()
  },
)

// The trade is only known once prospects load, well after the templates.
watch([templates, recommendedTrade], applyRecommendedTemplate)

watch([form, selectedProspectIds, currentStep], saveDraft, { deep: true })

onMounted(async (): Promise<void> => {
  restoreDraft()
  // Après restauration : le brouillon peut venir de l'autre mode, qui a un email et une étape de plus.
  if (isSiteMode.value) form.value.autoCampaign = false
  currentStep.value = Math.min(currentStep.value, steps.value.length)

  try {
    const [, demoList]: [unknown, DemoSiteTemplate[]] = await Promise.all([
      reloadEmailTemplates(),
      DemoSiteService.listDemoSiteTemplates(),
    ])
    templates.value = demoList
  } catch {
    // Non-critical — the wizard still works with what loaded.
  }
  try {
    sendPolicy.value = await SendPolicyService.getSendPolicy()
  } catch {
    // Non-critical — the recap falls back to a generic cadence label.
  }
  await reloadProspects()

  // Pre-select the prospect(s) passed via ?prospect= (one or several, for the site-generation tunnel).
  const rawProspects: Array<LocationQueryValue | undefined> = Array.isArray(route.query.prospect)
    ? route.query.prospect
    : [route.query.prospect]
  const preselected: string[] = rawProspects.filter(
    (value: LocationQueryValue | undefined): value is string =>
      typeof value === 'string' && value.length > 0 && !Number.isNaN(Number(value)),
  )
  if (preselected.length) {
    selectedProspectIds.value = preselected
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
/* Révélation en cascade du récapitulatif, calée après l'éclat du hero. */
.recap-reveal {
  animation: recap-reveal-in 0.34s cubic-bezier(0.16, 1, 0.3, 1) backwards;
  animation-delay: calc(0.72s + var(--recap-order) * 70ms);
}
@keyframes recap-reveal-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wizard-step,
  .recap-reveal {
    animation: none;
  }
}
</style>
