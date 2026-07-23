<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed right-4 bottom-4 z-[70] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-3.5 shadow-lg shadow-black/5"
        >
          <span
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
            :style="{ backgroundColor: TOAST_STYLE[toast.type].tileBg }"
          >
            <UIcon
              :name="TOAST_STYLE[toast.type].icon"
              class="h-4 w-4"
              :style="{ color: TOAST_STYLE[toast.type].iconColor }"
            />
          </span>
          <p class="flex-1 pt-1 text-sm leading-snug text-[var(--app-ink)]">{{ toast.message }}</p>
          <button
            type="button"
            class="flex h-6 w-6 shrink-0 cursor-pointer items-center justify-center rounded text-[var(--app-faint)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Fermer la notification"
            @click="dismiss(toast.id)"
          >
            <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ToastToneClasses } from '~/types/UiToastHost'
import { watch } from 'vue'
import type { ToastItem, ToastType } from '~/composables/useToast'
import { useToastHost } from '~/composables/useToast'

const TOAST_STYLE: Record<ToastType, ToastToneClasses> = {
  success: { icon: 'i-lucide-check', tileBg: 'var(--app-green-soft)', iconColor: 'var(--app-green)' },
  error: { icon: 'i-lucide-circle-alert', tileBg: 'var(--app-red-soft)', iconColor: 'var(--app-red)' },
  warning: { icon: 'i-lucide-triangle-alert', tileBg: 'var(--app-accent-soft)', iconColor: 'var(--app-accent-ink)' },
  info: { icon: 'i-lucide-info', tileBg: 'var(--app-blue-soft)', iconColor: 'var(--app-blue)' },
}

const { toasts, dismiss } = useToastHost()

/** Toast ids whose auto-dismiss timer is already scheduled. */
const scheduled: Set<number> = new Set()

watch(
  toasts,
  (items: ToastItem[]): void => {
    for (const item of items) {
      if (scheduled.has(item.id)) continue
      scheduled.add(item.id)
      setTimeout((): void => {
        dismiss(item.id)
        scheduled.delete(item.id)
      }, item.duration)
    }
  },
  { deep: true },
)
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease;
}
.toast-enter-from {
  transform: translateY(8px);
  opacity: 0;
}
.toast-leave-to {
  transform: translateX(12px);
  opacity: 0;
}
.toast-move {
  transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
