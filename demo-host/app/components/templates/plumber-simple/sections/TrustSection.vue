<template>
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
</template>

<script lang="ts" setup>
import type { TrustBlock, Theme } from '../types'

const props = defineProps<{
  trust: TrustBlock
  theme: Theme
}>()

const trustItems = computed(() => Array.isArray(props.trust.items) ? props.trust.items : [])
</script>

<style scoped>
.trust-card {
  animation: fadeInUp 0.6s ease-out both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
