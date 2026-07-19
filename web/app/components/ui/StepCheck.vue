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
/**
 * A small, satisfying check mark that pops and draws itself in on mount.
 *
 * Sized and coloured by the parent (``currentColor`` stroke) — e.g.
 * ``<UiStepCheck class="h-4 w-4 text-[var(--app-green)]" />``. Used to reward a
 * completed step in wizard/stepper flows. Respects ``prefers-reduced-motion``.
 */
</script>

<style scoped>
.step-check {
  animation: step-check-pop 320ms cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.step-check__path {
  stroke-dasharray: 24;
  stroke-dashoffset: 24;
  animation: step-check-draw 300ms 90ms ease-out forwards;
}

@keyframes step-check-pop {
  0% {
    transform: scale(0.3);
    opacity: 0;
  }
  60% {
    transform: scale(1.12);
    opacity: 1;
  }
  100% {
    transform: scale(1);
  }
}

@keyframes step-check-draw {
  to {
    stroke-dashoffset: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .step-check {
    animation: none;
  }
  .step-check__path {
    animation: none;
    stroke-dashoffset: 0;
  }
}
</style>
