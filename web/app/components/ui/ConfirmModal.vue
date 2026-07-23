<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-sm"
      :style="{ backgroundColor: 'var(--app-overlay, rgba(0, 0, 0, 0.7))' }"
      @click.self="handleCancel"
    >
      <div class="app-card mx-4 w-full max-w-md p-6 shadow-[var(--app-shadow-soft)]">
        <h2 class="font-display mb-2 text-lg font-semibold text-[var(--app-ink)]">{{ props.title }}</h2>
        <p class="mb-6 text-sm leading-relaxed text-[var(--app-ink-soft)]">{{ props.message }}</p>

        <div class="flex gap-3">
          <button class="app-btn-secondary flex-1" @click="handleCancel">
            {{ props.cancelText }}
          </button>
          <button class="app-btn-danger flex-1" @click="handleConfirm">
            {{ props.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref } from 'vue'
import type { UiConfirmModalProps } from '~/types/UiConfirmModal'

/** Confirm/cancel dialog whose labels are all overridable. */
const props: UiConfirmModalProps = defineProps({
  title: {
    type: String,
    default: 'Confirmer',
  },
  message: {
    type: String,
    default: 'Êtes-vous sûr ?',
  },
  confirmText: {
    type: String,
    default: 'Confirmer',
  },
  cancelText: {
    type: String,
    default: 'Annuler',
  },
})

const emit = defineEmits<{
  (e: 'confirm' | 'cancel'): void
}>()

/** Whether the modal is visible. */
const isOpen: Ref<boolean> = ref(false)

/**
 * Open the modal.
 */
function open(): void {
  isOpen.value = true
}

/**
 * Close the modal.
 */
function close(): void {
  isOpen.value = false
}

/**
 * Confirm and close.
 */
function handleConfirm(): void {
  emit('confirm')
  close()
}

/**
 * Cancel and close.
 */
function handleCancel(): void {
  emit('cancel')
  close()
}

defineExpose({
  open,
  close,
})
</script>
