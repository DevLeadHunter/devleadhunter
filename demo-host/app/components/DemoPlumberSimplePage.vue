<template>
  <div class="plumber-site" :style="cssVars">
    <!-- Nav -->
    <nav class="fixed inset-x-0 top-0 z-50 border-b border-white/10 backdrop-blur-md" :style="{ backgroundColor: `${theme.secondary}ee` }">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <span class="text-lg font-bold text-white">{{ hero.title || businessName }}</span>
        <a
          v-if="hero.phone"
          :href="`tel:${hero.phone}`"
          class="hidden rounded-full px-5 py-2 text-sm font-semibold text-white shadow-lg transition hover:scale-105 sm:inline-flex"
          :style="{ backgroundColor: theme.accent }"
        >
          {{ hero.cta_label || 'Appeler' }}
        </a>
      </div>
    </nav>

    <!-- Hero -->
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

    <!-- Trust stats -->
    <section v-if="trustItems.length" class="border-b border-slate-200 bg-white py-12">
      <div class="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-6 md:grid-cols-4">
        <div
          v-for="(item, index) in trustItems"
          :key="index"
          class="trust-card text-center"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <p class="text-3xl font-extrabold md:text-4xl" :style="{ color: theme.primary }">{{ item.value }}</p>
          <p class="mt-1 text-sm font-medium text-slate-600">{{ item.label }}</p>
        </div>
      </div>
    </section>

    <!-- Services -->
    <section class="bg-slate-50 px-6 py-20">
      <div class="mx-auto max-w-6xl">
        <div class="text-center">
          <h2 class="text-3xl font-bold text-slate-900 md:text-4xl">{{ services.heading || 'Nos services' }}</h2>
          <p v-if="services.subheading" class="mx-auto mt-4 max-w-2xl text-slate-600">{{ services.subheading }}</p>
        </div>
        <div class="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <article
            v-for="(item, index) in serviceItems"
            :key="index"
            class="service-card group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-xl"
            :style="{ animationDelay: `${index * 0.08}s` }"
          >
            <div
              class="mb-4 flex h-12 w-12 items-center justify-center rounded-xl text-white transition group-hover:scale-110"
              :style="{ backgroundColor: theme.primary }"
            >
              <span class="text-xl">{{ serviceIcon(item.icon) }}</span>
            </div>
            <h3 class="text-lg font-bold text-slate-900">{{ item.label }}</h3>
            <p v-if="item.description" class="mt-2 text-sm leading-relaxed text-slate-600">{{ item.description }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- Why us -->
    <section v-if="whyItems.length" class="px-6 py-20" :style="{ backgroundColor: theme.secondary }">
      <div class="mx-auto max-w-6xl">
        <h2 class="text-center text-3xl font-bold text-white md:text-4xl">{{ whyUs.heading || 'Pourquoi nous choisir ?' }}</h2>
        <ul class="mt-12 grid gap-4 md:grid-cols-3">
          <li
            v-for="(item, index) in whyItems"
            :key="index"
            class="why-card flex items-start gap-4 rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm"
          >
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold" :style="{ backgroundColor: theme.accent, color: theme.secondary }">✓</span>
            <span class="text-white/90">{{ item.label }}</span>
          </li>
        </ul>
      </div>
    </section>

    <!-- Contact -->
    <section id="contact" class="bg-white px-6 py-20">
      <div class="mx-auto max-w-6xl">
        <div class="overflow-hidden rounded-3xl shadow-2xl" :style="{ background: contactGradient }">
          <div class="grid md:grid-cols-2">
            <div class="p-10 text-white md:p-14">
              <h2 class="text-3xl font-bold">{{ contact.heading || 'Contactez-nous' }}</h2>
              <p v-if="contact.subheading" class="mt-4 text-white/80">{{ contact.subheading }}</p>
              <dl class="mt-8 space-y-4">
                <div v-if="contact.phone" class="flex items-center gap-3">
                  <span class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">📞</span>
                  <div>
                    <dt class="text-xs uppercase tracking-wide text-white/60">Téléphone</dt>
                    <dd class="font-semibold">{{ contact.phone }}</dd>
                  </div>
                </div>
                <div v-if="contact.email" class="flex items-center gap-3">
                  <span class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">✉️</span>
                  <div>
                    <dt class="text-xs uppercase tracking-wide text-white/60">Email</dt>
                    <dd class="font-semibold">{{ contact.email }}</dd>
                  </div>
                </div>
                <div v-if="contact.city" class="flex items-center gap-3">
                  <span class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">📍</span>
                  <div>
                    <dt class="text-xs uppercase tracking-wide text-white/60">Zone</dt>
                    <dd class="font-semibold">{{ contact.city }}</dd>
                  </div>
                </div>
              </dl>
            </div>
            <div class="flex flex-col justify-center bg-white p-10 md:p-14">
              <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Devis gratuit</p>
              <p class="mt-2 text-2xl font-bold text-slate-900">Réponse sous 2 heures</p>
              <p class="mt-4 text-slate-600">Décrivez votre besoin — nous vous rappelons rapidement avec un devis transparent.</p>
              <a
                v-if="contact.phone"
                :href="`tel:${contact.phone}`"
                class="mt-8 inline-flex w-fit items-center justify-center rounded-xl px-8 py-4 font-bold text-white transition hover:scale-[1.02]"
                :style="{ backgroundColor: theme.primary }"
              >
                Appeler maintenant
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer class="border-t border-slate-200 bg-slate-50 px-6 py-8 text-center text-xs text-slate-500">
      © {{ new Date().getFullYear() }} {{ hero.title || businessName }} · Propulsé par DevLeadHunter
    </footer>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'

const props = defineProps<{
  content: Record<string, unknown>
  businessName: string
}>()

type Block = Record<string, unknown>
type Theme = { primary: string; secondary: string; accent: string }

const defaultTheme: Theme = { primary: '#0284c7', secondary: '#0f172a', accent: '#f59e0b' }

const theme: ComputedRef<Theme> = computed((): Theme => {
  const raw = props.content.theme
  if (raw && typeof raw === 'object') {
    const t = raw as Record<string, string>
    return {
      primary: t.primary || defaultTheme.primary,
      secondary: t.secondary || defaultTheme.secondary,
      accent: t.accent || defaultTheme.accent,
    }
  }
  return defaultTheme
})

const cssVars = computed(() => ({
  '--color-primary': theme.value.primary,
  '--color-secondary': theme.value.secondary,
  '--color-accent': theme.value.accent,
}))

const heroGradient = computed(() =>
  `linear-gradient(135deg, ${theme.value.secondary} 0%, ${theme.value.primary} 100%)`,
)

const contactGradient = computed(() =>
  `linear-gradient(135deg, ${theme.value.primary} 0%, ${theme.value.secondary} 100%)`,
)

const blocks: ComputedRef<Block[]> = computed((): Block[] => {
  const body = props.content.body
  return Array.isArray(body) ? (body as Block[]) : []
})

const findBlock = (component: string): Block =>
  blocks.value.find((b: Block): boolean => b.component === component) ?? {}

const hero = computed(() => findBlock('hero'))
const trust = computed(() => findBlock('trust'))
const services = computed(() => findBlock('services'))
const whyUs = computed(() => findBlock('why_us'))
const contact = computed(() => findBlock('contact'))

const trustItems = computed(() => {
  const items = trust.value.items
  return Array.isArray(items) ? (items as Array<{ value?: string; label?: string }>) : []
})

const serviceItems = computed(() => {
  const items = services.value.items
  return Array.isArray(items) ? (items as Array<{ label?: string; description?: string; icon?: string }>) : []
})

const whyItems = computed(() => {
  const items = whyUs.value.items
  return Array.isArray(items) ? (items as Array<{ label?: string }>) : []
})

function serviceIcon(icon?: string): string {
  const icons: Record<string, string> = {
    emergency: '🚨',
    install: '🔧',
    heater: '♨️',
    leak: '💧',
  }
  return icons[icon ?? ''] ?? '🔧'
}
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

.trust-card {
  animation: fadeInUp 0.6s ease-out both;
}

.service-card {
  animation: fadeInUp 0.5s ease-out both;
}

.why-card {
  animation: fadeInUp 0.5s ease-out both;
}
</style>
