<template>
  <div
    v-if="isDesktopDev"
    ref="rootEl"
    class="fixed z-[90] flex items-center gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]/90 px-1.5 py-1 shadow-lg backdrop-blur"
    :class="position === null ? 'right-4 bottom-4' : ''"
    :style="floatingStyle"
  >
    <button
      type="button"
      class="flex cursor-grab touch-none items-center gap-1 rounded-full py-1 pr-1 pl-2 text-amber-400 active:cursor-grabbing"
      title="Glisser pour déplacer"
      @pointerdown="startDrag"
    >
      <UIcon name="i-lucide-grip-vertical" class="h-3.5 w-3.5 opacity-70" />
      <span class="text-[10px] font-semibold tracking-[0.12em] uppercase">Dev</span>
    </button>
    <UButton
      size="xs"
      color="warning"
      variant="soft"
      icon="i-lucide-database"
      :loading="isSyncing"
      title="Écrase la base LOCALE avec les données de PROD (desktop dev uniquement). Requiert web/.env.sync (voir .env.sync.example)."
      @click="syncConfirmModal?.open()"
    >
      Sync DB prod <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> local
    </UButton>

    <UiConfirmModal
      ref="syncConfirmModal"
      title="Synchroniser la base locale"
      message="Remplacer la base LOCALE par les données de PROD ? Les tables locales seront écrasées par le dump de prod, et le bucket R2 dev sera aligné sur celui de prod (copie incrémentale)."
      confirm-text="Synchroniser"
      cancel-text="Annuler"
      confirm-button-variant="primary"
      @confirm="syncDatabaseFromProd"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseDesktopRuntimeReturn } from '~/types/Composables'
import type { StorageActionResponse } from '~/types/AdminStorage'
import type { ToolbarPosition } from '~/types/DevLeadHunterDevToolbar'
import type { CSSProperties, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { AdminStorageService } from '~/services/adminStorageService'

const STORAGE_KEY: string = 'dlh-devtoolbar-pos'

const { isDesktopDev, syncDevDatabaseFromProd }: UseDesktopRuntimeReturn = useDesktopRuntime()
const toast: ReturnType<typeof useToast> = useToast()

const isSyncing: Ref<boolean> = ref(false)
const syncConfirmModal: Ref<{ open: () => void } | null> = ref(null)
/** Root element, used to measure the toolbar during a drag. */
const rootEl: Ref<HTMLElement | null> = ref(null)
/** Current absolute position (null = default bottom-right). */
const position: Ref<ToolbarPosition | null> = ref(null)

// Drag bookkeeping.
let dragPointerId: number | null = null
let startX: number = 0
let startY: number = 0
let startLeft: number = 0
let startTop: number = 0

/** Inline style pinning the toolbar to its dragged position, if any. */
const floatingStyle: Ref<CSSProperties> = computed((): CSSProperties => {
  if (position.value === null) return {}
  return {
    left: `${position.value.left}px`,
    top: `${position.value.top}px`,
    right: 'auto',
    bottom: 'auto',
  }
})

/**
 * Clamp a position so the toolbar stays fully inside the viewport.
 * @param left - Proposed left (px).
 * @param top - Proposed top (px).
 * @returns The clamped position.
 */
function clampToViewport(left: number, top: number): ToolbarPosition {
  const rect: DOMRect | undefined = rootEl.value?.getBoundingClientRect()
  const width: number = rect?.width ?? 0
  const height: number = rect?.height ?? 0
  const maxLeft: number = Math.max(0, window.innerWidth - width - 4)
  const maxTop: number = Math.max(0, window.innerHeight - height - 4)
  return {
    left: Math.min(Math.max(4, left), maxLeft),
    top: Math.min(Math.max(4, top), maxTop),
  }
}

/**
 * Begin dragging from the current on-screen position.
 * @param event - The pointerdown event on the handle.
 */
function startDrag(event: PointerEvent): void {
  const rect: DOMRect | undefined = rootEl.value?.getBoundingClientRect()
  if (!rect) return
  dragPointerId = event.pointerId
  startX = event.clientX
  startY = event.clientY
  startLeft = rect.left
  startTop = rect.top
  // Anchor to top/left so the drag math is consistent.
  position.value = { left: rect.left, top: rect.top }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', endDrag)
}

/**
 * Move the toolbar with the pointer.
 * @param event - The pointermove event.
 */
function onDragMove(event: PointerEvent): void {
  if (dragPointerId === null) return
  position.value = clampToViewport(startLeft + (event.clientX - startX), startTop + (event.clientY - startY))
}

/** Finish dragging and persist the position. */
function endDrag(): void {
  dragPointerId = null
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', endDrag)
  if (position.value !== null) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(position.value))
  }
}

/**
 * Pull the prod database into the local dev database, once the confirmation dialog has
 * been accepted. Shows the result (or error) via a toast. Only reachable in desktop dev
 * (button is gated + the Tauri command is compiled only into debug builds).
 * @returns A promise resolved once the sync finishes.
 */
async function syncDatabaseFromProd(): Promise<void> {
  isSyncing.value = true
  try {
    const message: string = await syncDevDatabaseFromProd()
    // Le stockage suit la base, sinon les démos pointent vers des vidéos absentes du bucket dev.
    let storageMessage: string = ''
    try {
      const storage: StorageActionResponse = await AdminStorageService.syncStorageFromProd()
      storageMessage = ` · Stockage : ${storage.message}`
    } catch (storageError) {
      storageMessage = ` · Stockage NON synchronisé (${
        storageError instanceof Error ? storageError.message : String(storageError)
      })`
    }
    toast.add({ title: 'Synchro terminée', description: `${message}${storageMessage}`, color: 'success' })
  } catch (error) {
    toast.add({
      title: 'Synchro DB — échec',
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  } finally {
    isSyncing.value = false
  }
}

onMounted((): void => {
  try {
    const raw: string | null = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed: ToolbarPosition = JSON.parse(raw) as ToolbarPosition
      if (typeof parsed.left === 'number' && typeof parsed.top === 'number') {
        // Re-clamp on load in case the window was resized since last time.
        position.value = clampToViewport(parsed.left, parsed.top)
      }
    }
  } catch {
    // Ignore malformed saved position — fall back to the default corner.
  }
})

onBeforeUnmount((): void => {
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', endDrag)
})
</script>
