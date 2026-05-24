<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-[#050505]">
    <div class="loader-smooth"></div>
  </div>
</template>

<script setup lang="ts">
/**
 * Full-screen loader component with smooth spinner
 * @module components/ui/Loader
 */
</script>

<style scoped>
.loader-smooth {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-left-color: #f9f9f9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
