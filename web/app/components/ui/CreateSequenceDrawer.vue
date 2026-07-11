<template>
  <Teleport to="body">
    <!-- Non-modal drawer: navigation stays possible; close with X / Échap. -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[540px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
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
            <UIcon name="i-lucide-workflow" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Nouvelle séquence</h2>
            <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">
              Enrichir → générer les sites → valider → démarcher, en une passe
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <form
          id="create-sequence-form"
          class="flex-1 space-y-6 overflow-y-auto px-5 py-4"
          @submit.prevent="handleCreate"
        >
          <!-- Nom -->
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="sequence-name">Nom de la séquence</label>
            <input
              id="sequence-name"
              v-model="form.name"
              type="text"
              required
              minlength="2"
              placeholder="Ex : Plombiers Lyon — juillet"
              class="input-field"
            />
          </div>

          <!-- Prospects -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Prospects</p>
              <span class="text-[11px] text-[var(--app-ink-soft)]">{{ selectedIds.size }} sélectionné(s)</span>
            </div>

            <div class="relative">
              <UIcon
                name="i-lucide-search"
                class="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
              />
              <input
                v-model="prospectSearch"
                type="text"
                placeholder="Filtrer par nom ou ville…"
                class="input-field pl-8"
              />
            </div>

            <div class="flex items-center gap-3 text-[11px]">
              <button
                type="button"
                class="text-[var(--app-ink-soft)] underline-offset-2 hover:text-[var(--app-ink)] hover:underline"
                @click="selectAllFiltered"
              >
                Tout sélectionner ({{ filteredProspects.length }})
              </button>
              <button
                type="button"
                class="text-[var(--app-ink-soft)] underline-offset-2 hover:text-[var(--app-ink)] hover:underline"
                @click="clearSelection"
              >
                Vider
              </button>
            </div>

            <div class="max-h-56 overflow-y-auto rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-1">
              <p v-if="isLoadingProspects" class="flex items-center gap-2 px-2 py-6 text-xs text-[var(--app-ink-soft)]">
                <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                Chargement des prospects…
              </p>
              <p
                v-else-if="filteredProspects.length === 0"
                class="px-2 py-6 text-center text-xs text-[var(--app-faint)]"
              >
                Aucun prospect ne correspond.
              </p>
              <button
                v-for="prospect in filteredProspects"
                v-else
                :key="prospect.id"
                type="button"
                class="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-[var(--app-surface-2)]"
                @click="toggleProspect(prospect.id)"
              >
                <span
                  class="flex h-4 w-4 shrink-0 items-center justify-center rounded border"
                  :class="
                    selectedIds.has(prospect.id)
                      ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
                      : 'border-[var(--app-line)]'
                  "
                >
                  <UIcon v-if="selectedIds.has(prospect.id)" name="i-lucide-check" class="h-3 w-3" />
                </span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-xs font-medium text-[var(--app-ink)]">{{ prospect.name }}</span>
                  <span class="block truncate text-[10px] text-[var(--app-ink-soft)]">
                    {{ prospect.city || '—' }}
                  </span>
                </span>
                <span
                  v-if="prospect.website"
                  class="shrink-0 rounded-full bg-[var(--app-surface-2)] px-1.5 py-0.5 text-[9px] text-[var(--app-faint)]"
                  title="A déjà un site web"
                >
                  site existant
                </span>
                <UIcon
                  v-if="!prospect.email"
                  name="i-lucide-mail-x"
                  class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                  title="Pas d'email — ne pourra pas être démarché"
                />
              </button>
            </div>
          </div>

          <!-- Mode -->
          <div class="space-y-2">
            <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Mode</p>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                class="rounded-lg border p-3 text-left transition-colors"
                :class="modeCardClass('semi_auto')"
                @click="form.mode = 'semi_auto'"
              >
                <span class="block text-xs font-semibold text-[var(--app-ink)]">Semi-auto</span>
                <span class="mt-0.5 block text-[10px] text-[var(--app-ink-soft)]">
                  Pause pour valider les sites avant de démarcher
                </span>
              </button>
              <button
                type="button"
                class="rounded-lg border p-3 text-left transition-colors"
                :class="modeCardClass('full_auto')"
                @click="form.mode = 'full_auto'"
              >
                <span class="block text-xs font-semibold text-[var(--app-ink)]">Full-auto</span>
                <span class="mt-0.5 block text-[10px] text-[var(--app-ink-soft)]">
                  Démarche sans validation — volume, confiance établie
                </span>
              </button>
            </div>
          </div>

          <!-- Étapes -->
          <div class="space-y-3">
            <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Étapes automatiques</p>

            <!-- Enrichir -->
            <label class="flex cursor-pointer items-start gap-2.5">
              <input v-model="form.autoEnrich" type="checkbox" class="mt-0.5 accent-[var(--app-ink)]" />
              <span class="min-w-0 flex-1">
                <span class="block text-xs font-medium text-[var(--app-ink)]">Enrichir</span>
                <span class="block text-[10px] text-[var(--app-ink-soft)]"
                  >Photos, avis, horaires… avant de générer</span
                >
              </span>
            </label>

            <!-- Générer -->
            <label class="flex cursor-pointer items-start gap-2.5">
              <input v-model="form.autoGenerate" type="checkbox" class="mt-0.5 accent-[var(--app-ink)]" />
              <span class="min-w-0 flex-1">
                <span class="block text-xs font-medium text-[var(--app-ink)]">Générer les sites</span>
                <span class="block text-[10px] text-[var(--app-ink-soft)]">Une démo par prospect</span>
              </span>
            </label>
            <div v-if="form.autoGenerate" class="pl-6">
              <label class="text-muted mb-1 block text-[10px]" for="sequence-template">Template de site</label>
              <select id="sequence-template" v-model="form.templateId" class="input-field text-xs">
                <option :value="null">Template par défaut</option>
                <option v-for="tpl in demoTemplates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
              </select>
            </div>

            <!-- Démarcher -->
            <label class="flex cursor-pointer items-start gap-2.5">
              <input v-model="form.autoCampaign" type="checkbox" class="mt-0.5 accent-[var(--app-ink)]" />
              <span class="min-w-0 flex-1">
                <span class="block text-xs font-medium text-[var(--app-ink)]">Démarcher (cold email)</span>
                <span class="block text-[10px] text-[var(--app-ink-soft)]">Campagne A/B + relances throttlées</span>
              </span>
            </label>
            <div v-if="form.autoCampaign" class="space-y-3 pl-6">
              <div>
                <label class="text-muted mb-1 block text-[10px]">Modèle A — envoi initial</label>
                <UiTemplateSelect
                  :model-value="form.emailTemplateIdA"
                  :templates="emailTemplateOptions"
                  @update:model-value="form.emailTemplateIdA = $event"
                />
              </div>
              <div>
                <label class="text-muted mb-1 block text-[10px]">Modèle B — test A/B (optionnel)</label>
                <UiTemplateSelect
                  :model-value="form.emailTemplateIdB"
                  :templates="emailTemplateOptions"
                  @update:model-value="form.emailTemplateIdB = $event"
                />
              </div>
              <div>
                <label class="text-muted mb-1 block text-[10px]" for="sequence-delay">
                  Délai entre 2 envois (min)
                </label>
                <input
                  id="sequence-delay"
                  v-model.number="form.sendDelayMinutes"
                  type="number"
                  min="1"
                  max="1440"
                  class="input-field text-xs"
                />
              </div>
            </div>
          </div>

          <!-- Garde-fous -->
          <div class="space-y-3">
            <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Garde-fous (optionnel)</p>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-muted mb-1 block text-[10px]" for="sequence-max-credits">Crédits max</label>
                <input
                  id="sequence-max-credits"
                  v-model.number="form.maxCredits"
                  type="number"
                  min="0"
                  placeholder="illimité"
                  class="input-field text-xs"
                />
              </div>
              <div>
                <label class="text-muted mb-1 block text-[10px]" for="sequence-daily-cap">Emails / jour max</label>
                <input
                  id="sequence-daily-cap"
                  v-model.number="form.dailyEmailCap"
                  type="number"
                  min="1"
                  placeholder="illimité"
                  class="input-field text-xs"
                />
              </div>
            </div>
          </div>
        </form>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isCreating" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="create-sequence-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isCreating || selectedIds.size === 0"
          >
            <UIcon v-if="isCreating" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isCreating ? 'Lancement…' : `Lancer la séquence (${selectedIds.size})` }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { CreateSequenceDrawerProps } from '~/types/CreateSequenceDrawer'
