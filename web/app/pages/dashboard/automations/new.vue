<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <!-- Header + stepper -->
    <div>
      <NuxtLink
        to="/dashboard/automations"
        class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Automatisations
      </NuxtLink>
      <h1 class="app-page-title mt-3">Créer une automatisation</h1>
      <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
        Trouver → générer les sites → {{ form.mode === 'semi_auto' ? 'valider' : '(auto)' }} → démarcher.
      </p>

      <ol class="mt-5 flex flex-wrap items-center gap-2 text-xs">
        <li v-for="(label, index) in stepLabels" :key="label" class="flex items-center gap-2">
          <span
            class="flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-semibold"
            :class="
              index === step
                ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
                : index < step
                  ? 'border-[var(--app-green)] bg-[var(--app-green-soft)] text-[var(--app-green)]'
                  : 'border-[var(--app-line)] text-[var(--app-ink-soft)]'
            "
          >
            <UIcon v-if="index < step" name="i-lucide-check" class="h-3 w-3" />
            <template v-else>{{ index + 1 }}</template>
          </span>
          <span :class="index === step ? 'font-semibold text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)]'">
            {{ label }}
          </span>
          <UIcon
            v-if="index < stepLabels.length - 1"
            name="i-lucide-chevron-right"
            class="h-3 w-3 text-[var(--app-faint)]"
          />
        </li>
      </ol>
    </div>

    <!-- ═══════════════ Step 0 · Cible ═══════════════ -->
    <div v-if="step === 0" class="card space-y-5">
      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium" for="auto-name">Nom de l'automatisation</label>
        <input
          id="auto-name"
          v-model="form.name"
          type="text"
          placeholder="Ex : Plombiers — Rennes"
          class="input-field"
        />
      </div>

      <!-- Mode -->
      <div class="grid grid-cols-2 gap-2">
        <button
          type="button"
          class="rounded-lg border p-3 text-left transition-colors"
          :class="modeCardClass('semi_auto')"
          @click="form.mode = 'semi_auto'"
        >
          <span class="block text-xs font-semibold text-[var(--app-ink)]">Semi-auto</span>
          <span class="mt-0.5 block text-[10px] text-[var(--app-ink-soft)]"
            >Tu valides les sites avant le démarchage</span
          >
        </button>
        <button
          type="button"
          class="rounded-lg border p-3 text-left transition-colors"
          :class="modeCardClass('full_auto')"
          @click="form.mode = 'full_auto'"
        >
          <span class="block text-xs font-semibold text-[var(--app-ink)]">Full-auto</span>
          <span class="mt-0.5 block text-[10px] text-[var(--app-ink-soft)]"
            >Métier + ville + jours → la machine fait tout</span
          >
        </button>
      </div>

      <!-- Semi-auto: prospect picker -->
      <div v-if="form.mode === 'semi_auto'" class="space-y-2">
        <div class="flex items-center justify-between">
          <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Prospects</p>
          <span class="text-[11px] text-[var(--app-ink-soft)]">{{ form.prospectIds.size }} sélectionné(s)</span>
        </div>
        <input v-model="prospectSearch" type="text" placeholder="Filtrer par nom ou ville…" class="input-field" />
        <div class="flex items-center gap-3 text-[11px]">
          <button
            type="button"
            class="text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] hover:underline"
            @click="selectAllFiltered"
          >
            Tout sélectionner ({{ filteredProspects.length }})
          </button>
          <button
            type="button"
            class="text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] hover:underline"
            @click="clearProspects"
          >
            Vider
          </button>
        </div>
        <div class="max-h-64 overflow-y-auto rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-1">
          <p v-if="isLoadingProspects" class="flex items-center gap-2 px-2 py-6 text-xs text-[var(--app-ink-soft)]">
            <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" /> Chargement…
          </p>
          <p v-else-if="filteredProspects.length === 0" class="px-2 py-6 text-center text-xs text-[var(--app-faint)]">
            Aucun prospect disponible (les prospects déjà pris par une automatisation sont masqués).
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
                form.prospectIds.has(prospect.id)
                  ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
                  : 'border-[var(--app-line)]'
              "
            >
              <UIcon v-if="form.prospectIds.has(prospect.id)" name="i-lucide-check" class="h-3 w-3" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-xs font-medium text-[var(--app-ink)]">{{ prospect.name }}</span>
              <span class="block truncate text-[10px] text-[var(--app-ink-soft)]">{{ prospect.city || '—' }}</span>
            </span>
            <span
              v-if="prospect.website"
              class="shrink-0 rounded-full bg-[var(--app-surface-2)] px-1.5 py-0.5 text-[9px] text-[var(--app-faint)]"
              >site existant</span
            >
            <UIcon
              v-if="!prospect.email"
              name="i-lucide-mail-x"
              class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
              title="Pas d'email"
            />
          </button>
        </div>
      </div>

      <!-- Full-auto: query -->
      <div v-else class="space-y-3">
        <div>
          <label class="text-muted mb-1 block text-[11px] font-medium" for="auto-metiers">Métier(s)</label>
          <input
            id="auto-metiers"
            v-model="form.metiers"
            type="text"
            placeholder="plombier, électricien…"
            class="input-field"
          />
        </div>
        <div>
          <label class="text-muted mb-1 block text-[11px] font-medium" for="auto-villes">Ville(s)</label>
          <input
            id="auto-villes"
            v-model="form.villes"
            type="text"
            placeholder="Rennes, Iffendic…"
            class="input-field"
          />
        </div>
        <div class="flex items-end gap-3">
          <div class="flex-1">
            <label class="text-muted mb-1 block text-[11px] font-medium" for="auto-days"
              >Objectif (jours de démarchage)</label
            >
            <input id="auto-days" v-model.number="form.targetDays" type="number" min="1" max="90" class="input-field" />
          </div>
          <label class="flex cursor-pointer items-center gap-2 pb-2 text-[11px] text-[var(--app-ink-soft)]">
            <input v-model="form.onlyWithoutWebsite" type="checkbox" class="accent-[var(--app-ink)]" />
            Sans site web
          </label>
        </div>
        <p
          class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2 text-[11px] text-[var(--app-ink-soft)]"
        >
          <UIcon name="i-lucide-info" class="mr-1 inline h-3 w-3" />
          Pioche dans tes prospects non-utilisés correspondants. S'il en manque, elle te préviendra de lancer une
          recherche.
        </p>
      </div>
    </div>

    <!-- ═══════════════ Step 1 · Site ═══════════════ -->
    <div v-else-if="step === 1" class="card space-y-4">
      <div>
        <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Template de site</p>
        <p class="mt-1 mb-2 text-[11px] text-[var(--app-ink-soft)]">
          Appliqué à tous les prospects — tu pourras en changer par prospect ensuite.
        </p>
        <select v-model="form.templateId" class="input-field">
          <option :value="null">Template par défaut</option>
          <option v-for="tpl in demoTemplates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
        </select>
      </div>
      <div v-if="selectedTemplate" class="overflow-hidden rounded-lg border border-[var(--app-line)]">
        <DemoSitesDemoSitePreviewFrame :template-id="selectedTemplate.id" business-name="Aperçu" />
      </div>
    </div>

    <!-- ═══════════════ Step 2 · Emails ═══════════════ -->
    <div v-else-if="step === 2" class="card space-y-4">
      <label class="flex cursor-pointer items-start gap-2.5">
        <input v-model="form.autoCampaign" type="checkbox" class="mt-0.5 accent-[var(--app-ink)]" />
        <span>
          <span class="block text-xs font-medium text-[var(--app-ink)]">Démarcher les prospects par email</span>
          <span class="block text-[10px] text-[var(--app-ink-soft)]"
            >Décoche pour seulement générer les sites (sans envoi).</span
          >
        </span>
      </label>

      <div v-if="form.autoCampaign" class="space-y-3">
        <div>
          <label class="text-muted mb-1 block text-[10px]">Modèle A — envoi initial</label>
          <UiTemplateSelect
            :model-value="form.emailA"
            :templates="emailTemplates"
            @update:model-value="form.emailA = $event"
          />
        </div>
        <div>
          <label class="text-muted mb-1 block text-[10px]">Modèle B — test A/B (optionnel)</label>
          <UiTemplateSelect
            :model-value="form.emailB"
            :templates="emailTemplates"
            @update:model-value="form.emailB = $event"
          />
        </div>
        <p class="text-[11px] text-[var(--app-ink-soft)]">
          <UIcon name="i-lucide-clock" class="mr-1 inline h-3 w-3" />
          La cadence d'envoi suit tes
          <NuxtLink to="/dashboard/settings/sending" class="underline hover:text-[var(--app-ink)]"
            >réglages d'envoi</NuxtLink
          >.
        </p>
      </div>
    </div>

    <!-- ═══════════════ Step 3 · Récap ═══════════════ -->
    <div v-else class="card space-y-3">
      <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Récapitulatif</p>
      <dl class="space-y-2 text-sm">
        <div class="flex justify-between gap-4">
          <dt class="text-[var(--app-ink-soft)]">Nom</dt>
          <dd class="font-medium text-[var(--app-ink)]">{{ form.name || '—' }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-[var(--app-ink-soft)]">Mode</dt>
          <dd class="font-medium text-[var(--app-ink)]">{{ form.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto' }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-[var(--app-ink-soft)]">Cible</dt>
          <dd class="text-right font-medium text-[var(--app-ink)]">{{ targetSummary }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-[var(--app-ink-soft)]">Template</dt>
          <dd class="font-medium text-[var(--app-ink)]">{{ selectedTemplate?.name ?? 'Par défaut' }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-[var(--app-ink-soft)]">Démarchage</dt>
          <dd class="font-medium text-[var(--app-ink)]">
            {{ form.autoCampaign ? (form.emailB ? 'A/B' : 'Modèle A') : 'Sites seuls' }}
          </dd>
        </div>
      </dl>
      <p
        v-if="form.mode === 'semi_auto'"
        class="rounded-lg border border-[var(--app-blue)] bg-[var(--app-blue-soft)] px-3 py-2 text-[11px] text-[var(--app-ink)]"
      >
        En semi-auto, la machine génère les sites puis <strong>s'arrête pour ta validation</strong> avant tout envoi.
      </p>
    </div>

    <!-- Footer nav -->
    <div class="flex items-center justify-between">
      <button v-if="step > 0" class="btn-secondary" :disabled="isCreating" @click="step -= 1">Précédent</button>
      <span v-else />
      <button v-if="step < stepLabels.length - 1" class="btn-primary" :disabled="!canNext" @click="step += 1">
        Suivant
      </button>
      <button v-else class="btn-primary disabled:opacity-50" :disabled="isCreating || !canNext" @click="launch">
        <UIcon v-if="isCreating" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
        {{ isCreating ? 'Lancement…' : 'Lancer l’automatisation' }}
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { AutomationMode } from '~/types/Automation'
import type { Prospect } from '~/types'
import type { TemplateSelectOption } from '~/types/TemplateSelect'
import type { DemoSiteTemplate } from '~/services/demoSiteService'
import { createAutomation, getUsedProspectIds } from '~/services/automationsService'
import { listProspects } from '~/services/prospectsService'
import { getEmailTemplates } from '~/services/emailTemplatesService'
import { listDemoSiteTemplates } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

/** Local wizard form. */
interface TunnelForm {
  name: string
  mode: AutomationMode
  prospectIds: Set<number>
  metiers: string
  villes: string
  targetDays: number
  onlyWithoutWebsite: boolean
  templateId: string | null
  autoCampaign: boolean
  emailA: number
  emailB: number
}

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()
const route = useRoute()

/** Current wizard step (0-based). */
const step: Ref<number> = ref<number>(0)
/** Whether the create request is in flight. */
const isCreating: Ref<boolean> = ref<boolean>(false)
/** Whether prospects are loading. */
const isLoadingProspects: Ref<boolean> = ref<boolean>(false)
/** The user's selectable prospects (unused only). */
const prospects: Ref<Prospect[]> = ref<Prospect[]>([])
/** Email templates for the A/B selectors. */
const emailTemplates: Ref<TemplateSelectOption[]> = ref<TemplateSelectOption[]>([])
/** Demo-site templates. */
const demoTemplates: Ref<DemoSiteTemplate[]> = ref<DemoSiteTemplate[]>([])
/** Free-text prospect filter. */
const prospectSearch: Ref<string> = ref<string>('')

/** Wizard state. */
const form: Ref<TunnelForm> = ref<TunnelForm>({
  name: '',
  mode: 'semi_auto',
  prospectIds: new Set<number>(),
  metiers: '',
  villes: '',
  targetDays: 10,
  onlyWithoutWebsite: true,
  templateId: null,
  autoCampaign: true,
  emailA: 0,
  emailB: 0,
})

/** Step labels. */
const stepLabels: ReadonlyArray<string> = ['Cible', 'Site', 'Emails', 'Lancer']

/** Prospects matching the current filter. */
const filteredProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  const needle: string = prospectSearch.value.trim().toLowerCase()
  if (!needle) return prospects.value
  return prospects.value.filter(
    (p: Prospect): boolean => p.name.toLowerCase().includes(needle) || (p.city ?? '').toLowerCase().includes(needle),
  )
})

/** The selected demo template object, if any. */
const selectedTemplate: ComputedRef<DemoSiteTemplate | null> = computed(
  (): DemoSiteTemplate | null =>
    demoTemplates.value.find((t: DemoSiteTemplate): boolean => t.id === form.value.templateId) ?? null,
)

/** Human summary of the target for the recap step. */
const targetSummary: ComputedRef<string> = computed((): string => {
  if (form.value.mode === 'full_auto') {
    const metiers: string = form.value.metiers.trim() || '—'
    const villes: string = form.value.villes.trim() || '—'
    return `${metiers} · ${villes} · ${form.value.targetDays} j`
  }
  return `${form.value.prospectIds.size} prospect(s)`
})

/** Whether the current step is complete enough to advance / launch. */
const canNext: ComputedRef<boolean> = computed((): boolean => {
  if (step.value === 0) {
    if (!form.value.name.trim()) return false
    if (form.value.mode === 'semi_auto') return form.value.prospectIds.size > 0
    return Boolean(form.value.metiers.trim() && form.value.villes.trim() && form.value.targetDays > 0)
  }
  if (step.value === 2 && form.value.autoCampaign) return form.value.emailA > 0
  return true
})

/**
 * CSS classes for a mode card.
 * @param mode - The mode this card represents.
 * @returns Border/background classes.
 */
function modeCardClass(mode: AutomationMode): string {
  return form.value.mode === mode
    ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
    : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]'
}

/**
 * Toggle a prospect in the selection.
 * @param id - Prospect id.
 */
function toggleProspect(id: number): void {
  const next: Set<number> = new Set<number>(form.value.prospectIds)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  form.value.prospectIds = next
}

/** Clear the whole prospect selection. */
function clearProspects(): void {
  form.value.prospectIds = new Set<number>()
}

/** Select every filtered prospect. */
function selectAllFiltered(): void {
  const next: Set<number> = new Set<number>(form.value.prospectIds)
  filteredProspects.value.forEach((p: Prospect): void => {
    next.add(p.id)
  })
  form.value.prospectIds = next
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
      prospect_ids: form.value.mode === 'semi_auto' ? Array.from(form.value.prospectIds) : [],
      search_metiers: form.value.mode === 'full_auto' ? splitList(form.value.metiers) : [],
      search_villes: form.value.mode === 'full_auto' ? splitList(form.value.villes) : [],
      target_days: form.value.mode === 'full_auto' ? form.value.targetDays : null,
      only_without_website: form.value.onlyWithoutWebsite,
      auto_enrich: true,
      auto_generate: true,
      template_id: form.value.templateId,
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

/**
 * Load prospects (excluding used), email templates and demo templates.
 * @returns A promise resolved once loaded.
 */
async function loadData(): Promise<void> {
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
    demoTemplates.value = demoList
  } catch {
    // Non-critical — the wizard still submits with what's available.
  } finally {
    isLoadingProspects.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadData()
  // Pre-select a prospect passed via ?prospect= (single-site shortcut).
  const raw: string | undefined = Array.isArray(route.query.prospect) ? route.query.prospect[0] : route.query.prospect
  const preselect: number = Number(raw)
  if (raw && !Number.isNaN(preselect)) {
    form.value.prospectIds = new Set<number>([preselect])
  }
})
</script>
