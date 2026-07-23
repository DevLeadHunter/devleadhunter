<template>
  <section id="sale-automation" class="px-5 py-24 md:px-8 md:py-36">
    <div class="mx-auto max-w-6xl">
      <div class="grid items-center gap-14 lg:grid-cols-[1fr_1.15fr] lg:gap-20">
        <div>
          <p v-reveal class="landing-eyebrow">{{ $t('landing.sale.eyebrow') }}</p>
          <h2
            v-reveal="{ delay: 80 }"
            class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
          >
            {{ $t('landing.sale.title') }}
          </h2>
          <p v-reveal="{ delay: 160 }" class="mt-5 max-w-lg text-lg leading-relaxed text-[#6b6355]">
            {{ $t('landing.sale.description') }}
          </p>
          <ul class="mt-8 max-w-lg">
            <li
              v-for="(bulletKey, index) in bulletKeys"
              :key="bulletKey"
              v-reveal="{ delay: 220 + index * 70 }"
              class="flex items-start gap-3 border-t border-[#e3dccd] py-4 text-base text-[#1b1813]"
            >
              <i class="fa-solid fa-check mt-1 text-sm text-[#e8a33c]" aria-hidden="true"></i>
              {{ $t(bulletKey) }}
            </li>
          </ul>
        </div>

        <div v-reveal="{ delay: 150 }">
          <div ref="orderCardRef" class="landing-card landing-tilt mx-auto max-w-md p-6 md:p-7 lg:mx-0 lg:ml-auto">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
                  {{ $t('landing.sale.card.label') }}
                </p>
                <p class="font-display mt-2 text-2xl font-semibold text-[#1b1813]">
                  {{ $t('landing.sale.card.name') }}
                </p>
              </div>

              <span
                class="rounded-full bg-[#635bff] px-3.5 py-1 font-sans text-xs font-bold tracking-tight text-white lowercase"
              >
                {{ $t('landing.sale.card.provider') }}
              </span>
            </div>

            <ol class="mt-6 space-y-4 border-t border-dashed border-[#e3dccd] pt-5">
              <li
                v-for="(stepKey, index) in stepKeys"
                :key="stepKey"
                class="flex items-start gap-3 text-sm transition-colors duration-300"
                :class="stepState(index) === 'pending' ? 'text-[#6b6355]/50' : 'text-[#1b1813]'"
              >
                <span class="mt-0.5 w-4 shrink-0 text-center" aria-hidden="true">
                  <i v-if="stepState(index) === 'done'" class="fa-solid fa-circle-check text-sm text-[#e8a33c]"></i>
                  <i
                    v-else-if="stepState(index) === 'active'"
                    class="fa-solid fa-circle-notch fa-spin text-sm text-[#e8a33c]"
                  ></i>
                  <i v-else class="fa-regular fa-circle text-sm text-[#e3dccd]"></i>
                </span>
                {{ $t(stepKey) }}
              </li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { LandingSaleStepState } from '~/types/LandingSaleAutomation'
import type { Ref } from 'vue'
import { ref, onMounted, onBeforeUnmount } from 'vue'

/** i18n keys of the four sale bullets. */
const bulletKeys: string[] = [
  'landing.sale.bullet1',
  'landing.sale.bullet2',
  'landing.sale.bullet3',
  'landing.sale.bullet4',
]

/** i18n keys of the four fulfilment steps played in the order card. */
const stepKeys: string[] = [
  'landing.sale.card.step1',
  'landing.sale.card.step2',
  'landing.sale.card.step3',
  'landing.sale.card.step4',
]

/** Order card element, observed to start the animation when visible. */
const orderCardRef: Ref<HTMLElement | null> = ref(null)

/** Number of completed steps (0 → stepKeys.length; the loop resets it). */
const completedStepCount: Ref<number> = ref(0)

/** Pending timer of the animation loop. */
let cycleTimer: ReturnType<typeof setTimeout> | null = null

/** Observer that arms the animation once the card scrolls into view. */
let visibilityObserver: IntersectionObserver | null = null

/**
 * Resolve the visual state of a fulfilment step row.
 * @param index - Index of the step row.
 * @returns Whether the step is done, currently running or still pending.
 */
function stepState(index: number): LandingSaleStepState {
  if (index < completedStepCount.value) {
    return 'done'
  }
  if (index === completedStepCount.value && completedStepCount.value < stepKeys.length) {
    return 'active'
  }
  return 'pending'
}

/**
 * Advance the fulfilment animation by one step, hold once complete,
 * then loop back to the start.
 */
function scheduleNextStep(): void {
  const isComplete: boolean = completedStepCount.value >= stepKeys.length
  const delay: number = isComplete ? 3200 : 950
  cycleTimer = setTimeout((): void => {
    completedStepCount.value = isComplete ? 0 : completedStepCount.value + 1
    scheduleNextStep()
  }, delay)
}

onMounted((): void => {
  const prefersReducedMotion: boolean = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReducedMotion || typeof IntersectionObserver === 'undefined') {
    // Static fallback: show the order fully fulfilled.
    completedStepCount.value = stepKeys.length
    return
  }

  visibilityObserver = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      for (const entry of entries) {
        if (entry.isIntersecting && cycleTimer === null) {
          scheduleNextStep()
          visibilityObserver?.disconnect()
        }
      }
    },
    { threshold: 0.35 },
  )

  if (orderCardRef.value) {
    visibilityObserver.observe(orderCardRef.value)
  }
})

onBeforeUnmount((): void => {
  if (cycleTimer !== null) {
    clearTimeout(cycleTimer)
    cycleTimer = null
  }
  visibilityObserver?.disconnect()
  visibilityObserver = null
})
</script>
