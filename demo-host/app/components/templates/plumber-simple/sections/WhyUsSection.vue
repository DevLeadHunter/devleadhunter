<template>
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
</template>

<script lang="ts" setup>
import type { WhyUsBlock, Theme } from '../types'

const props = defineProps<{
  whyUs: WhyUsBlock
  theme: Theme
}>()

const whyItems = computed(() => Array.isArray(props.whyUs.items) ? props.whyUs.items : [])
</script>

<style scoped>
.why-card {
  animation: fadeInUp 0.5s ease-out both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
