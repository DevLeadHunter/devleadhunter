<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center"
    :style="{ backgroundColor: 'var(--app-bg, #050505)' }"
  >
    <div class="loader-ring"></div>
  </div>
</template>

<script setup lang="ts">
/**
 * Full-screen loader overlay themed by the app variables
 * (falls back to the legacy dark backdrop outside the dashboard shell).
 * @module components/ui/Loader
 */
</script>

<style scoped>
.loader-ring {
  width: 48px;
  height: 48px;
  border: 3px solid var(--app-line, rgba(255, 255, 255, 0.1));
  border-left-color: var(--app-accent, #e8a33c);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
