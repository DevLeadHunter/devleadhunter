<template>
  <section id="etapes" class="steps">
    <div class="section-head">
      <p class="kicker kicker-light">En toute simplicité</p>
      <h2 class="section-title section-title-light reveal" data-reveal>
        {{ steps.heading || 'Comment ça se passe' }}
      </h2>
      <p v-if="steps.subheading" class="section-lede section-lede-light reveal" data-reveal style="--d: 80ms">
        {{ steps.subheading }}
      </p>
    </div>
    <ol ref="stepsList" class="step-list">
      <span class="step-line" aria-hidden="true"><span ref="stepProgress" class="step-line-fill"></span></span>
      <li
        v-for="(s, i) in stepItems"
        :key="i"
        class="step reveal"
        data-reveal
        :style="{ '--d': `${i * 90}ms` }"
      >
        <span class="step-num">{{ String(i + 1).padStart(2, '0') }}</span>
        <span class="step-ico"><svg viewBox="0 0 24 24" aria-hidden="true" v-html="icon(s.icon || 'phone')" /></span>
        <h3 class="step-title">{{ s.title }}</h3>
        <p v-if="s.description" class="step-desc">{{ s.description }}</p>
      </li>
    </ol>
  </section>
</template>

<script lang="ts" setup>
import type { StepsBlock } from '../types'
import { icon } from '../utils'

defineProps<{
  steps: StepsBlock
  stepItems: { title?: string; description?: string; icon?: string }[]
}>()

/* ── Remplissage de la ligne des étapes au scroll (GSAP) ── */
const stepsList = ref<HTMLElement | null>(null)
const stepProgress = ref<HTMLElement | null>(null)
let cleanup: Array<() => void> = []

onMounted(async (): Promise<void> => {
  if (!import.meta.client) return

  try {
    const gsapMod = await import('gsap')
    const stMod = await import('gsap/ScrollTrigger')
    const gsap = gsapMod.gsap ?? gsapMod.default
    const ScrollTrigger = stMod.ScrollTrigger ?? stMod.default
    gsap.registerPlugin(ScrollTrigger)

    if (stepsList.value && stepProgress.value) {
      gsap.fromTo(
        stepProgress.value,
        { scaleX: 0 },
        {
          scaleX: 1,
          ease: 'none',
          scrollTrigger: { trigger: stepsList.value, start: 'top 75%', end: 'bottom 60%', scrub: true },
        },
      )
    }
    cleanup.push(() => ScrollTrigger.getAll().forEach((t: { kill: () => void }) => t.kill()))
  } catch {
    /* GSAP indisponible : les reveals CSS/IO suffisent. */
  }
})

onBeforeUnmount((): void => {
  cleanup.forEach((fn) => fn())
  cleanup = []
})
</script>

<style scoped>
/* ════════════ Étapes (section sombre) ════════════ */
.steps {
  background: var(--ink);
  color: var(--paper);
  padding: clamp(3.5rem, 7vw, 6rem) 0;
}
/* #etapes au lieu de `.steps` : préserve la victoire de spécificité de l'override
   face à la règle de base `.sig :deep(.section-head)` (même élément, sortie identique). */
#etapes .section-head {
  margin-bottom: clamp(2rem, 4vw, 3rem);
}
.step-list {
  position: relative;
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 1.5rem;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
}
.step-line {
  position: absolute;
  top: 1.25rem;
  left: calc(1.5rem + 12.5%);
  right: calc(1.5rem + 12.5%);
  height: 2px;
  background: color-mix(in srgb, var(--paper) 16%, transparent);
}
.step-line-fill {
  display: block;
  height: 100%;
  width: 100%;
  background: var(--signal);
  transform: scaleX(0);
  transform-origin: left center;
}
.step {
  position: relative;
}
.step-num {
  display: inline-grid;
  place-items: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: var(--ink);
  border: 2px solid var(--signal);
  color: var(--signal);
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
  position: relative;
  z-index: 1;
}
.step-ico {
  display: block;
  margin-top: 1.1rem;
  color: color-mix(in srgb, var(--paper) 80%, transparent);
}
.step-ico :deep(svg) {
  width: 1.7rem;
  height: 1.7rem;
}
.step-title {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 650;
  font-size: 1.18rem;
  margin-top: 0.7rem;
  letter-spacing: -0.01em;
}
.step-desc {
  margin-top: 0.4rem;
  color: color-mix(in srgb, var(--paper) 64%, transparent);
  font-size: 0.95rem;
}

/* ════════════ Responsive ════════════ */
@media (max-width: 980px) {
  .step-list {
    grid-template-columns: repeat(2, 1fr);
    gap: 2rem 1.5rem;
  }
  .step-line {
    display: none;
  }
}

@media (max-width: 680px) {
  .step-list {
    grid-template-columns: 1fr;
  }
}
</style>
