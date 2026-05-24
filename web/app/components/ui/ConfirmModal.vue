<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
    @click.self="handleCancel"
  >
    <div class="border-muted mx-4 w-full max-w-md rounded-lg border bg-[#1a1a1a] p-6">
      <h2 class="mb-3 text-base font-semibold text-[#f9f9f9]">{{ title }}</h2>
      <p class="text-muted mb-6 text-sm">{{ message }}</p>

      <div class="flex gap-3">
        <button class="btn-secondary flex-1" @click="handleCancel">
          {{ cancelText }}
        </button>
        <button class="btn-danger flex-1" @click="handleConfirm">
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(
  defineProps<{
    title?: string
    message?: string
    confirmText?: string
    cancelText?: string
  }>(),
  {
    title: 'Confirm',
    message: 'Are you sure?',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
  },
)

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const isOpen = ref(false)

const open = () => {
  isOpen.value = true
}

const close = () => {
  isOpen.value = false
}

const handleConfirm = () => {
  emit('confirm')
  close()
}

const handleCancel = () => {
  emit('cancel')
  close()
}

defineExpose({
  open,
  close,
})
</script>
