<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm"
    @click.self="handleCancel"
  >
    <div class="bg-[#1a1a1a] border border-muted rounded-lg p-6 w-full max-w-md mx-4">
      <h2 class="text-base font-semibold text-[#f9f9f9] mb-3">{{ title }}</h2>
      <p class="text-sm text-muted mb-6">{{ message }}</p>
      
      <div class="flex gap-3">
        <button
          @click="handleCancel"
          class="btn-secondary flex-1"
        >
          {{ cancelText }}
        </button>
        <button
          @click="handleConfirm"
          class="btn-danger flex-1"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const props = withDefaults(defineProps<{
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
}>(), {
  title: 'Confirm',
  message: 'Are you sure?',
  confirmText: 'Confirm',
  cancelText: 'Cancel'
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const isOpen = ref(false);

const open = () => {
  isOpen.value = true;
};

const close = () => {
  isOpen.value = false;
};

const handleConfirm = () => {
  emit('confirm');
  close();
};

const handleCancel = () => {
  emit('cancel');
  close();
};

defineExpose({
  open,
  close
});
</script>

