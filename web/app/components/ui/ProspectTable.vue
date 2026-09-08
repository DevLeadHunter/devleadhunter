<template>
  <div class="overflow-hidden">
    <BaseTable :animate-row-moves="reorderable">
      <template #head>
        <BaseTableTh v-if="reorderable" sr-only>Réordonner</BaseTableTh>
        <BaseTableTh v-if="!hideSelection" class="w-12">
          <input
            type="checkbox"
            class="h-4 w-4 cursor-pointer accent-(--app-accent)"
            :checked="allSelected"
            :indeterminate.prop="someSelected && !allSelected"
            aria-label="Tout sélectionner sur cette page"
            @change="onToggleAll"
          />
        </BaseTableTh>
        <BaseTableTh>Nom</BaseTableTh>
        <BaseTableTh>Ville</BaseTableTh>
        <BaseTableTh>Téléphone</BaseTableTh>
        <BaseTableTh>Email</BaseTableTh>
        <BaseTableTh>Site web</BaseTableTh>
        <BaseTableTh>Contacté</BaseTableTh>
        <BaseTableTh align="center">Température</BaseTableTh>
        <BaseTableTh>Source</BaseTableTh>
        <BaseTableTh v-if="showAbVariant" align="center">Variante</BaseTableTh>
        <BaseTableTh align="center" sr-only>Actions</BaseTableTh>
      </template>

      <BaseTableTr
        v-for="prospect in displayedProspects"
        :key="prospect.id"
        :data-prospect-id="prospect.id"
        :class="[
          isSelected(prospect) ? 'bg-[var(--app-accent-soft)] hover:bg-[var(--app-accent-soft)]' : '',
          isLockedForMe(prospect)
            ? 'bg-[var(--app-surface-2)]/40 hover:bg-[var(--app-surface-2)]/40'
            : 'cursor-pointer',
          isBeingDragged(prospect) ? 'bg-[var(--app-accent-soft)] opacity-50 hover:bg-[var(--app-accent-soft)]' : '',
        ]"
        @click="onRowClick(prospect, $event)"
      >
        <BaseTableTd v-if="reorderable" class="w-10 pr-0">
          <button
            type="button"
            class="flex h-7 w-7 cursor-grab touch-none items-center justify-center rounded text-[var(--app-faint)] transition-colors hover:text-[var(--app-ink)] active:cursor-grabbing"
            aria-label="Glisser pour changer le jour d'envoi"
            title="Glisser pour changer le jour d'envoi"
            @pointerdown="onHandlePointerDown($event, prospect)"
            @pointermove="onHandlePointerMove"
            @pointerup="onHandlePointerUp"
            @pointercancel="cancelDrag"
          >
            <UIcon name="i-lucide-grip-vertical" class="h-4 w-4" />
          </button>
        </BaseTableTd>

        <BaseTableTd v-if="!hideSelection">
          <input
            type="checkbox"
            class="h-4 w-4 accent-(--app-accent)"
            :class="isLockedForMe(prospect) ? 'cursor-not-allowed opacity-30' : 'cursor-pointer'"
            :checked="isSelected(prospect)"
            :disabled="isLockedForMe(prospect)"
            :aria-label="`Sélectionner ${prospect.name}`"
            @change="emit('toggleSelect', prospect)"
          />
        </BaseTableTd>

        <BaseTableTd>
          <div
            v-if="isLockedForMe(prospect)"
            class="flex items-center gap-2"
            :title="`Réservé par ${prospect.reserved_by_name || 'un membre de votre organisation'}`"
          >
            <UIcon name="i-lucide-lock" class="h-3.5 w-3.5 shrink-0 text-[var(--app-faint)]" />
            <span class="min-w-0">
              <span class="block truncate text-sm font-semibold text-[var(--app-ink-soft)]">
                {{ prospect.name }}
              </span>
              <span class="text-[11px] text-[var(--app-faint)]">
                Réservé par {{ prospect.reserved_by_name || 'un membre' }}
              </span>
            </span>
          </div>
          <button
            v-else
            type="button"
            class="cursor-pointer text-left text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors hover:decoration-[var(--app-accent)]"
            @click="emit('viewProspect', prospect)"
          >
            <span class="flex items-center gap-1.5">
              {{ prospect.name }}
              <UIcon
                v-if="prospect.has_pending_contact_proposal"
                name="i-lucide-user-round-search"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]"
                title="Décisionnaire à confirmer — ouvrez la fiche pour valider ou rejeter le nom proposé"
              />
              <UIcon
                v-if="isReservedByMe(prospect)"
                name="i-lucide-lock-keyhole"
                class="h-3 w-3 text-[var(--app-accent)]"
                title="Vous avez réservé ce prospect"
              />
              <UIcon
                v-if="prospect.sms_opted_out"
                name="i-lucide-message-square-off"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="A répondu STOP — ne plus envoyer de SMS"
              />
              <UIcon
                v-if="prospect.email_unsubscribed"
                name="i-lucide-mail-x"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="Désinscrit de la liste d'emails"
              />
              <UIcon
                v-if="prospect.do_not_contact"
                name="i-lucide-ban"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="Ne plus contacter — exclu des campagnes et des SMS"
              />
              <UIcon
                v-if="prospect.email_undeliverable"
                name="i-lucide-mail-x"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="Email injoignable (bounce) — récupérable en campagne SMS"
              />
            </span>
          </button>
        </BaseTableTd>

        <BaseTableTd label="Ville" class="text-sm text-[var(--app-ink-soft)]">{{ prospect.city || '—' }}</BaseTableTd>

        <BaseTableTd
          label="Téléphone"
          class="font-label text-xs whitespace-nowrap text-[var(--app-ink-soft)] tabular-nums"
          :class="isLockedForMe(prospect) && 'blur-[3px] select-none'"
        >
          {{ prospect.phone || '—' }}
        </BaseTableTd>

        <BaseTableTd label="Email" :class="isLockedForMe(prospect) && 'blur-[3px] select-none'">
          <span v-if="prospect.email" class="font-label text-xs text-[var(--app-ink)]">{{ prospect.email }}</span>
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd label="Site web">
          <span
            v-if="prospect.website_status === 'dead'"
            class="app-badge app-badge--danger"
            title="Le site trouvé ne répond plus — cible idéale"
          >
            <UIcon name="i-lucide-unplug" class="h-3 w-3" />
            Site mort
          </span>
          <span
            v-else-if="prospect.website_status === 'placeholder'"
            class="app-badge app-badge--info"
            title="Mini-site annuaire (business.site, Solocal…) — pas un vrai site"
          >
            <UIcon name="i-lucide-layout-template" class="h-3 w-3" />
            Site annuaire
          </span>
          <span v-else-if="prospect.website" class="app-badge">
            <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
            Oui
          </span>
          <span v-else class="app-badge app-badge--progress">
            <UIcon name="i-lucide-sparkle" class="h-3 w-3" />
            Non
          </span>
        </BaseTableTd>

        <BaseTableTd label="Contacté">
          <span
            v-if="prospect.email_undeliverable"
            class="app-badge app-badge--danger"
            title="Email injoignable (bounce) — récupérable en campagne SMS"
          >
            <UIcon name="i-lucide-mail-x" class="h-3 w-3" />
            Email KO
          </span>
          <span v-else-if="prospect.contacted" class="app-badge app-badge--success">
            <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
            Oui
          </span>
          <span v-else class="app-badge">Non</span>
        </BaseTableTd>

        <BaseTableTd label="Température" align="center">
          <UiTemperatureBadge v-if="temperatureOf(prospect)" :temperature="temperatureOf(prospect)" />
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd label="Source">
          <UiProspectSourceBadge :source="prospect.source" />
        </BaseTableTd>

        <BaseTableTd v-if="showAbVariant" label="Variante" align="center">
          <span
            v-if="abVariants?.[prospect.id]"
            :class="[
              'rounded px-1.5 py-0.5 text-xs font-bold',
              abVariants[prospect.id] === 'A'
                ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                : 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
            ]"
          >
            {{ abVariants[prospect.id] }}
          </span>
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd align="center">
          <button
            v-if="rowAction === 'remove' && !isLockedForMe(prospect)"
            type="button"
            class="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-[var(--app-red)]/30 px-2 py-1 text-xs text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/10"
            @click="emit('removeProspect', prospect)"
          >
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
            Retirer
          </button>
          <span v-else-if="rowAction === 'delete' && !isLockedForMe(prospect)" class="inline-flex items-center gap-1">
            <button
              type="button"
              class="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              :aria-label="`Modifier ${prospect.name}`"
              title="Modifier"
              @click="emit('editProspect', prospect)"
            >
              <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              class="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)]"
              :aria-label="`Supprimer ${prospect.name}`"
              title="Supprimer"
              @click="emit('deleteProspect', prospect)"
            >
              <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
            </button>
          </span>
        </BaseTableTd>
      </BaseTableTr>
    </BaseTable>

    <div v-if="prospects.length === 0" class="py-12 text-center">
      <LandingAsterisk class="mb-3 text-3xl text-[var(--app-accent)]" />
      <p class="text-sm text-[var(--app-ink-soft)]">Aucun prospect trouvé.</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, onBeforeUnmount, ref } from 'vue'
