<template>
  <section id="features" class="scroll-mt-20 bg-[#050505] py-24 md:py-32">
    <div class="container mx-auto px-4 md:px-6 lg:px-8">
      <!-- Section heading -->
      <div class="mx-auto mb-20 max-w-2xl text-center">
        <h2 v-reveal class="mb-5 text-3xl font-bold tracking-tight text-[#f9f9f9] md:text-4xl lg:text-5xl">
          {{ $t('features.title') }}
        </h2>
        <p v-reveal class="text-base leading-relaxed text-[#8b949e] md:text-lg">{{ $t('features.subtitle') }}</p>
      </div>

      <div class="mx-auto max-w-6xl space-y-24 md:space-y-32">
        <!-- 1. Automatic site generation -->
        <LandingFeatureRow
          icon="fa-wand-magic-sparkles"
          accent="emerald"
          :badge="$t('features.demoSite.badge')"
          :heading="$t('features.demoSite.heading')"
          :description="$t('features.demoSite.description')"
          :features="[
            $t('features.demoSite.feature1'),
            $t('features.demoSite.feature2'),
            $t('features.demoSite.feature3'),
            $t('features.demoSite.feature4'),
          ]"
        >
          <div class="relative">
            <div class="overflow-hidden rounded-2xl border border-[#30363d] bg-[#0d1117] shadow-2xl">
              <!-- Browser chrome -->
              <div class="flex items-center gap-2 border-b border-[#30363d] bg-[#161b22] px-3 py-2.5">
                <div class="flex gap-1.5">
                  <span class="h-2.5 w-2.5 rounded-full bg-[#ff5f57]"></span>
                  <span class="h-2.5 w-2.5 rounded-full bg-[#febc2e]"></span>
                  <span class="h-2.5 w-2.5 rounded-full bg-[#28c840]"></span>
                </div>
                <div
                  class="ml-2 flex flex-1 items-center gap-2 truncate rounded-md bg-[#0d1117] px-3 py-1 text-xs text-[#8b949e]"
                >
                  <i class="fa-solid fa-lock text-[10px] text-[#3fb950]"></i>
                  <span class="truncate">{{ $t('features.demoSite.mockupUrl') }}</span>
                </div>
              </div>
              <!-- Rendered site -->
              <div>
                <div class="bg-gradient-to-br from-[#0b2a4a] to-[#0e4377] px-6 py-7">
                  <div class="mb-5 flex items-center justify-between">
                    <span class="flex items-center gap-1.5 text-sm font-bold text-white">
                      <i class="fa-solid fa-droplet text-[#5fb3ff]"></i>{{ $t('features.demoSite.mockupTitle') }}
                    </span>
                    <span class="hidden gap-3 text-[10px] font-medium text-white/60 sm:flex">
                      <span>Services</span><span>Avis</span><span>Contact</span>
                    </span>
                  </div>
                  <h4 class="mb-1.5 text-xl font-bold text-white">{{ $t('features.demoSite.mockupTitle') }}</h4>
                  <p class="mb-5 text-xs text-white/75">{{ $t('features.demoSite.mockupTag') }}</p>
                  <span class="inline-flex rounded-lg bg-[#3fb950] px-3.5 py-2 text-xs font-semibold text-[#04130a]">
                    {{ $t('features.demoSite.mockupCta') }}
                  </span>
                </div>
                <div class="grid grid-cols-3 gap-2 bg-white p-3">
                  <div v-for="n in 3" :key="n" class="rounded-lg bg-slate-100 p-2.5">
                    <div class="mb-2 h-5 w-5 rounded-md bg-[#0e4377]/15"></div>
                    <div class="mb-1 h-1.5 w-full rounded bg-slate-300"></div>
                    <div class="h-1.5 w-2/3 rounded bg-slate-200"></div>
                  </div>
                </div>
              </div>
            </div>
            <!-- Floating CMS pill -->
            <div
              class="absolute -right-3 -bottom-3 flex items-center gap-2 rounded-xl border border-[#2BAD5F]/30 bg-[#0d1117] px-3 py-2 shadow-xl"
            >
              <i class="fa-solid fa-pen-to-square text-sm text-[#3fb950]"></i>
              <span class="text-xs font-medium text-[#c9d1d9]">{{ $t('features.demoSite.mockupEdit') }}</span>
            </div>
          </div>
        </LandingFeatureRow>

        <!-- 2. Prospecting & enrichment -->
        <LandingFeatureRow
          icon="fa-magnifying-glass"
          accent="blue"
          reversed
          :badge="$t('features.prospecting.badge')"
          :heading="$t('features.prospecting.heading')"
          :description="$t('features.prospecting.description')"
          :features="[
            $t('features.prospecting.feature1'),
            $t('features.prospecting.feature2'),
            $t('features.prospecting.feature3'),
            $t('features.prospecting.feature4'),
          ]"
        >
          <div class="space-y-3 rounded-2xl border border-[#30363d] bg-[#0d1117] p-4 shadow-2xl md:p-5">
            <div
              v-for="card in prospectCards"
              :key="card.name"
              class="flex items-center gap-3 rounded-xl border border-[#30363d] bg-[#161b22] p-3"
            >
              <span class="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg bg-[#58a6ff]/10">
                <i class="fa-solid fa-store text-[#58a6ff]"></i>
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold text-[#f9f9f9]">{{ card.name }}</p>
                <p class="truncate text-xs text-[#8b949e]">{{ card.meta }}</p>
              </div>
              <span
                class="hidden flex-shrink-0 rounded-md bg-[#f0883e]/10 px-2 py-1 text-[10px] font-semibold text-[#f0883e] sm:inline-block"
              >
                {{ $t('features.prospecting.mockupTag') }}
              </span>
            </div>
            <div class="flex items-center justify-center gap-3 pt-1 text-[10px] font-medium text-[#6e7681]">
              <span class="inline-flex items-center gap-1"><i class="fa-brands fa-google"></i>Google</span>
              <span class="inline-flex items-center gap-1"><i class="fa-solid fa-book"></i>Pages Jaunes</span>
              <span class="inline-flex items-center gap-1"><i class="fa-solid fa-map-location-dot"></i>OSM</span>
            </div>
          </div>
        </LandingFeatureRow>

        <!-- 3. Cold email engine -->
        <LandingFeatureRow
          icon="fa-paper-plane"
          accent="emerald"
          :badge="$t('features.coldEmail.badge')"
          :heading="$t('features.coldEmail.heading')"
          :description="$t('features.coldEmail.description')"
          :features="[
            $t('features.coldEmail.feature1'),
            $t('features.coldEmail.feature2'),
            $t('features.coldEmail.feature3'),
            $t('features.coldEmail.feature4'),
          ]"
        >
          <div class="rounded-2xl border border-[#30363d] bg-[#0d1117] p-4 shadow-2xl md:p-5">
            <div class="mb-3 grid grid-cols-2 gap-3">
              <div class="rounded-xl border border-[#2BAD5F]/30 bg-[#161b22] p-3">
                <div class="mb-2 flex items-center justify-between">
                  <span class="rounded-md bg-[#2BAD5F]/15 px-2 py-0.5 text-[10px] font-bold text-[#3fb950]">
                    {{ $t('features.coldEmail.variantA') }}
                  </span>
                  <span class="text-[10px] font-semibold text-[#3fb950]">68%</span>
                </div>
                <p class="line-clamp-2 text-[11px] leading-snug text-[#8b949e]">
                  {{ $t('features.coldEmail.variantApreview') }}
                </p>
                <div class="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-[#21262d]">
                  <div class="h-full w-[68%] rounded-full bg-[#3fb950]"></div>
                </div>
              </div>
              <div class="rounded-xl border border-[#30363d] bg-[#161b22] p-3">
                <div class="mb-2 flex items-center justify-between">
                  <span class="rounded-md bg-[#30363d] px-2 py-0.5 text-[10px] font-bold text-[#8b949e]">
                    {{ $t('features.coldEmail.variantB') }}
                  </span>
                  <span class="text-[10px] font-semibold text-[#8b949e]">41%</span>
                </div>
                <p class="line-clamp-2 text-[11px] leading-snug text-[#8b949e]">
                  {{ $t('features.coldEmail.variantBpreview') }}
                </p>
                <div class="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-[#21262d]">
                  <div class="h-full w-[41%] rounded-full bg-[#6e7681]"></div>
                </div>
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span
                class="inline-flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#161b22] px-2.5 py-1.5 text-[11px] font-medium text-[#c9d1d9]"
              >
                <i class="fa-solid fa-gauge-high text-[#58a6ff]"></i>{{ $t('features.coldEmail.queueLabel') }}
                <span class="font-mono text-[#3fb950]">{{ $t('features.coldEmail.queueValue') }}</span>
              </span>
              <span
                class="inline-flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#161b22] px-2.5 py-1.5 text-[11px] font-medium text-[#c9d1d9]"
              >
                <i class="fa-solid fa-clock-rotate-left text-[#e3b341]"></i>{{ $t('features.coldEmail.followUp') }}
              </span>
            </div>
          </div>
        </LandingFeatureRow>

        <!-- 4. AI lead scoring & behavior -->
        <LandingFeatureRow
          icon="fa-fire"
          accent="blue"
          reversed
          :badge="$t('features.leadScoring.badge')"
          :heading="$t('features.leadScoring.heading')"
          :description="$t('features.leadScoring.description')"
          :features="[
            $t('features.leadScoring.feature1'),
            $t('features.leadScoring.feature2'),
            $t('features.leadScoring.feature3'),
            $t('features.leadScoring.feature4'),
          ]"
        >
          <div class="rounded-2xl border border-[#30363d] bg-[#0d1117] p-4 shadow-2xl md:p-5">
            <div class="mb-3 grid grid-cols-3 gap-2">
              <div class="rounded-xl border border-[#ff7b72]/40 bg-[#ff7b72]/10 px-2 py-2.5 text-center">
                <i class="fa-solid fa-fire mb-1 text-[#ff7b72]"></i>
                <p class="text-[11px] font-bold text-[#ff7b72]">{{ $t('features.leadScoring.hot') }}</p>
              </div>
              <div class="rounded-xl border border-[#30363d] bg-[#161b22] px-2 py-2.5 text-center opacity-60">
                <i class="fa-solid fa-temperature-half mb-1 text-[#e3b341]"></i>
                <p class="text-[11px] font-bold text-[#8b949e]">{{ $t('features.leadScoring.warm') }}</p>
              </div>
              <div class="rounded-xl border border-[#30363d] bg-[#161b22] px-2 py-2.5 text-center opacity-60">
                <i class="fa-solid fa-snowflake mb-1 text-[#58a6ff]"></i>
                <p class="text-[11px] font-bold text-[#8b949e]">{{ $t('features.leadScoring.cold') }}</p>
              </div>
            </div>
            <div class="mb-3 space-y-2">
              <div
                v-for="(event, i) in behaviorEvents"
                :key="i"
                class="flex items-center gap-2.5 rounded-lg bg-[#161b22] px-3 py-2"
              >
                <i :class="['fa-solid', event.icon, 'text-xs text-[#58a6ff]']"></i>
                <span class="text-[11px] text-[#c9d1d9]">{{ event.label }}</span>
              </div>
            </div>
            <div class="rounded-xl border border-[#bc8cff]/30 bg-[#bc8cff]/10 p-3">
              <div class="mb-1.5 flex items-center gap-1.5">
                <i class="fa-solid fa-wand-magic-sparkles text-xs text-[#bc8cff]"></i>
                <span class="text-[10px] font-bold tracking-wide text-[#bc8cff] uppercase">
                  {{ $t('features.leadScoring.aiLabel') }}
                </span>
              </div>
              <p class="text-[11px] leading-snug text-[#c9d1d9]">{{ $t('features.leadScoring.aiSummary') }}</p>
            </div>
          </div>
        </LandingFeatureRow>

        <!-- 5. Sales funnel & deploy -->
        <LandingFeatureRow
          icon="fa-rocket"
          accent="emerald"
          :badge="$t('features.sales.badge')"
          :heading="$t('features.sales.heading')"
          :description="$t('features.sales.description')"
          :features="[
            $t('features.sales.feature1'),
            $t('features.sales.feature2'),
            $t('features.sales.feature3'),
            $t('features.sales.feature4'),
          ]"
        >
          <div class="rounded-2xl border border-[#30363d] bg-[#0d1117] p-5 shadow-2xl">
            <div class="mb-4 flex items-center justify-between border-b border-[#30363d] pb-4">
              <div>
                <p class="text-xs text-[#8b949e]">{{ $t('features.sales.orderLabel') }}</p>
                <p class="text-base font-bold text-[#f9f9f9]">{{ $t('features.demoSite.mockupTitle') }}</p>
              </div>
              <span
                class="inline-flex items-center gap-1.5 rounded-lg bg-[#2BAD5F]/15 px-3 py-1.5 text-xs font-semibold text-[#3fb950]"
              >
                <i class="fa-solid fa-circle-check"></i>{{ $t('features.sales.orderPaid') }}
              </span>
            </div>
            <ol class="relative space-y-4 pl-6">
              <span class="absolute top-2 bottom-2 left-[7px] w-px bg-[#30363d]"></span>
              <li class="relative flex items-center gap-3">
                <span class="absolute -left-6 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#3fb950]">
                  <i class="fa-solid fa-check text-[7px] text-[#04130a]"></i>
                </span>
                <i class="fa-brands fa-stripe-s text-[#635bff]"></i>
                <span class="text-xs font-medium text-[#c9d1d9]">{{ $t('features.sales.orderPaid') }}</span>
              </li>
              <li class="relative flex items-center gap-3">
                <span
                  class="absolute -left-6 h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#30363d] border-t-[#3fb950]"
                ></span>
                <i class="fa-solid fa-cloud-arrow-up text-[#58a6ff]"></i>
                <span class="text-xs font-medium text-[#c9d1d9]">{{ $t('features.sales.deploying') }}</span>
              </li>
              <li class="relative flex items-center gap-3 opacity-50">
                <span class="absolute -left-6 h-3.5 w-3.5 rounded-full border-2 border-[#30363d] bg-[#0d1117]"></span>
                <i class="fa-solid fa-globe text-[#8b949e]"></i>
                <span class="text-xs font-medium text-[#8b949e]">{{ $t('features.sales.deployed') }}</span>
              </li>
            </ol>
          </div>
        </LandingFeatureRow>
      </div>

      <!-- Secondary highlights grid -->
      <div class="mx-auto mt-28 max-w-6xl">
        <h3 v-reveal class="mb-12 text-center text-2xl font-bold tracking-tight text-[#f9f9f9] md:text-3xl">
          {{ $t('features.highlights.title') }}
        </h3>
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <div
            v-for="(item, index) in highlights"
            :key="item.key"
            v-reveal="{ delay: (index % 3) * 80 }"
            class="group rounded-2xl border border-[#30363d] bg-[#0d1117] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#30363d]/80 hover:bg-[#161b22]"
          >
            <span
              class="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[#21262d] text-[#8b949e] transition-colors group-hover:bg-[#2BAD5F]/10 group-hover:text-[#3fb950]"
            >
              <i :class="['fa-solid', item.icon, 'text-base']"></i>
            </span>
            <h4 class="mb-2 text-base font-semibold text-[#f9f9f9]">{{ item.title }}</h4>
            <p class="text-sm leading-relaxed text-[#8b949e]">{{ item.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'

/** A prospect card shown in the prospecting mockup. */
interface ProspectCard {
  name: string
  meta: string
}

/** A behavior event shown in the lead-scoring mockup. */
interface BehaviorEvent {
  icon: string
  label: string
}

/** A secondary highlight card. */
interface HighlightItem {
  key: string
  icon: string
  title: string
  description: string
}

const { t } = useI18n()

/**
 * Enriched prospect cards for the prospecting mockup.
 */
const prospectCards: ComputedRef<ProspectCard[]> = computed((): ProspectCard[] => [
  { name: t('features.prospecting.card1Name'), meta: t('features.prospecting.card1Meta') },
  { name: t('features.prospecting.card2Name'), meta: t('features.prospecting.card2Meta') },
  { name: t('features.prospecting.card3Name'), meta: t('features.prospecting.card3Meta') },
])

/**
 * Behavior timeline events for the lead-scoring mockup.
 */
const behaviorEvents: ComputedRef<BehaviorEvent[]> = computed((): BehaviorEvent[] => [
  { icon: 'fa-eye', label: t('features.leadScoring.timeline1') },
  { icon: 'fa-envelope-open', label: t('features.leadScoring.timeline2') },
  { icon: 'fa-hand-pointer', label: t('features.leadScoring.timeline3') },
])

/**
 * Secondary feature highlights grid.
 */
const highlights: ComputedRef<HighlightItem[]> = computed((): HighlightItem[] => [
  {
    key: 'analytics',
    icon: 'fa-chart-line',
    title: t('features.highlights.analytics.title'),
    description: t('features.highlights.analytics.description'),
  },
  {
    key: 'credits',
    icon: 'fa-coins',
    title: t('features.highlights.credits.title'),
    description: t('features.highlights.credits.description'),
  },
  {
    key: 'emailAccounts',
    icon: 'fa-envelopes-bulk',
    title: t('features.highlights.emailAccounts.title'),
    description: t('features.highlights.emailAccounts.description'),
  },
  {
    key: 'security',
    icon: 'fa-shield-halved',
    title: t('features.highlights.security.title'),
    description: t('features.highlights.security.description'),
  },
  {
    key: 'i18n',
    icon: 'fa-language',
    title: t('features.highlights.i18n.title'),
    description: t('features.highlights.i18n.description'),
  },
  {
    key: 'autoUpdate',
    icon: 'fa-arrows-rotate',
    title: t('features.highlights.autoUpdate.title'),
    description: t('features.highlights.autoUpdate.description'),
  },
])
</script>
