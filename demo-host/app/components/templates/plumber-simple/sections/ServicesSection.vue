<template>
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
</template>

<script lang="ts" setup>
import type { ServicesBlock, Theme } from '../types'

const props = defineProps<{
  services: ServicesBlock
  theme: Theme
}>()

const serviceItems = computed(() => Array.isArray(props.services.items) ? props.services.items : [])

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
.service-card {
  animation: fadeInUp 0.5s ease-out both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