import type { SequenceDetail, SequenceMode } from '~/types/AcquisitionSequence'
import type { Prospect } from '~/types'
import type { TemplateSelectOption } from '~/types/TemplateSelect'
import type { DemoSiteTemplate } from '~/services/demoSiteService'
import { createSequence } from '~/services/acquisitionSequencesService'
import { listProspects } from '~/services/prospectsService'
import { getEmailTemplates } from '~/services/emailTemplatesService'
import { listDemoSiteTemplates } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

/** Local shape of the create-sequence form. */
interface CreateSequenceForm {
  name: string
  mode: SequenceMode
  autoEnrich: boolean
  autoGenerate: boolean
  templateId: string | null
  autoCampaign: boolean
  emailTemplateIdA: number
  emailTemplateIdB: number
  sendDelayMinutes: number
  maxCredits: number | null
  dailyEmailCap: number | null
}

/**
 * Defines the component props.
 */
const props: CreateSequenceDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  prospectIds: {
    type: Array as PropType<number[]>,
    default: (): number[] => [],
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
  /** A sequence was created and started. */
  created: [sequence: SequenceDetail]
}>()

const toast = useToast()

/** Whether the create request is in flight. */
const isCreating: Ref<boolean> = ref<boolean>(false)
/** Whether the prospect list is loading. */
const isLoadingProspects: Ref<boolean> = ref<boolean>(false)
/** The user's prospects (selection source). */
const prospects: Ref<Prospect[]> = ref<Prospect[]>([])
/** Available email templates. */
const emailTemplates: Ref<TemplateSelectOption[]> = ref<TemplateSelectOption[]>([])
/** Available demo-site templates. */
const demoTemplates: Ref<DemoSiteTemplate[]> = ref<DemoSiteTemplate[]>([])
/** Free-text prospect filter. */
const prospectSearch: Ref<string> = ref<string>('')
/** Currently selected prospect ids. */
const selectedIds: Ref<Set<number>> = ref<Set<number>>(new Set<number>())

