<template>
  <section class="relative overflow-hidden pt-28 pb-20 md:pt-36 md:pb-28">
    <!-- Ambient glows -->
    <div class="landing-glow -top-32 left-1/2 h-[420px] w-[680px] -translate-x-1/2 bg-[#2BAD5F]/15"></div>
    <div class="landing-glow top-40 -right-20 h-[320px] w-[320px] bg-[#58a6ff]/10"></div>
    <!-- Subtle grid backdrop -->
    <div
      class="pointer-events-none absolute inset-0 z-0 opacity-[0.04]"
      style="
        background-image:
          linear-gradient(#f9f9f9 1px, transparent 1px), linear-gradient(90deg, #f9f9f9 1px, transparent 1px);
        background-size: 56px 56px;
        mask-image: radial-gradient(ellipse 70% 60% at 50% 0%, #000 40%, transparent 100%);
      "
    ></div>

    <div class="relative z-10 container mx-auto px-4 md:px-6 lg:px-8">
      <div class="grid items-center gap-14 lg:grid-cols-2 lg:gap-10">
        <!-- Copy -->
        <div class="mx-auto max-w-2xl text-center lg:mx-0 lg:text-left">
          <div
            class="mb-7 inline-flex items-center gap-2 rounded-full border border-[#2BAD5F]/30 bg-[#2BAD5F]/10 px-4 py-1.5"
          >
            <span class="relative flex h-2 w-2">
              <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3fb950] opacity-75"></span>
              <span class="relative inline-flex h-2 w-2 rounded-full bg-[#3fb950]"></span>
            </span>
            <span class="text-xs font-semibold tracking-wide text-[#3fb950] uppercase">{{ $t('hero.badge') }}</span>
          </div>

          <h1 class="mb-6 text-4xl leading-[1.1] font-bold tracking-tight text-[#f9f9f9] md:text-5xl lg:text-6xl">
            {{ $t('hero.title') }}
            <span class="text-gradient-emerald">{{ $t('hero.titleHighlight') }}</span>
          </h1>

          <p class="mx-auto mb-9 max-w-xl text-base leading-relaxed text-[#8b949e] md:text-lg lg:mx-0">
            {{ $t('hero.subtitle') }}
          </p>

          <div class="flex flex-col items-center gap-3 sm:flex-row lg:items-start lg:justify-start">
            <NuxtLink :to="localePath('/signup')" class="btn-emerald w-full py-3.5 text-base sm:w-auto">
              {{ $t('hero.ctaPrimary') }}
              <i class="fa-solid fa-arrow-right text-sm"></i>
            </NuxtLink>
            <button type="button" class="btn-ghost w-full py-3.5 text-base sm:w-auto" @click="emit('discover')">
              <i class="fa-solid fa-play text-xs"></i>
              {{ $t('hero.ctaSecondary') }}
            </button>
          </div>

          <!-- Trust row -->
          <div
            class="mt-7 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-[#8b949e] lg:justify-start"
          >
            <span class="inline-flex items-center gap-1.5">
              <i class="fa-solid fa-circle-check text-[#3fb950]"></i>{{ $t('hero.trust.freeCredits') }}
            </span>
            <span class="inline-flex items-center gap-1.5">
              <i class="fa-solid fa-circle-check text-[#3fb950]"></i>{{ $t('hero.trust.noSubscription') }}
            </span>
            <span class="inline-flex items-center gap-1.5">
              <i class="fa-solid fa-circle-check text-[#3fb950]"></i>{{ $t('hero.trust.noCard') }}
            </span>
          </div>

          <!-- Platform availability -->
          <div class="mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
            <span class="text-xs font-medium tracking-wide text-[#6e7681] uppercase">{{ $t('hero.availableOn') }}</span>
            <div class="flex items-center gap-2">
              <span
                v-for="platform in platforms"
                :key="platform.label"
                class="inline-flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#1a1a1a]/60 px-2.5 py-1 text-xs font-medium text-[#c9d1d9]"
              >
                <i :class="[platform.icon, 'text-[#8b949e]']"></i>{{ platform.label }}
              </span>
            </div>
          </div>
        </div>

        <!-- Live pipeline mockup -->
        <div class="relative mx-auto w-full max-w-md lg:max-w-none">
          <div
            class="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-br from-[#2BAD5F]/20 via-transparent to-[#58a6ff]/10 blur-2xl"
          ></div>
          <div class="rounded-2xl border border-[#30363d] bg-[#0d1117]/90 p-5 shadow-2xl backdrop-blur-sm md:p-6">
            <!-- Card header -->
            <div class="mb-5 flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[#2BAD5F]/15">
                  <i class="fa-solid fa-bolt text-sm text-[#3fb950]"></i>
                </span>
                <span class="text-sm font-semibold text-[#f9f9f9]">{{ $t('hero.mockup.title') }}</span>
              </div>
              <span
                class="inline-flex items-center gap-1.5 rounded-full bg-[#2BAD5F]/10 px-2.5 py-1 text-xs font-medium text-[#3fb950]"
              >
                <span class="h-1.5 w-1.5 rounded-full bg-[#3fb950]"></span>{{ $t('hero.mockup.live') }}
              </span>
            </div>

            <!-- Steps -->
            <ol class="relative space-y-3">
              <li
                v-for="(step, index) in mockupSteps"
                :key="index"
                class="flex items-center gap-3 rounded-xl border bg-[#161b22] p-3 transition-colors"
                :class="step.done ? 'border-[#2BAD5F]/30' : 'border-[#30363d]'"
              >
                <span
                  class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg"
                  :class="step.done ? 'bg-[#2BAD5F]/15 text-[#3fb950]' : 'bg-[#21262d] text-[#8b949e]'"
                >
                  <i :class="['fa-solid', step.icon, 'text-sm']"></i>
                </span>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold text-[#f9f9f9]">{{ step.title }}</p>
                  <p class="truncate text-xs text-[#8b949e]">{{ step.detail }}</p>
                </div>
                <i
                  v-if="step.done"
                  class="fa-solid fa-circle-check flex-shrink-0 text-base text-[#3fb950]"
                  aria-hidden="true"
                ></i>
                <span
                  v-else
                  class="h-4 w-4 flex-shrink-0 animate-spin rounded-full border-2 border-[#30363d] border-t-[#3fb950]"
                  aria-hidden="true"
                ></span>
              </li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'

/** A platform availability pill. */
interface PlatformPill {
  icon: string
  label: string
}

/** A step shown in the live pipeline mockup. */
interface MockupStep {
  icon: string
  title: string
  detail: string
  done: boolean
}

const localePath = useLocalePath()
const { t } = useI18n()

const emit = defineEmits<{
  (e: 'discover'): void
}>()

/**
 * Platform availability pills displayed under the hero CTAs.
 */
const platforms: ComputedRef<PlatformPill[]> = computed((): PlatformPill[] => [
  { icon: 'fa-solid fa-globe', label: 'Web' },
  { icon: 'fa-brands fa-windows', label: 'Windows' },
  { icon: 'fa-brands fa-apple', label: 'macOS' },
  { icon: 'fa-solid fa-mobile-screen', label: 'Mobile' },
])

/**
 * Steps rendered in the live pipeline mockup card.
 */
const mockupSteps: ComputedRef<MockupStep[]> = computed((): MockupStep[] => [
  { icon: 'fa-magnifying-glass', title: t('hero.mockup.step1'), detail: t('hero.mockup.step1detail'), done: true },
  { icon: 'fa-wand-magic-sparkles', title: t('hero.mockup.step2'), detail: t('hero.mockup.step2detail'), done: true },
  { icon: 'fa-paper-plane', title: t('hero.mockup.step3'), detail: t('hero.mockup.step3detail'), done: true },
  {
    icon: 'fa-circle-dollar-to-slot',
    title: t('hero.mockup.step4'),
    detail: t('hero.mockup.step4detail'),
    done: false,
  },
])
</script>
