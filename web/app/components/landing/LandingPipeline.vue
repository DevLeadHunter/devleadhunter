<template>
  <section id="how-it-works" class="relative scroll-mt-20 overflow-hidden bg-[#050505] py-24 md:py-32">
    <div class="landing-glow top-1/4 left-1/2 h-[300px] w-[600px] -translate-x-1/2 bg-[#2BAD5F]/8"></div>

    <div class="relative z-10 container mx-auto px-4 md:px-6 lg:px-8">
      <!-- Metrics band -->
      <div v-reveal class="mx-auto mb-20 max-w-4xl">
        <div
          class="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-[#30363d] bg-[#30363d] md:grid-cols-4"
        >
          <div v-for="metric in metrics" :key="metric.label" class="bg-[#0d1117] px-4 py-6 text-center">
            <div class="mb-1 text-3xl font-bold text-[#f9f9f9] md:text-4xl">{{ metric.value }}</div>
            <div class="text-xs font-medium tracking-wide text-[#8b949e] uppercase md:text-sm">{{ metric.label }}</div>
          </div>
        </div>
      </div>

      <!-- Heading -->
      <div class="mx-auto mb-16 max-w-2xl text-center">
        <div
          v-reveal
          class="mb-5 inline-flex items-center gap-2 rounded-full border border-[#2BAD5F]/30 bg-[#2BAD5F]/10 px-4 py-1.5"
        >
          <i class="fa-solid fa-diagram-project text-xs text-[#3fb950]"></i>
          <span class="text-xs font-semibold tracking-wide text-[#3fb950] uppercase">{{ $t('pipeline.badge') }}</span>
        </div>
        <h2 v-reveal class="mb-5 text-3xl font-bold tracking-tight text-[#f9f9f9] md:text-4xl lg:text-5xl">
          {{ $t('pipeline.title') }}
        </h2>
        <p v-reveal class="text-base leading-relaxed text-[#8b949e] md:text-lg">{{ $t('pipeline.subtitle') }}</p>
      </div>

      <!-- Steps -->
      <div class="mx-auto grid max-w-6xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="(step, index) in steps"
          :key="index"
          v-reveal="{ delay: (index % 3) * 80 }"
          class="group relative overflow-hidden rounded-2xl border border-[#30363d] bg-[#0d1117] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#2BAD5F]/40"
        >
          <div
            class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#2BAD5F]/50 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          ></div>
          <div class="mb-5 flex items-center justify-between">
            <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-[#2BAD5F]/10 text-[#3fb950]">
              <i :class="['fa-solid', step.icon, 'text-lg']"></i>
            </span>
            <span class="font-mono text-2xl font-bold text-[#21262d] transition-colors group-hover:text-[#2BAD5F]/30">
              {{ step.number }}
            </span>
          </div>
          <h3 class="mb-2 text-lg font-semibold text-[#f9f9f9]">{{ step.title }}</h3>
          <p class="text-sm leading-relaxed text-[#8b949e]">{{ step.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'

/** A KPI shown in the metrics band. */
interface PipelineMetric {
  value: string
  label: string
}

/** A pipeline step card. */
interface PipelineStep {
  number: string
  icon: string
  title: string
  description: string
}

const { t } = useI18n()

/**
 * Honest, capability-based metrics (no invented vanity numbers).
 */
const metrics: ComputedRef<PipelineMetric[]> = computed((): PipelineMetric[] => [
  { value: t('metrics.sourcesValue'), label: t('metrics.sources') },
  { value: t('metrics.stepsValue'), label: t('metrics.steps') },
  { value: t('metrics.demoValue'), label: t('metrics.demo') },
  { value: t('metrics.subscriptionValue'), label: t('metrics.subscription') },
])

/**
 * The six automated pipeline steps, in order.
 */
const steps: ComputedRef<PipelineStep[]> = computed((): PipelineStep[] => [
  {
    number: '01',
    icon: 'fa-magnifying-glass',
    title: t('pipeline.step1.title'),
    description: t('pipeline.step1.description'),
  },
  { number: '02', icon: 'fa-images', title: t('pipeline.step2.title'), description: t('pipeline.step2.description') },
  {
    number: '03',
    icon: 'fa-wand-magic-sparkles',
    title: t('pipeline.step3.title'),
    description: t('pipeline.step3.description'),
  },
  { number: '04', icon: 'fa-globe', title: t('pipeline.step4.title'), description: t('pipeline.step4.description') },
  {
    number: '05',
    icon: 'fa-paper-plane',
    title: t('pipeline.step5.title'),
    description: t('pipeline.step5.description'),
  },
  { number: '06', icon: 'fa-rocket', title: t('pipeline.step6.title'), description: t('pipeline.step6.description') },
])
</script>
