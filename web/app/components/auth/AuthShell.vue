<template>
  <div class="landing-theme relative min-h-screen">
    <!-- Paper grain over the whole page (same treatment as the landing) -->
    <div class="landing-grain"></div>

    <div class="flex min-h-screen">
      <!-- Editorial poster panel (paper, desktop only) -->
      <aside class="relative hidden overflow-hidden lg:flex lg:flex-1 lg:flex-col">
        <!-- Wordmark -->
        <div class="px-10 pt-8">
          <NuxtLink :to="localePath('/')" class="inline-flex items-center gap-2.5" aria-label="DevLeadHunter">
            <svg
              class="h-4 w-4 fill-current text-[#1b1813]"
              viewBox="0 0 493 515"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
                fill="currentColor"
              />
            </svg>
            <span class="text-sm font-semibold tracking-tight text-[#1b1813]">devleadhunter</span>
          </NuxtLink>
        </div>

        <!-- Monumental asterisk, cropped on the right edge, in ceremonial slow spin -->
        <span class="pointer-events-none absolute top-1/2 -right-44 -translate-y-1/2 select-none" aria-hidden="true">
          <LandingAsterisk class="auth-spin-slow block text-[36rem] text-[#e8a33c]/15" />
        </span>

        <!-- Stacked pipeline words -->
        <div class="relative z-10 flex flex-1 items-center px-10 xl:px-16">
          <div>
            <h2
              class="font-display text-[4.25rem] leading-[1.02] font-semibold tracking-[-0.025em] text-[#1b1813] xl:text-[5.25rem]"
            >
              <span
                v-for="(wordKey, index) in wordKeys"
                :key="wordKey"
                class="auth-rise block"
                :style="{ animationDelay: `${120 + index * 110}ms` }"
              >
                <em v-if="index === 1" class="font-medium italic">{{ $t(wordKey) }}</em>
                <template v-else>{{ $t(wordKey) }}</template>
                <span class="text-[#e8a33c]" aria-hidden="true">.</span>
              </span>
            </h2>
            <p
              class="auth-rise mt-7 max-w-sm text-base leading-relaxed text-[#6b6355]"
              :style="{ animationDelay: `${120 + wordKeys.length * 110 + 130}ms` }"
            >
              {{ mode === 'signup' ? $t('auth.panel.signupLine') : $t('auth.panel.loginLine') }}
            </p>
          </div>
        </div>

        <!-- Trades ticker — ambient motion, edge to edge -->
        <div class="auth-rise relative z-10 pb-10" :style="{ animationDelay: '650ms' }">
          <LandingTradesTicker />
        </div>
      </aside>

      <!-- Form column (raised paper) -->
      <div class="relative flex w-full flex-col border-[#e3dccd] bg-[#fcfaf5] lg:w-[44%] lg:border-l xl:w-[40%]">
        <div class="flex items-center justify-between px-6 pt-6 md:px-10">
          <NuxtLink :to="localePath('/')" class="inline-flex items-center gap-2.5 lg:hidden" aria-label="DevLeadHunter">
            <svg
              class="h-4 w-4 fill-current text-[#1b1813]"
              viewBox="0 0 493 515"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
                fill="currentColor"
              />
            </svg>
            <span class="text-sm font-semibold tracking-tight text-[#1b1813]">devleadhunter</span>
          </NuxtLink>
          <NuxtLink :to="localePath('/')" class="landing-link ml-auto text-xs">{{ $t('auth.backHome') }}</NuxtLink>
        </div>

        <div class="flex flex-1 items-center justify-center px-6 py-12 md:px-12">
          <div class="w-full max-w-sm">
            <slot />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { AuthShellMode } from '~/types/AuthShell'

/**
 * Split-screen shell for the auth pages (login / signup) — « l'affiche de
 * l'atelier ». Left (desktop only): an airy editorial poster on paper — the
 * three pipeline words stacked in Fraunces, a monumental amber asterisk in
 * ceremonial slow spin, the trades ticker as ambient motion. Right: raised
 * paper column hosting the form (slot). Mode drives the poster copy.
 */
const props = defineProps({
  mode: {
    type: String as PropType<AuthShellMode>,
    required: true,
  },
})

const localePath = useLocalePath()

/**
 * i18n keys of the stacked poster words (signup: the pipeline; login: the
 * welcome-back greeting).
 */
const wordKeys: ComputedRef<string[]> = computed((): string[] =>
  props.mode === 'signup'
    ? ['auth.panel.signupWord1', 'auth.panel.signupWord2', 'auth.panel.signupWord3']
    : ['auth.panel.loginWord1', 'auth.panel.loginWord2'],
)
</script>
