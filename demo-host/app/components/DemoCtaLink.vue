<template>
  <a class="cta" :class="{ 'cta--pulse': props.pulse }" :href="props.href" @click="emit('click')">
    <slot />
    <svg
      class="cta__icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2.2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  </a>
</template>

<script lang="ts" setup>
import type { EmitFn } from 'vue'
import type { DemoCtaLinkEmits, DemoCtaLinkProps } from '~/types/DemoCtaLink'

/**
 * The black pill call to action of the demo pages (video, receptionist): an arrow, and, when `pulse` is on, the
 * breathing halo and periodic light sweep that nudge the visitor to click.
 */
const props: DemoCtaLinkProps = defineProps({
  href: {
    type: String,
    required: true,
  },
  pulse: {
    type: Boolean,
    default: true,
  },
})

const emit: EmitFn<DemoCtaLinkEmits> = defineEmits<DemoCtaLinkEmits>()
</script>

<style scoped>
/* The DA's signature pill; the tokens let a page recolour it, both default to the editorial ink and paper. */
.cta {
  --cta-ink: var(--demo-cta-ink, #17130d);
  --cta-paper: var(--demo-cta-paper, #f7f3ec);
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px 32px;
  border-radius: 999px;
  background: var(--cta-ink);
  color: var(--cta-paper);
  font-weight: 600;
  font-size: 15.5px;
  text-align: center;
  text-decoration: none;
  box-shadow: 0 10px 28px -12px rgba(23, 19, 13, 0.5);
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}
.cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 34px -12px rgba(23, 19, 13, 0.55);
}
.cta__icon {
  flex: none;
  transition: transform 0.18s;
}
.cta:hover .cta__icon {
  transform: translateX(3px);
}

/* Click nudge: breathing halo + periodic light sweep (the dashboard's .app-btn-celebrate, ported). */
.cta--pulse {
  overflow: hidden;
  animation: demo-cta-pulse 2.6s ease-out 1.4s infinite;
}
.cta--pulse::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 38%;
  background: linear-gradient(105deg, transparent, rgba(247, 243, 236, 0.32), transparent);
  transform: skewX(-18deg) translateX(-160%);
  animation: demo-cta-shine 2.6s ease-in-out 1.6s infinite;
  pointer-events: none;
}
@keyframes demo-cta-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(23, 19, 13, 0.35);
  }
  55%,
  100% {
    box-shadow: 0 0 0 9px transparent;
  }
}
@keyframes demo-cta-shine {
  0% {
    transform: skewX(-18deg) translateX(-160%);
  }
  42%,
  100% {
    transform: skewX(-18deg) translateX(440%);
  }
}
@media (prefers-reduced-motion: reduce) {
  .cta--pulse,
  .cta--pulse::after {
    animation: none;
  }
}
</style>
