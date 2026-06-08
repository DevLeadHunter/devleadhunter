<template>
  <header class="hero-section relative overflow-hidden pt-24" :style="{ background: heroGradient }">
    <div class="hero-blob hero-blob-1"></div>
    <div class="hero-blob hero-blob-2"></div>
    <div class="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
      <span
        v-if="hero.badge"
        class="hero-fade-in inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-xs font-medium uppercase tracking-wider text-white"
      >
        <span class="pulse-dot h-2 w-2 rounded-full bg-emerald-400"></span>
        {{ hero.badge }}
      </span>
      <h1 class="hero-fade-in hero-fade-in-delay-1 mt-6 max-w-3xl text-4xl font-extrabold leading-tight text-white md:text-6xl">
        {{ hero.title || businessName }}
      </h1>
      <p class="hero-fade-in hero-fade-in-delay-2 mt-6 max-w-2xl text-lg text-white/85 md:text-xl">
        {{ hero.subtitle }}
      </p>
      <div class="hero-fade-in hero-fade-in-delay-3 mt-10 flex flex-wrap gap-4">
        <a
          v-if="hero.phone"
          :href="`tel:${hero.phone}`"
          class="inline-flex items-center gap-2 rounded-xl px-8 py-4 text-base font-bold shadow-xl transition hover:scale-[1.02] hover:shadow-2xl"
          :style="{ backgroundColor: theme.accent, color: theme.secondary }"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
          {{ hero.cta_label || 'Appeler maintenant' }} — {{ hero.phone }}
        </a>
        <a
          href="#contact"
          class="inline-flex items-center gap-2 rounded-xl border-2 border-white/30 px-8 py-4 text-base font-semibold text-white transition hover:bg-white/10"
        >
          Demander un devis
        </a>
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
import type { HeroBlock, Theme } from '../types'

const props = defineProps<{
  hero: HeroBlock
  theme: Theme
  businessName: string
}>()

const heroGradient = computed(() =>
  `linear-gradient(135deg, ${props.theme.secondary} 0%, ${props.theme.primary} 100%)`,
)
</script>

<style scoped>
.hero-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  animation: float 8s ease-in-out infinite;
}
.hero-blob-1 {
  top: -10%;
  right: -5%;
  width: 400px;
  height: 400px;
  background: var(--color-accent);
}
.hero-blob-2 {
  bottom: -20%;
  left: -10%;
  width: 300px;
  height: 300px;
  background: white;
  animation-delay: -4s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, -20px) scale(1.05); }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

.hero-fade-in {
  animation: fadeInUp 0.7s ease-out both;
}
.hero-fade-in-delay-1 { animation-delay: 0.1s; }
.hero-fade-in-delay-2 { animation-delay: 0.2s; }
.hero-fade-in-delay-3 { animation-delay: 0.35s; }

.pulse-dot {
  animation: pulse 2s ease-in-out infinite;
}
</style>