import type { Prospect } from '~/types'
import type { UiProspectTableDragSession, UiProspectTableEmits, UiProspectTableProps } from '~/types/UiProspectTable'
import { useUserStore } from '~/stores/user'

/** Pointer travel before a press on the grip turns into a drag, so a plain click goes through. */
const DRAG_START_THRESHOLD_PX: number = 4

/** Dead zone around a row's midpoint so a still hand does not flip the order back and forth. */
const DRAG_MIDPOINT_TOLERANCE_PX: number = 4

/** Paginated prospect rows with per-row and select-all checkboxes. */
const props: UiProspectTableProps = defineProps({
  prospects: {
    type: Array as PropType<Prospect[]>,
    required: true,
  },
  selectedProspects: {
    type: Array as PropType<string[]>,
    default: () => [],
  },
  showAbVariant: {
    type: Boolean,
    default: false,
  },
  abVariants: {
    type: Object as PropType<Record<number, string | null | undefined>>,
    default: () => ({}),
  },
  temperatures: {
    type: Object as PropType<Record<number, string>>,
    default: () => ({}),
  },
  rowAction: {
    type: String as PropType<'delete' | 'remove'>,
    default: 'delete',
  },
  hideSelection: {
    type: Boolean,
    default: false,
  },
  reorderable: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProspectTableEmits> = defineEmits<UiProspectTableEmits>()

const userStore: ReturnType<typeof useUserStore> = useUserStore()

/** Id of the prospect being dragged, or null when no drag is in progress. */
const draggedProspectId: Ref<number | null> = ref(null)

/** Live order shown during a drag — the dragged row moves as the pointer crosses rows; null otherwise. */
const draftOrder: Ref<Prospect[] | null> = ref(null)

/** Rows to render: the live draft while dragging, the prop order otherwise. */
const displayedProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => draftOrder.value ?? props.prospects)

/** The pointer-drag in progress — transient DOM session, deliberately not reactive — or null. */
let dragSession: UiProspectTableDragSession | null = null

/** Current user id (0 while the store hydrates). */
const currentUserId: ComputedRef<number> = computed((): number => userStore.user?.id ?? 0)

/** Fast lookup set of the currently-selected prospect IDs. */
const selectedSet: ComputedRef<Set<string>> = computed((): Set<string> => new Set(props.selectedProspects ?? []))

/**
 * Whether the prospect is reserved by ANOTHER organization member → locked for me.
 * @param prospect - The prospect to test.
 * @returns True when someone else holds the reservation.
 */
function isLockedForMe(prospect: Prospect): boolean {
  return prospect.reserved_by_user_id != null && prospect.reserved_by_user_id !== currentUserId.value
}

/**
 * Whether the current user holds the reservation on this prospect.
 * @param prospect - The prospect to test.
 * @returns True when the reservation is mine.
 */
function isReservedByMe(prospect: Prospect): boolean {
  return prospect.reserved_by_user_id != null && prospect.reserved_by_user_id === currentUserId.value
}

/** Whether every visible prospect is selected. */
const allSelected: ComputedRef<boolean> = computed(
  (): boolean =>
    props.prospects.length > 0 && props.prospects.every((p: Prospect): boolean => selectedSet.value.has(String(p.id))),
)

/** Whether at least one visible prospect is selected. */
const someSelected: ComputedRef<boolean> = computed((): boolean =>
  props.prospects.some((p: Prospect): boolean => selectedSet.value.has(String(p.id))),
)

/**
 * Whether a given prospect is currently selected.
 * @param prospect - The prospect to test.
 * @returns True when the prospect's id is in the selection.
 */
function isSelected(prospect: Prospect): boolean {
  return selectedSet.value.has(String(prospect.id))
}

/**
 * Return the prospect's badge-worthy temperature, or '' when there is no activity.
 * @param prospect - The prospect to read the temperature for.
 * @returns 'hot' | 'warm' | 'cold', or '' to hide the badge.
 */
function temperatureOf(prospect: Prospect): string {
  const temperature: string | undefined = props.temperatures?.[prospect.id]
  return temperature === 'hot' || temperature === 'warm' || temperature === 'cold' ? temperature : ''
}

/**
 * Relay the header checkbox toggle to the parent.
 * @param event - The native change event.
 */
function onToggleAll(event: Event): void {
  emit('toggleSelectAll', (event.target as HTMLInputElement).checked)
}

/**
 * Open the prospect drawer when a bare part of the row is clicked, leaving controls to their handlers.
 * @param prospect - The prospect of the clicked row.
 * @param event - The native click event.
 */
function onRowClick(prospect: Prospect, event: MouseEvent): void {
  if (isLockedForMe(prospect)) return
  const target: HTMLElement | null = event.target instanceof HTMLElement ? event.target : null
  if (target?.closest('button, a, input, label, select, textarea')) return
  emit('viewProspect', prospect)
}

/**
 * Whether this row is the one being dragged — it stays in the table as the landing placeholder.
 * @param prospect - Row to test.
 * @returns True while this prospect is being dragged.
 */
function isBeingDragged(prospect: Prospect): boolean {
  return draggedProspectId.value === prospect.id
}

/**
 * Arm a drag from a row's grip; it only becomes a drag once the pointer travels a few pixels.
 * @param event - The native pointerdown event on the grip.
 * @param prospect - The row's prospect.
 */
function onHandlePointerDown(event: PointerEvent, prospect: Prospect): void {
  if (!props.reorderable || event.button !== 0) return
  const handle: HTMLElement | null = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
  const row: HTMLTableRowElement | null = handle?.closest('tr') ?? null
  const table: HTMLTableElement | null = row?.closest('table') ?? null
  if (!handle || !row || !table) return
  event.preventDefault()
  handle.setPointerCapture(event.pointerId)
  const rowBounds: DOMRect = row.getBoundingClientRect()
  dragSession = {
    prospect,
    pointerId: event.pointerId,
    startClientY: event.clientY,
    grabOffsetY: event.clientY - rowBounds.top,
    rowLeft: rowBounds.left,
    rowWidth: rowBounds.width,
    table,
    ghost: null,
    active: false,
  }
}

/**
 * Follow the pointer: start the drag past the threshold, then move the ghost and the live order.
 * @param event - The native pointermove event, captured by the grip.
 */
function onHandlePointerMove(event: PointerEvent): void {
  const session: UiProspectTableDragSession | null = dragSession
  if (!session || event.pointerId !== session.pointerId) return
  if (!session.active) {
    if (Math.abs(event.clientY - session.startClientY) < DRAG_START_THRESHOLD_PX) return
    beginDrag(session)
  }
  positionRowGhost(session, event.clientY)
  moveDraggedRowTowards(session, event.clientY)
}

/**
 * Release: commit the previewed order; a press without travel is a plain click and does nothing.
 * @param event - The native pointerup event.
 */
function onHandlePointerUp(event: PointerEvent): void {
  const session: UiProspectTableDragSession | null = dragSession
  if (!session || event.pointerId !== session.pointerId) return
  if (session.active) commitDrag()
  else dragSession = null
}

/**
 * Turn the armed press into a drag: snapshot the order, lift a ghost of the row, lock the page cursor.
 * @param session - The armed drag session.
 */
function beginDrag(session: UiProspectTableDragSession): void {
  const row: HTMLTableRowElement | null = session.table.querySelector(`tr[data-prospect-id="${session.prospect.id}"]`)
  session.active = true
  draggedProspectId.value = session.prospect.id
  draftOrder.value = [...props.prospects]
  if (row) session.ghost = createRowGhost(row, session.rowWidth)
  document.body.style.cursor = 'grabbing'
  document.body.style.userSelect = 'none'
  window.addEventListener('keydown', onDragKeydown)
}

/**
 * Build the floating copy of the row that follows the pointer — opaque, bordered and shadowed, with the
 * live column widths so it looks lifted straight out of the table.
 * @param row - The table row being dragged.
 * @param width - The row's on-screen width.
 * @returns The ghost element, appended to the document body.
 */
function createRowGhost(row: HTMLTableRowElement, width: number): HTMLElement {
  const clone: HTMLTableRowElement = row.cloneNode(true) as HTMLTableRowElement
  clone.className = ''
  clone.removeAttribute('style')
  const originalCells: Element[] = Array.from(row.children)
  Array.from(clone.children).forEach((cell: Element, index: number): void => {
    const original: Element | undefined = originalCells[index]
    if (cell instanceof HTMLElement && original) cell.style.width = `${original.getBoundingClientRect().width}px`
  })
  const table: HTMLTableElement = document.createElement('table')
  table.className = 'w-full border-collapse'
  table.style.tableLayout = 'fixed'
  const body: HTMLTableSectionElement = document.createElement('tbody')
  body.appendChild(clone)
  table.appendChild(body)
  const ghost: HTMLDivElement = document.createElement('div')
  ghost.className =
    'pointer-events-none fixed top-0 left-0 z-[120] overflow-hidden rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl'
  ghost.style.width = `${width}px`
  ghost.appendChild(table)
  document.body.appendChild(ghost)
  return ghost
}

/**
 * Keep the ghost under the pointer, sliding vertically along the table so it stays column-aligned.
 * @param session - The active drag session.
 * @param clientY - Current pointer Y in viewport coordinates.
 */
function positionRowGhost(session: UiProspectTableDragSession, clientY: number): void {
  if (!session.ghost) return
  session.ghost.style.transform = `translate3d(${session.rowLeft}px, ${clientY - session.grabOffsetY}px, 0)`
}

/**
 * Slide the dragged row into the slot under the pointer. Rows are located by their layout position
 * (``offsetTop``), which ignores the slide animation, so the order never oscillates mid-transition.
 * @param session - The active drag session.
 * @param clientY - Current pointer Y in viewport coordinates.
 */
function moveDraggedRowTowards(session: UiProspectTableDragSession, clientY: number): void {
  const order: Prospect[] | null = draftOrder.value
  if (!order) return
  const from: number = order.findIndex((prospect: Prospect): boolean => prospect.id === session.prospect.id)
  const rows: HTMLTableRowElement[] = Array.from(session.table.tBodies[0]?.rows ?? [])
  if (from === -1 || rows.length !== order.length) return
  const pointerY: number = clientY - session.table.getBoundingClientRect().top
  let target: number = from
  for (let index: number = 0; index < from; index++) {
    const row: HTMLTableRowElement | undefined = rows[index]
    if (row && pointerY < row.offsetTop + row.offsetHeight / 2 - DRAG_MIDPOINT_TOLERANCE_PX) {
      target = index
      break
    }
  }
  if (target === from) {
    for (let index: number = rows.length - 1; index > from; index--) {
      const row: HTMLTableRowElement | undefined = rows[index]
      if (row && pointerY > row.offsetTop + row.offsetHeight / 2 + DRAG_MIDPOINT_TOLERANCE_PX) {
        target = index
        break
      }
    }
  }
  if (target === from) return
  const next: Prospect[] = [...order]
  const moved: Prospect | undefined = next.splice(from, 1)[0]
  if (moved === undefined) return
  next.splice(target, 0, moved)
  draftOrder.value = next
}

/** Apply the previewed order when it changed, then tear the drag down. */
function commitDrag(): void {
  const order: Prospect[] | null = draftOrder.value
  const changed: boolean =
    order !== null &&
    order.some((prospect: Prospect, position: number): boolean => prospect.id !== props.prospects[position]?.id)
  if (order && changed) {
    emit(
      'reorder',
      order.map((prospect: Prospect): number => prospect.id),
    )
  }
  endDrag()
}

/** Abandon the drag — the rows snap back to the saved order. */
function cancelDrag(): void {
  endDrag()
}

/** Remove the ghost, restore the page cursor and forget the session; the draft order is dropped. */
function endDrag(): void {
  dragSession?.ghost?.remove()
  dragSession = null
  draggedProspectId.value = null
  draftOrder.value = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('keydown', onDragKeydown)
}

/**
 * Escape cancels the drag in progress.
 * @param event - The native keydown event.
 */
function onDragKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') cancelDrag()
}

onBeforeUnmount((): void => {
  endDrag()
})
</script>