/** Sequence configuration form state. */
const form: Ref<CreateSequenceForm> = ref<CreateSequenceForm>({
  name: '',
  mode: 'semi_auto',
  autoEnrich: true,
  autoGenerate: true,
  templateId: null,
  autoCampaign: true,
  emailTemplateIdA: 0,
  emailTemplateIdB: 0,
  sendDelayMinutes: 20,
  maxCredits: null,
  dailyEmailCap: null,
})

/** Email templates mapped for the A/B selectors. */
const emailTemplateOptions: ComputedRef<TemplateSelectOption[]> = computed(
  (): TemplateSelectOption[] => emailTemplates.value,
)

/** Prospects matching the current search filter. */
const filteredProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  const needle: string = prospectSearch.value.trim().toLowerCase()
  if (!needle) return prospects.value
  return prospects.value.filter(
    (p: Prospect): boolean => p.name.toLowerCase().includes(needle) || (p.city ?? '').toLowerCase().includes(needle),
  )
})

/**
 * Resolve the CSS class of a mode card based on the selected mode.
 * @param mode - The mode this card represents.
 * @returns The border/background classes.
 */
function modeCardClass(mode: SequenceMode): string {
  return form.value.mode === mode
    ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
    : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]'
}

/**
 * Toggle a prospect in the selection.
 * @param id - Prospect id to toggle.
 */
function toggleProspect(id: number): void {
  const next: Set<number> = new Set<number>(selectedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedIds.value = next
}

/** Select every prospect currently matching the filter. */
function selectAllFiltered(): void {
  const next: Set<number> = new Set<number>(selectedIds.value)
  filteredProspects.value.forEach((p: Prospect): void => {
    next.add(p.id)
  })
  selectedIds.value = next
}

/** Clear the whole selection. */
function clearSelection(): void {
  selectedIds.value = new Set<number>()
}

/**
 * Load prospects, email templates and demo templates in parallel.
 * @returns A promise resolved once loaded.
 */
async function loadData(): Promise<void> {
  isLoadingProspects.value = true
  try {
    const [prospectList, emailList, demoList] = await Promise.all([
      listProspects(),
      getEmailTemplates(),
      listDemoSiteTemplates(),
    ])
    prospects.value = prospectList
    emailTemplates.value = emailList.map((t): TemplateSelectOption => ({ id: t.id, name: t.name, subject: t.subject }))
    demoTemplates.value = demoList
  } catch {
    // Non-critical — the lists stay empty and the form still submits.
  } finally {
    isLoadingProspects.value = false
  }
}

/** Reset the form to its defaults, pre-selecting the incoming prospect ids. */
function resetForm(): void {
  form.value = {
    name: '',
    mode: 'semi_auto',
    autoEnrich: true,
    autoGenerate: true,
    templateId: null,
    autoCampaign: true,
    emailTemplateIdA: 0,
    emailTemplateIdB: 0,
    sendDelayMinutes: 20,
    maxCredits: null,
    dailyEmailCap: null,
  }
  prospectSearch.value = ''
  selectedIds.value = new Set<number>(props.prospectIds)
}

/**
 * Create the sequence then emit it up and close.
 * @returns A promise resolved once the sequence is created.
 */
async function handleCreate(): Promise<void> {
  if (selectedIds.value.size === 0) return
  isCreating.value = true
  try {
    const detail: SequenceDetail = await createSequence({
      name: form.value.name.trim(),
      prospect_ids: Array.from(selectedIds.value),
      mode: form.value.mode,
      auto_enrich: form.value.autoEnrich,
      auto_generate: form.value.autoGenerate,
      template_id: form.value.templateId,
      auto_campaign: form.value.autoCampaign,
      email_template_id_a: form.value.emailTemplateIdA || null,
      email_template_id_b: form.value.emailTemplateIdB || null,
      send_delay_minutes: form.value.sendDelayMinutes,
      follow_ups: [],
      max_credits: form.value.maxCredits,
      daily_email_cap: form.value.dailyEmailCap,
    })
    toast.success('Séquence lancée')
    emit('created', detail)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du lancement de la séquence')
  } finally {
    isCreating.value = false
  }
}

// Reset + reload each time the drawer opens.
watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) {
      resetForm()
      void loadData()
    }
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
