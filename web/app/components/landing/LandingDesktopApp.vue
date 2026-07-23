<template>
  <section id="desktop-app" class="px-5 py-24 md:px-8 md:py-36">
    <div class="mx-auto max-w-6xl">
      <div class="grid items-center gap-14 lg:grid-cols-[1fr_1.15fr] lg:gap-20">
        <div>
          <p v-reveal class="landing-eyebrow">{{ $t('landing.desktop.eyebrow') }}</p>
          <h2
            v-reveal="{ delay: 80 }"
            class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
          >
            {{ $t('landing.desktop.title') }}
          </h2>
          <p v-reveal="{ delay: 160 }" class="mt-5 max-w-lg text-lg leading-relaxed text-[#6b6355]">
            {{ $t('landing.desktop.description') }}
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
          <div v-reveal="{ delay: 440 }" class="mt-9 flex flex-col items-start gap-3">
            <NuxtLink
              :to="localePath('/downloads')"
              class="landing-btn-primary whitespace-nowrap"
              @click="track('site_download_click', { location: 'section' })"
            >
              {{ $t('landing.desktop.cta') }}
              <i class="fa-solid fa-arrow-down text-sm" aria-hidden="true"></i>
            </NuxtLink>
            <p class="font-label text-xs tracking-wide text-[#6b6355]">
              {{ $t('landing.desktop.note') }}
            </p>
          </div>
        </div>

        <div v-reveal="{ delay: 150 }" class="relative">
          <div
            class="landing-tilt overflow-hidden rounded-2xl border border-[#3a342b] bg-[#1b1813] shadow-[0_32px_64px_-32px_rgba(27,24,19,0.45)]"
          >
            <div class="flex items-center gap-2 border-b border-[#3a342b] px-4 py-3.5">
              <span class="h-3 w-3 rounded-full bg-[#e8a33c]/80" aria-hidden="true"></span>
              <span class="h-3 w-3 rounded-full bg-[#4a4438]" aria-hidden="true"></span>
              <span class="h-3 w-3 rounded-full bg-[#4a4438]" aria-hidden="true"></span>
              <span class="font-label ml-3 flex-1 truncate text-center text-xs text-[#f6f3ec]/50">
                devleadhunter — {{ $t('landing.desktop.window.title') }}
              </span>
            </div>

            <div class="flex">
              <div class="hidden w-16 flex-col gap-4 border-r border-[#3a342b] p-4 sm:flex" aria-hidden="true">
                <span class="h-7 w-7 rounded-lg bg-[#e8a33c]/25"></span>
                <span class="mt-1 h-2.5 w-full rounded-full bg-[#3a342b]"></span>
                <span class="h-2.5 w-full rounded-full bg-[#3a342b]"></span>
                <span class="h-2.5 w-3/4 rounded-full bg-[#3a342b]"></span>
                <span class="h-2.5 w-full rounded-full bg-[#3a342b]"></span>
              </div>

              <div class="flex-1 p-6">
                <div class="grid grid-cols-3 gap-3">
                  <div
                    v-for="kpi in kpis"
                    :key="kpi.labelKey"
                    class="rounded-xl border border-[#3a342b] bg-[#262119] p-4"
                  >
                    <p class="font-label text-[0.6rem] tracking-[0.14em] text-[#e8a33c]/80 uppercase">
                      {{ $t(kpi.labelKey) }}
                    </p>
                    <p class="font-display mt-2 text-xl font-semibold text-[#fcfaf5]" aria-hidden="true">
                      {{ kpi.value }}
                    </p>
                  </div>
                </div>

                <div class="mt-4 space-y-2.5" aria-hidden="true">
                  <div
                    v-for="rowIndex in MOCK_PROSPECT_ROW_COUNT"
                    :key="rowIndex"
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
          </div>

          <p
            class="font-label absolute right-6 -bottom-5 inline-flex rotate-[2deg] items-center gap-2 rounded-full border border-[#e3dccd] bg-[#fcfaf5] px-4 py-2 text-xs text-[#1b1813] shadow-lg md:right-10"
          >
            <i class="fa-solid fa-desktop text-[0.65rem] text-[#e8a33c]" aria-hidden="true"></i>
            {{ $t('landing.desktop.chip') }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { LandingDesktopKpi } from '~/types/LandingDesktopApp'

const localePath = useLocalePath()
const { track } = useSiteTracking()

/** i18n keys of the three benefit bullets under the heading. */
const bulletKeys: string[] = ['landing.desktop.bullet1', 'landing.desktop.bullet2', 'landing.desktop.bullet3']

/** Decorative KPI tiles mirroring the real dashboard (prospects, demos, sales). */
const kpis: LandingDesktopKpi[] = [
  { labelKey: 'landing.desktop.window.kpiProspects', value: '128' },
  { labelKey: 'landing.desktop.window.kpiDemos', value: '42' },
  { labelKey: 'landing.desktop.window.kpiSales', value: '9' },
]

const MOCK_PROSPECT_ROW_COUNT: number = 3
</script>
