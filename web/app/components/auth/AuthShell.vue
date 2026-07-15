<template>
  <div class="landing-theme min-h-screen">
    <div class="flex min-h-screen">
      <!-- Form column (paper) -->
      <div class="relative flex w-full flex-col lg:w-[44%] xl:w-[42%]">
        <div class="flex items-center justify-between px-6 pt-6 md:px-10">
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
          <NuxtLink :to="localePath('/')" class="landing-link text-xs">{{ $t('auth.backHome') }}</NuxtLink>
        </div>

        <div class="flex flex-1 items-center justify-center px-5 py-12 md:px-10">
          <div class="w-full max-w-sm">
            <slot />
          </div>
        </div>
      </div>

      <!-- Brand panel (ink, desktop only) -->
      <aside class="relative hidden overflow-hidden bg-[#14110d] lg:flex lg:flex-1">
        <!-- Amber asterisk watermark -->
        <LandingAsterisk
          class="pointer-events-none absolute -top-24 -right-20 rotate-12 text-[22rem] text-[#e8a33c]/[0.08]"
        />

        <div class="relative z-10 flex w-full flex-col justify-center px-12 py-16 xl:px-16">
          <p class="landing-eyebrow landing-eyebrow--inverse">{{ $t('auth.panel.eyebrow') }}</p>

          <h2
            class="font-display mt-6 max-w-md text-4xl leading-[1.08] font-semibold tracking-[-0.015em] text-[#fcfaf5]"
          >
            {{ mode === 'signup' ? $t('auth.panel.signupTitle') : $t('auth.panel.loginTitle') }}
          </h2>

          <p class="mt-4 max-w-md text-base leading-relaxed text-[#fcfaf5]/60">
            {{ mode === 'signup' ? $t('auth.panel.signupText') : $t('auth.panel.loginText') }}
          </p>

          <!-- App window mockup (mirrors the landing's desktop-app section) -->
          <div
            class="mt-10 max-w-lg overflow-hidden rounded-2xl border border-[#3a342b] bg-[#1b1813] shadow-[0_32px_64px_-32px_rgba(0,0,0,0.65)]"
            aria-hidden="true"
          >
            <div class="flex items-center gap-2 border-b border-[#3a342b] px-4 py-3.5">
              <span class="h-3 w-3 rounded-full bg-[#e8a33c]/80"></span>
              <span class="h-3 w-3 rounded-full bg-[#4a4438]"></span>
              <span class="h-3 w-3 rounded-full bg-[#4a4438]"></span>
              <span class="font-label ml-3 flex-1 truncate text-center text-xs text-[#f6f3ec]/50">
                devleadhunter — {{ $t('landing.desktop.window.title') }}
              </span>
            </div>

            <div class="p-6">
              <div class="grid grid-cols-3 gap-3">
                <div
                  v-for="kpi in kpis"
                  :key="kpi.labelKey"
                  class="rounded-xl border border-[#3a342b] bg-[#262119] p-4"
                >
                  <p class="font-label text-[0.6rem] tracking-[0.14em] text-[#e8a33c]/80 uppercase">
                    {{ $t(kpi.labelKey) }}
                  </p>
                  <p class="font-display mt-2 text-xl font-semibold text-[#fcfaf5]">{{ kpi.value }}</p>
                </div>
              </div>

              <div class="mt-4 space-y-2.5">
                <div
                  v-for="row in listRows"
                  :key="row"
                  class="flex items-center gap-3 rounded-xl border border-[#3a342b] bg-[#262119] px-4 py-3"
                >
                  <span class="h-7 w-7 shrink-0 rounded-full bg-[#3a342b]"></span>
                  <div class="flex-1 space-y-1.5">
                    <span class="block h-2 w-1/3 rounded-full bg-[#3a342b]"></span>
                    <span class="block h-2 w-2/3 rounded-full bg-[#3a342b]/70"></span>
                  </div>
                  <span class="h-2 w-10 rounded-full bg-[#e8a33c]/40"></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Signup: pitch bullets / Login: one quiet reassurance line -->
          <ul v-if="mode === 'signup'" class="mt-8 max-w-md space-y-3">
            <li
              v-for="bulletKey in bulletKeys"
              :key="bulletKey"
              class="flex items-start gap-3 text-sm text-[#fcfaf5]/80"
            >
              <svg
                class="mt-0.5 h-4 w-4 shrink-0 text-[#e8a33c]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                aria-hidden="true"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {{ $t(bulletKey) }}
            </li>
          </ul>
          <p v-else class="font-label mt-8 text-xs tracking-[0.14em] text-[#fcfaf5]/45 uppercase">
            {{ $t('auth.panel.loginChip') }}
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { AuthShellMode } from '~/types/AuthShell'

/** A decorative KPI tile shown in the app window mockup. */
interface AuthShellKpi {
  /** i18n key of the KPI label. */
  labelKey: string
  /** Decorative display value (mockup only, not localized). */
  value: string
}

/**
 * Split-screen shell for the auth pages (login / signup).
 * Left: paper column hosting the form (slot). Right (desktop only): ink brand
 * panel in the landing DA — eyebrow, pitch, app-window mockup — so wide
 * viewports never feel empty. Mode drives the panel copy: signup sells,
 * login welcomes back.
 */
defineProps({
  mode: {
    type: String as PropType<AuthShellMode>,
    required: true,
  },
})

const localePath = useLocalePath()

/** i18n keys of the signup pitch bullets under the mockup. */
const bulletKeys: string[] = ['auth.panel.bullet1', 'auth.panel.bullet2', 'auth.panel.bullet3']

/** Decorative KPI tiles mirroring the real dashboard (same values as the landing mockup). */
const kpis: AuthShellKpi[] = [
  { labelKey: 'landing.desktop.window.kpiProspects', value: '128' },
  { labelKey: 'landing.desktop.window.kpiDemos', value: '42' },
  { labelKey: 'landing.desktop.window.kpiSales', value: '9' },
]

/** Number of skeleton rows in the mocked prospect list. */
const listRows: number[] = [1, 2, 3]
</script>
