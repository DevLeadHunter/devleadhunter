<template>
  <span class="step-check inline-flex">
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="h-full w-full">
      <path
        class="step-check__path"
        d="M5 12.5l4.2 4.3L19 7"
        stroke="currentColor"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </span>
</template>

<script lang="ts" setup>
/** Animated check mark for completed wizard steps; CSS starting-style fallback when motion is off. */
</script>

<style scoped>
.step-check {
  opacity: 1;
  transform: scale(1);
  transition:
    opacity 200ms ease-out,
    transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

.step-check__path {
  stroke-dasharray: 24;
  stroke-dashoffset: 0;
  transition: stroke-dashoffset 300ms ease-out 90ms;
}

@starting-style {
  .step-check {
    opacity: 0;
    transform: scale(0.3);
  }

  .step-check__path {
    stroke-dashoffset: 24;
  }
}

@media (prefers-reduced-motion: reduce) {
  .step-check,
  .step-check__path {
    transition: none;
  }
}
</style>
