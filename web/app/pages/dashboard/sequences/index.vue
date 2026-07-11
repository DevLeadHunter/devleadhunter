<template>
  <div class="space-y-5">
    <!-- ───────────────────────── Header ───────────────────────── -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Séquences</h1>
        <p class="text-muted mt-1 text-sm">
          La machine enrichit, génère les sites, s'arrête pour validation, puis démarche — seule.
        </p>
      </div>
      <button class="btn-primary" @click="openCreateDrawer">
        <UIcon name="i-lucide-plus" class="mr-1.5 h-4 w-4" />
        Nouvelle séquence
      </button>
    </div>

    <!-- ═══════════════════ Pipeline board (selected) ═══════════════════ -->
    <template v-if="store.current !== null">
      <button
        class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
        @click="store.clearCurrent()"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Toutes les séquences
      </button>

      <!-- Board header -->
      <div class="card space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <h2 class="truncate text-lg font-semibold text-[var(--app-ink)]">{{ store.current.name }}</h2>
              <span class="app-badge" :class="statusBadgeClass(store.current.status)">
                {{ statusLabel(store.current.status) }}
              </span>
            </div>
            <p class="text-muted mt-0.5 text-xs">
              {{ store.current.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto' }}
              · {{ store.current.stats.total }} prospect(s)
              <span v-if="store.current.campaign_id">
                ·
                <NuxtLink
                  :to="`/dashboard/campaigns/${store.current.campaign_id}`"
                  class="underline underline-offset-2 hover:text-[var(--app-ink)]"
                >
                  campagne liée
                </NuxtLink>
              </span>
            </p>
          </div>

          <div class="flex items-center gap-2">
            <button
              v-if="store.current.status === 'running'"
              class="btn-secondary"
              :disabled="isActing"
              @click="act('pause')"
            >
              <UIcon name="i-lucide-pause" class="mr-1.5 h-3.5 w-3.5" />
              Pause
            </button>
            <button
              v-if="store.current.status === 'paused'"
              class="btn-secondary"
              :disabled="isActing"
              @click="act('resume')"
            >
              <UIcon name="i-lucide-play" class="mr-1.5 h-3.5 w-3.5" />
              Reprendre
            </button>
            <button
              v-if="canCancel(store.current.status)"
              class="btn-secondary"
              :disabled="isActing"
              @click="act('cancel')"
            >
              Annuler
            </button>
            <button
              v-if="isTerminal(store.current.status)"
              class="btn-danger"
              :disabled="isActing"
              @click="act('delete')"
            >
              <UIcon name="i-lucide-trash-2" class="mr-1.5 h-3.5 w-3.5" />
              Supprimer
            </button>
          </div>
        </div>

        <!-- KPIs -->
        <div class="grid grid-cols-3 gap-3 sm:grid-cols-6">
          <div v-for="kpi in boardKpis" :key="kpi.label" class="rounded-lg bg-[var(--app-surface-2)] px-3 py-2">
            <p class="app-label">{{ kpi.label }}</p>
            <p class="mt-0.5 text-xl font-bold tabular-nums" :class="kpi.class">{{ kpi.value }}</p>
          </div>
        </div>

        <!-- Guardrail / campaign note -->
        <p
          v-if="campaignNote"
          class="flex items-center gap-2 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2 text-xs text-[var(--app-ink-soft)]"
        >
          <UIcon name="i-lucide-info" class="h-3.5 w-3.5 shrink-0" />
          {{ campaignNote }}
        </p>
      </div>

      <!-- Review gate -->
      <div
        v-if="store.current.status === 'awaiting_review'"
        class="card border-[var(--app-blue)] bg-[var(--app-blue-soft)]"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-start gap-2.5">
            <UIcon name="i-lucide-clipboard-check" class="mt-0.5 h-5 w-5 shrink-0 text-[var(--app-blue)]" />
            <div>
              <p class="text-sm font-semibold text-[var(--app-ink)]">
                {{ reviewCount }} site(s) à valider avant démarchage
              </p>
              <p class="text-muted mt-0.5 text-xs">
                Vérifiez les sites générés, rejetez ceux à écarter, puis lancez le démarchage.
              </p>
            </div>
          </div>
          <button class="btn-primary" :disabled="isActing" @click="act('approve')">
            <UIcon name="i-lucide-send" class="mr-1.5 h-4 w-4" />
            Valider et démarcher
          </button>
        </div>
      </div>

      <!-- Columns -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-5">
        <div v-for="column in boardColumns" :key="column.key" class="space-y-2">
          <div class="flex items-center justify-between px-1">
            <p class="text-xs font-semibold text-[var(--app-ink)]">{{ column.label }}</p>
            <span class="rounded-full bg-[var(--app-surface-2)] px-2 py-0.5 text-[10px] text-[var(--app-ink-soft)]">
              {{ column.items.length }}
            </span>
          </div>

          <div class="space-y-2">
            <p
              v-if="column.items.length === 0"
              class="rounded-lg border border-dashed border-[var(--app-line)] px-2 py-4 text-center text-[10px] text-[var(--app-faint)]"
            >
              —
            </p>
            <div
              v-for="item in column.items"
              :key="item.id"
              class="card gap-2 p-3"
              :class="item.won ? 'border-[var(--app-green)]' : ''"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate text-xs font-medium text-[var(--app-ink)]">
                    {{ item.prospect_name || `#${item.prospect_id}` }}
                  </p>
                  <p class="truncate text-[10px] text-[var(--app-ink-soft)]">{{ item.prospect_city || '—' }}</p>
                </div>
                <span
                  v-if="item.won"
                  class="shrink-0 rounded-full bg-[var(--app-green-soft)] px-1.5 py-0.5 text-[9px] font-medium text-[var(--app-green)]"
                >
                  vendu
                </span>
                <span v-else class="mt-1 h-2 w-2 shrink-0 rounded-full" :class="stepDotClass(item.step)" />
              </div>

              <p v-if="item.step_reason" class="text-[10px] text-[var(--app-faint)]">{{ item.step_reason }}</p>

              <div class="flex items-center gap-2">
                <a
                  v-if="item.demo_url"
                  :href="item.demo_url"
                  target="_blank"
                  rel="noopener"
                  class="flex items-center gap-1 text-[10px] text-[var(--app-ink-soft)] underline-offset-2 hover:text-[var(--app-ink)] hover:underline"
                >
                  <UIcon name="i-lucide-external-link" class="h-3 w-3" />
                  Voir le site
                </a>
                <button
                  v-if="store.current.status === 'awaiting_review' && item.step === 'generated'"
                  class="text-[10px] text-[var(--app-red)] underline-offset-2 hover:underline"
                  :disabled="isActing"
                  @click="rejectItem(item.id)"
                >
                  Rejeter
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ═══════════════════ List of sequences ═══════════════════ -->
    <template v-else>
      <!-- Loading -->
      <div v-if="store.isLoading && store.sequences.length === 0" class="card animate-pulse space-y-3">
        <div class="h-4 w-1/3 rounded bg-[var(--app-surface-2)]" />
        <div class="h-3 w-1/2 rounded bg-[var(--app-surface-2)]" />
      </div>

      <!-- Content -->
      <div v-else-if="store.sequencesCount > 0" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <button
          v-for="seq in store.sequences"
          :key="seq.id"
          class="group card flex cursor-pointer flex-col gap-3 text-left transition-transform hover:-translate-y-0.5"
          @click="openSequence(seq.id)"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="truncate font-semibold text-[var(--app-ink)]">{{ seq.name }}</p>
              <p class="text-muted mt-0.5 text-[11px]">
                {{ seq.mode === 'full_auto' ? 'Full-auto' : 'Semi-auto' }} · {{ formatDate(seq.created_at) }}
              </p>
            </div>
            <span class="app-badge shrink-0" :class="statusBadgeClass(seq.status)">
              {{ statusLabel(seq.status) }}
            </span>
          </div>

          <div class="grid grid-cols-4 gap-2">
            <div v-for="kpi in listKpis(seq)" :key="kpi.label" class="rounded-lg bg-[var(--app-surface-2)] px-2 py-1.5">
              <p class="text-[9px] tracking-wide text-[var(--app-faint)] uppercase">{{ kpi.label }}</p>
              <p class="text-sm font-bold text-[var(--app-ink)] tabular-nums">{{ kpi.value }}</p>
            </div>
          </div>

          <p
            v-if="seq.status === 'awaiting_review'"
            class="flex items-center gap-1.5 text-[11px] font-medium text-[var(--app-blue)]"
          >
            <UIcon name="i-lucide-clipboard-check" class="h-3.5 w-3.5" />
            Des sites attendent votre validation
          </p>
        </button>
      </div>

      <!-- Empty -->
      <div v-else class="card px-6 py-12 text-center">
        <UIcon name="i-lucide-workflow" class="mx-auto h-8 w-8 text-[var(--app-faint)]" />
        <p class="mt-3 font-medium text-[var(--app-ink)]">Aucune séquence pour l'instant</p>
        <p class="text-muted mx-auto mt-1 max-w-md text-sm">
          Sélectionnez des prospects et laissez la machine enrichir, générer les sites et démarcher pour vous.
        </p>
        <button class="btn-primary mx-auto mt-4" @click="openCreateDrawer">
          <UIcon name="i-lucide-plus" class="mr-1.5 h-4 w-4" />
          Créer une séquence
        </button>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Sequence, SequenceItem, SequenceStatus, SequenceStep } from '~/types/AcquisitionSequence'
import { useAcquisitionSequencesStore } from '~/stores/acquisitionSequences'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

/** A single KPI tile. */
interface Kpi {
  label: string
  value: number
  class: string
}

/** A pipeline board column grouping several steps. */
interface BoardColumn {
  key: string
  label: string
  steps: SequenceStep[]
  items: SequenceItem[]
}

/** Sequence lifecycle actions triggered from the board. */
type SequenceAction = 'pause' | 'resume' | 'cancel' | 'approve' | 'delete'

const store = useAcquisitionSequencesStore()
const drawerStack = useDrawerStackStore()
const toast = useToast()
const route = useRoute()

/** Whether a lifecycle action is in flight. */
const isActing: Ref<boolean> = ref<boolean>(false)
/** Polling handle for live progress. */
const pollHandle: Ref<ReturnType<typeof setInterval> | null> = ref<ReturnType<typeof setInterval> | null>(null)

/** Board columns computed from the open sequence's items. */
const boardColumns: ComputedRef<BoardColumn[]> = computed((): BoardColumn[] => {
  const items: SequenceItem[] = store.current?.items ?? []
  const columns: Array<{ key: string; label: string; steps: SequenceStep[] }> = [
    { key: 'queue', label: "File d'attente", steps: ['found', 'enriching'] },
    { key: 'enriched', label: 'Enrichis', steps: ['enriched'] },
    { key: 'generated', label: 'Sites générés', steps: ['generating', 'generated'] },
    { key: 'campaigning', label: 'En campagne', steps: ['campaigning'] },
    { key: 'dropped', label: 'Écartés', steps: ['skipped', 'failed'] },
  ]
  return columns.map(
    (col): BoardColumn => ({
      ...col,
      items: items.filter((item: SequenceItem): boolean => col.steps.includes(item.step)),
    }),
  )
})

/** Number of generated sites awaiting review. */
const reviewCount: ComputedRef<number> = computed(
  (): number => (store.current?.items ?? []).filter((i: SequenceItem): boolean => i.step === 'generated').length,
)

/** Campaign / guardrail note surfaced from the run stats, if any. */
const campaignNote: ComputedRef<string | null> = computed((): string | null => {
  const stats: Record<string, unknown> = (store.current?.stats ?? {}) as unknown as Record<string, unknown>
  const note: unknown = stats.campaign_note ?? stats.pause_reason
  return typeof note === 'string' ? note : null
})

/** KPI tiles for the board header. */
const boardKpis: ComputedRef<Kpi[]> = computed((): Kpi[] => {
  const seq: Sequence | null = store.current
  if (seq === null) return []
  return [
    { label: 'Prospects', value: seq.stats.total, class: 'text-[var(--app-ink)]' },
    {
      label: 'Enrichis',
      value: stepCount(seq, ['enriched', 'generating', 'generated', 'campaigning']),
      class: 'text-[var(--app-ink)]',
    },
    { label: 'Sites', value: stepCount(seq, ['generated', 'campaigning']), class: 'text-[var(--app-violet)]' },
    { label: 'En campagne', value: stepCount(seq, ['campaigning']), class: 'text-[var(--app-blue)]' },
    { label: 'Emails', value: seq.stats.emails_sent, class: 'text-[var(--app-ink)]' },
    { label: 'Vendus', value: seq.stats.won, class: 'text-[var(--app-green)]' },
  ]
})

/**
 * Count items of a sequence currently in any of the given steps.
 * @param seq - The sequence.
 * @param steps - Steps to sum.
 * @returns The total count.
 */
function stepCount(seq: Sequence, steps: SequenceStep[]): number {
  return steps.reduce((sum: number, step: SequenceStep): number => sum + (seq.stats.by_step[step] ?? 0), 0)
}

/**
 * Compact KPI tiles for a sequence card in the list.
 * @param seq - The sequence.
 * @returns Four KPI tiles.
 */
function listKpis(seq: Sequence): Kpi[] {
  return [
    { label: 'Total', value: seq.stats.total, class: '' },
    { label: 'Sites', value: stepCount(seq, ['generated', 'campaigning']), class: '' },
    { label: 'Emails', value: seq.stats.emails_sent, class: '' },
    { label: 'Vendus', value: seq.stats.won, class: '' },
  ]
}

/**
 * Human label for a sequence status.
 * @param status - The status.
 * @returns The French label.
 */
function statusLabel(status: SequenceStatus): string {
  const labels: Record<SequenceStatus, string> = {
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
 * Badge modifier class for a sequence status.
 * @param status - The status.
 * @returns The ``app-badge--*`` modifier (or empty for neutral).
 */
function statusBadgeClass(status: SequenceStatus): string {
  const classes: Record<SequenceStatus, string> = {
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
 * Dot colour for a single item's step.
 * @param step - The item step.
 * @returns A background colour class.
 */
function stepDotClass(step: SequenceStep): string {
  const map: Record<SequenceStep, string> = {
    found: 'bg-[var(--app-faint)]',
    enriching: 'bg-[var(--app-blue)]',
    enriched: 'bg-[var(--app-blue)]',
    generating: 'bg-[var(--app-violet)]',
    generated: 'bg-[var(--app-violet)]',
    campaigning: 'bg-[var(--app-green)]',
    skipped: 'bg-[var(--app-faint)]',
    failed: 'bg-[var(--app-red)]',
  }
  return map[step]
}

/**
 * Whether a sequence can still be cancelled.
 * @param status - The status.
 * @returns True when cancellable.
 */
function canCancel(status: SequenceStatus): boolean {
  return ['running', 'paused', 'awaiting_review'].includes(status)
}

/**
 * Whether a sequence is in a terminal (deletable) state.
 * @param status - The status.
 * @returns True when terminal.
 */
function isTerminal(status: SequenceStatus): boolean {
  return ['completed', 'cancelled', 'failed'].includes(status)
}

/**
 * Format an ISO date as a short French date.
 * @param iso - ISO date string.
 * @returns The formatted date.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

/** Open the create-sequence drawer. */
function openCreateDrawer(): void {
  drawerStack.push({ kind: 'create-sequence' })
}

/**
 * Open a sequence's pipeline board.
 * @param id - Sequence identifier.
 * @returns A promise resolved once loaded.
 */
async function openSequence(id: number): Promise<void> {
  try {
    await store.fetchSequence(id)
  } catch {
    toast.error('Impossible de charger la séquence')
  }
}

/**
 * Run a lifecycle action on the open sequence.
 * @param action - The action to perform.
 * @returns A promise resolved once the action completes.
 */
async function act(action: SequenceAction): Promise<void> {
  const seq: Sequence | null = store.current
  if (seq === null) return
  isActing.value = true
  try {
    if (action === 'pause') await store.pause(seq.id)
    else if (action === 'resume') await store.resume(seq.id)
    else if (action === 'cancel') await store.cancel(seq.id)
    else if (action === 'approve') await store.approve(seq.id)
    else if (action === 'delete') {
      await store.remove(seq.id)
      toast.success('Séquence supprimée')
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'action")
  } finally {
    isActing.value = false
  }
}

/**
 * Reject a single generated site during review.
 * @param itemId - The item to reject.
 * @returns A promise resolved once rejected.
 */
async function rejectItem(itemId: number): Promise<void> {
  const seq: Sequence | null = store.current
  if (seq === null) return
  isActing.value = true
  try {
    await store.reject(seq.id, itemId)
  } catch {
    toast.error('Erreur lors du rejet du site')
  } finally {
    isActing.value = false
  }
}

onMounted(async (): Promise<void> => {
  await store.fetchSequences()
  const openId: string | undefined = Array.isArray(route.query.open) ? route.query.open[0] : route.query.open
  if (openId) {
    await openSequence(Number(openId))
  }
  // Live progress: refresh while the machine is still working.
  pollHandle.value = setInterval((): void => {
    if (store.hasActive) {
      void store.refreshActive()
    }
  }, 5000)
})

onBeforeUnmount((): void => {
  if (pollHandle.value !== null) {
    clearInterval(pollHandle.value)
    pollHandle.value = null
  }
})
</script>
