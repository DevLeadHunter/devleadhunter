<template>
  <div class="space-y-5">
    <NuxtLink
      to="/dashboard/automations"
      class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
    >
      <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
      Automatisations
    </NuxtLink>

    <div v-if="run === null" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-accent)]" />
    </div>

    <template v-else>
      <!-- Header -->
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <p class="app-label flex items-center gap-2">
            <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
            Automatisation · {{ run.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto' }}
          </p>
          <div class="mt-2 flex flex-wrap items-center gap-2.5">
            <h1 class="app-page-title">{{ run.name }}</h1>
            <span class="app-badge" :class="statusBadgeClass(run.status)">{{ statusLabel(run.status) }}</span>
          </div>
          <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
            {{ run.stats.total }} prospect(s)
            <span v-if="run.campaign_id">
              ·
              <NuxtLink
                :to="`/dashboard/campaigns/${run.campaign_id}`"
                class="underline underline-offset-2 hover:text-[var(--app-ink)]"
                >campagne liée</NuxtLink
              >
            </span>
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="run.status === 'running'"
            class="app-btn-secondary h-9 px-4 text-xs"
            :disabled="isActing"
            @click="run && store.pause(run.id)"
          >
            <UIcon name="i-lucide-pause" class="h-3.5 w-3.5" />Pause
          </button>
          <button
            v-if="run.status === 'paused'"
            class="app-btn-secondary h-9 px-4 text-xs"
            :disabled="isActing"
            @click="run && store.resume(run.id)"
          >
            <UIcon name="i-lucide-play" class="h-3.5 w-3.5" />Reprendre
          </button>
          <button v-if="canCancel" class="app-btn-secondary h-9 px-4 text-xs" :disabled="isActing" @click="cancel">
            Annuler
          </button>
          <button
            v-if="isTerminal"
            class="app-btn-secondary h-9 px-4 text-xs text-[var(--app-red)]"
            :disabled="isActing"
            @click="remove"
          >
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />Supprimer
          </button>
        </div>
      </div>

      <!-- KPIs -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div v-for="kpi in kpis" :key="kpi.label" class="app-card p-3.5">
          <p class="app-label">{{ kpi.label }}</p>
          <p class="mt-1 text-2xl font-bold tabular-nums" :class="kpi.class">{{ kpi.value }}</p>
        </div>
      </div>

      <p v-if="run.note" class="app-card flex items-center gap-2 p-3.5 text-xs text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0" />{{ run.note }}
      </p>

      <!-- Review gate -->
      <div
        v-if="run.status === 'awaiting_review'"
        class="app-card border-[var(--app-blue)]/50 bg-[var(--app-blue-soft)] p-5"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-start gap-2.5">
            <UIcon name="i-lucide-clipboard-check" class="mt-0.5 h-5 w-5 shrink-0 text-[var(--app-blue)]" />
            <div>
              <p class="text-sm font-semibold text-[var(--app-ink)]">
                {{ generatedCount }} site(s) à valider avant démarchage
              </p>
              <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
                Les sites les moins bien remplis sont remontés en premier. Corrige, exclus, puis lance.
              </p>
            </div>
          </div>
          <button class="app-btn-primary" :disabled="isActing" @click="approve">
            <UIcon name="i-lucide-send" class="h-4 w-4" />Valider et démarcher
          </button>
        </div>
      </div>

      <!-- Prospect list -->
      <div class="app-card overflow-hidden">
        <!-- Toolbar -->
        <div class="flex flex-wrap items-center gap-2 border-b border-[var(--app-line)] px-4 py-3">
          <p class="text-sm font-medium text-[var(--app-ink)]">Prospects</p>
          <template v-if="selected.size > 0">
            <span class="h-4 w-px bg-[var(--app-line)]" />
            <span class="font-label text-xs text-[var(--app-ink-soft)]">{{ selected.size }} sélectionné(s)</span>
            <select v-model="bulkTemplateId" class="app-input h-8 w-auto min-w-40 text-xs">
              <option :value="''">Changer de template…</option>
              <option v-for="tpl in demoTemplates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
            </select>
            <button class="app-btn-secondary h-8 px-3 text-xs" :disabled="isActing" @click="regenerate">
              <UIcon name="i-lucide-refresh-cw" class="h-3.5 w-3.5" />Régénérer
            </button>
            <button class="app-btn-secondary h-8 px-3 text-xs" :disabled="isActing" @click="reenrich">
              <UIcon name="i-lucide-sparkles" class="h-3.5 w-3.5" />Ré-enrichir
            </button>
            <button
              class="app-btn-secondary h-8 px-3 text-xs text-[var(--app-red)]"
              :disabled="isActing"
              @click="exclude"
            >
              Exclure
            </button>
          </template>
        </div>

        <!-- Rows -->
        <div class="divide-y divide-[var(--app-line-soft)]">
          <div
            v-for="item in sortedItems"
            :key="item.id"
            class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4 px-4 py-3 transition-colors hover:bg-[var(--app-surface-2)]/40"
          >
            <button
              type="button"
              class="flex h-4 w-4 shrink-0 items-center justify-center rounded border"
              :class="
                selected.has(item.id)
                  ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
                  : 'border-[var(--app-line)]'
              "
              @click="toggleSelect(item.id)"
            >
              <UIcon v-if="selected.has(item.id)" name="i-lucide-check" class="h-3 w-3" />
            </button>

            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <p class="truncate text-sm font-medium text-[var(--app-ink)]">
                  {{ item.prospect_name || `#${item.prospect_id}` }}
                </p>
                <span
                  v-if="item.won"
                  class="rounded-full bg-[var(--app-green-soft)] px-1.5 py-0.5 text-[9px] font-medium text-[var(--app-green)]"
                  >vendu</span
                >
                <span class="app-badge" :class="stepBadgeClass(item.step)">{{ stepLabel(item.step) }}</span>
                <span v-if="item.prospect_city" class="text-[11px] text-[var(--app-ink-soft)]">{{
                  item.prospect_city
                }}</span>
              </div>
              <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                <div v-if="item.quality_score !== null" class="flex items-center gap-1.5">
                  <div class="h-1.5 w-20 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
                    <div
                      class="h-full rounded-full"
                      :class="qualityColor(item.quality_score)"
                      :style="{ width: `${item.quality_score}%` }"
                    />
                  </div>
                  <span class="text-[10px] text-[var(--app-ink-soft)]">{{ item.quality_score }}/100</span>
                </div>
                <span
                  v-if="item.quality_flags && item.quality_flags.length"
                  class="text-[10px] text-[var(--app-red)]"
                  >{{ item.quality_flags.join(', ') }}</span
                >
                <span v-else-if="item.step_reason" class="text-[10px] text-[var(--app-faint)]">{{
                  item.step_reason
                }}</span>
              </div>
            </div>

            <div class="flex shrink-0 items-center gap-1">
              <a
                v-if="item.demo_url"
                :href="item.demo_url"
                target="_blank"
                rel="noopener"
                class="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                title="Voir le site"
                ><UIcon name="i-lucide-external-link" class="h-3.5 w-3.5"
              /></a>
              <a
                v-if="item.storyblok_editor_url"
                :href="item.storyblok_editor_url"
                target="_blank"
                rel="noopener"
                class="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                title="Éditer (Storyblok)"
                ><UIcon name="i-lucide-pencil" class="h-3.5 w-3.5"
              /></a>
              <button
                v-if="run.email_template_id_a"
                class="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                title="Voir le mail"
                @click="openPreview(item.id)"
              >
                <UIcon name="i-lucide-mail" class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Email preview modal -->
    <Teleport to="body">
      <div
        v-if="previewOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)] p-4"
        @click.self="previewOpen = false"
      >
        <div
          class="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
        >
          <div class="flex items-center justify-between border-b border-[var(--app-line)] px-5 py-3.5">
            <p class="text-sm font-semibold text-[var(--app-ink)]">Aperçu du mail</p>
            <button
              class="rounded-lg p-1 text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              @click="previewOpen = false"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />
            </button>
          </div>
          <div class="overflow-y-auto p-5">
            <p v-if="isPreviewing" class="flex items-center gap-2 text-sm text-[var(--app-ink-soft)]">
              <UIcon name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />Rendu…
            </p>
            <template v-else-if="preview">
              <p class="mb-3 text-sm">
                <span class="text-[var(--app-ink-soft)]">Objet :</span>
                <span class="font-medium text-[var(--app-ink)]">{{ preview.subject }}</span>
              </p>
              <!-- eslint-disable vue/no-v-html -- rendering our own backend-generated email HTML -->
              <div
                class="max-w-none rounded-xl border border-[var(--app-line)] bg-white p-4 text-black"
                v-html="preview.body_html"
              />
              <!-- eslint-enable vue/no-v-html -->
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type {
  AutomationDetail,
  AutomationItem,
  AutomationStatus,
  AutomationStep,
  EmailPreview,
} from '~/types/Automation'
import type { DemoSiteTemplate } from '~/services/demoSiteService'
import { useAutomationsStore } from '~/stores/automations'
import {
  excludeItems as excludeItemsSvc,
  previewItemEmail,
  reenrichItems as reenrichItemsSvc,
  regenerateItems as regenerateItemsSvc,
} from '~/services/automationsService'
import { listDemoSiteTemplates } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

/** A KPI tile. */
interface Kpi {
  label: string
  value: number
  class: string
}

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const store = useAutomationsStore()
const toast = useToast()
const route = useRoute()

/** The automatisation id from the route. */
const runId: number = Number(route.params.id)
/** Whether a lifecycle/correction action is in flight. */
const isActing: Ref<boolean> = ref<boolean>(false)
/** Selected item ids for bulk actions. */
const selected: Ref<Set<number>> = ref<Set<number>>(new Set<number>())
/** Demo templates (for the bulk template change). */
const demoTemplates: Ref<DemoSiteTemplate[]> = ref<DemoSiteTemplate[]>([])
/** Template chosen in the bulk toolbar (empty = keep current). */
const bulkTemplateId: Ref<string> = ref<string>('')
/** Email preview modal state. */
const previewOpen: Ref<boolean> = ref<boolean>(false)
const isPreviewing: Ref<boolean> = ref<boolean>(false)
const preview: Ref<EmailPreview | null> = ref<EmailPreview | null>(null)
/** Polling handle. */
const pollHandle: Ref<ReturnType<typeof setInterval> | null> = ref<ReturnType<typeof setInterval> | null>(null)

/** The open automatisation. */
const run: ComputedRef<AutomationDetail | null> = computed((): AutomationDetail | null => store.current)

/** Items sorted so the risky (low-score) generated sites come first. */
const sortedItems: ComputedRef<AutomationItem[]> = computed((): AutomationItem[] => {
  const items: AutomationItem[] = [...(run.value?.items ?? [])]
  return items.sort(
    (a: AutomationItem, b: AutomationItem): number => (a.quality_score ?? 999) - (b.quality_score ?? 999),
  )
})

/** Count of generated sites awaiting review. */
const generatedCount: ComputedRef<number> = computed(
  (): number => (run.value?.items ?? []).filter((i: AutomationItem): boolean => i.step === 'generated').length,
)

/** Whether the run can be cancelled. */
const canCancel: ComputedRef<boolean> = computed(
  (): boolean => run.value !== null && ['running', 'paused', 'awaiting_review'].includes(run.value.status),
)

/** Whether the run is terminal (deletable). */
const isTerminal: ComputedRef<boolean> = computed(
  (): boolean => run.value !== null && ['completed', 'cancelled', 'failed'].includes(run.value.status),
)

/** KPI tiles. */
const kpis: ComputedRef<Kpi[]> = computed((): Kpi[] => {
  const r: AutomationDetail | null = run.value
  if (r === null) return []
  const by: Record<string, number> = r.stats.by_step
  const count = (steps: AutomationStep[]): number =>
    steps.reduce((s: number, k: AutomationStep): number => s + (by[k] ?? 0), 0)
  return [
    { label: 'Prospects', value: r.stats.total, class: 'text-[var(--app-ink)]' },
    {
      label: 'Enrichis',
      value: count(['enriched', 'generating', 'generated', 'campaigning']),
      class: 'text-[var(--app-ink)]',
    },
    { label: 'Sites', value: count(['generated', 'campaigning']), class: 'text-[var(--app-violet)]' },
    { label: 'En campagne', value: count(['campaigning']), class: 'text-[var(--app-blue)]' },
    { label: 'Emails', value: r.stats.emails_sent, class: 'text-[var(--app-ink)]' },
    { label: 'Vendus', value: r.stats.won, class: 'text-[var(--app-green)]' },
  ]
})

/**
 * Label for a status.
 * @param status - The status.
 * @returns French label.
 */
function statusLabel(status: AutomationStatus): string {
  const labels: Record<AutomationStatus, string> = {
    draft: 'Brouillon',
    running: 'En cours',
    paused: 'En pause',
    awaiting_review: 'À valider',
    completed: 'Terminée',
    cancelled: 'Annulée',
    failed: 'Échec',
  }
  return labels[status]
}

/**
 * Badge class for a status.
 * @param status - The status.
 * @returns The ``app-badge--*`` modifier.
 */
function statusBadgeClass(status: AutomationStatus): string {
  const classes: Record<AutomationStatus, string> = {
    draft: '',
    running: 'app-badge--progress',
    paused: '',
    awaiting_review: 'app-badge--info',
    completed: 'app-badge--success',
    cancelled: 'app-badge--danger',
    failed: 'app-badge--danger',
  }
  return classes[status]
}

/**
 * Label for an item step.
 * @param step - The step.
 * @returns French label.
 */
function stepLabel(step: AutomationStep): string {
  const labels: Record<AutomationStep, string> = {
    found: 'En file',
    enriching: 'Enrichissement',
    enriched: 'Enrichi',
    generating: 'Génération',
    generated: 'Site prêt',
    campaigning: 'En campagne',
    skipped: 'Écarté',
    failed: 'Échec',
  }
  return labels[step]
}

/**
 * Badge class for an item step.
 * @param step - The step.
 * @returns The ``app-badge--*`` modifier.
 */
function stepBadgeClass(step: AutomationStep): string {
  if (step === 'campaigning') return 'app-badge--success'
  if (step === 'generated') return 'app-badge--info'
  if (step === 'failed') return 'app-badge--danger'
  if (step === 'skipped') return ''
  return 'app-badge--progress'
}

/**
 * Colour for a quality bar.
 * @param score - 0-100.
 * @returns A background class.
 */
function qualityColor(score: number): string {
  if (score >= 70) return 'bg-[var(--app-green)]'
  if (score >= 45) return 'bg-[var(--app-accent)]'
  return 'bg-[var(--app-red)]'
}

/**
 * Toggle an item selection.
 * @param id - Item id.
 */
function toggleSelect(id: number): void {
  const next: Set<number> = new Set<number>(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

/**
 * Run a correction action over the selected items, applying the fresh detail.
 * @param fn - The service call returning the updated detail.
 * @returns A promise resolved once applied.
 */
async function runAction(fn: () => Promise<AutomationDetail>): Promise<void> {
  isActing.value = true
  try {
    store.applyDetail(await fn())
    selected.value = new Set<number>()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'action")
  } finally {
    isActing.value = false
  }
}

/** Regenerate selected items (optionally with the chosen template). */
async function regenerate(): Promise<void> {
  const ids: number[] = Array.from(selected.value)
  await runAction((): Promise<AutomationDetail> => regenerateItemsSvc(runId, ids, bulkTemplateId.value || null))
}

/** Re-enrich selected items. */
async function reenrich(): Promise<void> {
  const ids: number[] = Array.from(selected.value)
  await runAction((): Promise<AutomationDetail> => reenrichItemsSvc(runId, ids))
}

/** Exclude selected items. */
async function exclude(): Promise<void> {
  const ids: number[] = Array.from(selected.value)
  await runAction((): Promise<AutomationDetail> => excludeItemsSvc(runId, ids))
}

/** Cancel the automatisation. */
async function cancel(): Promise<void> {
  isActing.value = true
  try {
    await store.cancel(runId)
  } finally {
    isActing.value = false
  }
}

/** Approve the review gate. */
async function approve(): Promise<void> {
  isActing.value = true
  try {
    await store.approve(runId)
    toast.success('Démarchage lancé')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur à la validation')
  } finally {
    isActing.value = false
  }
}

/** Delete the automatisation then go back to the list. */
async function remove(): Promise<void> {
  isActing.value = true
  try {
    await store.remove(runId)
    toast.success('Automatisation supprimée')
    await navigateTo('/dashboard/automations')
  } finally {
    isActing.value = false
  }
}

/**
 * Open the email preview modal for an item.
 * @param itemId - The item to preview.
 * @returns A promise resolved once rendered.
 */
async function openPreview(itemId: number): Promise<void> {
  if (run.value?.email_template_id_a == null) return
  previewOpen.value = true
  isPreviewing.value = true
  preview.value = null
  try {
    preview.value = await previewItemEmail(runId, itemId, run.value.email_template_id_a)
  } catch {
    toast.error("Impossible de générer l'aperçu")
    previewOpen.value = false
  } finally {
    isPreviewing.value = false
  }
}

onMounted(async (): Promise<void> => {
  try {
    await store.fetchOne(runId)
  } catch {
    toast.error('Automatisation introuvable')
    await navigateTo('/dashboard/automations')
    return
  }
  demoTemplates.value = await listDemoSiteTemplates().catch((): DemoSiteTemplate[] => [])
  pollHandle.value = setInterval((): void => {
    if (store.hasActive) void store.refreshActive()
  }, 5000)
})

onBeforeUnmount((): void => {
  if (pollHandle.value !== null) {
    clearInterval(pollHandle.value)
    pollHandle.value = null
  }
  store.clearCurrent()
})
</script>
