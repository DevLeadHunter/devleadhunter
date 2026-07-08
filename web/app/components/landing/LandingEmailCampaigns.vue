<template>
  <section id="email-campaigns" class="px-5 py-24 md:px-8 md:py-36">
    <div class="mx-auto max-w-6xl">
      <div class="grid items-center gap-14 lg:grid-cols-[1.15fr_1fr] lg:gap-20">
        <!-- Campaign A/B card -->
        <div v-reveal="{ delay: 150 }" class="order-2 lg:order-1">
          <div class="landing-card landing-tilt mx-auto max-w-md p-6 md:p-7 lg:mx-0">
            <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
              {{ $t('landing.campaigns.card.label') }}
            </p>

            <!-- Variant A — leading -->
            <div class="mt-5 rounded-xl border border-[#e3dccd] bg-[#f6f3ec] p-4">
              <div class="flex items-center justify-between gap-3">
                <p class="font-label text-[0.65rem] font-medium tracking-[0.14em] text-[#6b6355] uppercase">
                  {{ $t('landing.campaigns.card.variantALabel') }}
                </p>
                <span
                  class="inline-flex items-center gap-1.5 rounded-full bg-[#2f7d4e] px-2.5 py-0.5 text-[0.65rem] font-semibold text-[#fcfaf5]"
                >
                  <i class="fa-solid fa-trophy text-[0.55rem]" aria-hidden="true"></i>
                  {{ $t('landing.campaigns.card.leaderBadge') }}
                </span>
              </div>
              <p class="mt-2 text-sm font-semibold text-[#1b1813]">
                {{ $t('landing.campaigns.card.variantASubject') }}
              </p>
              <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-[#e3dccd]" aria-hidden="true">
                <div class="h-full w-[62%] rounded-full bg-[#e8a33c]"></div>
              </div>
              <p class="font-label mt-2 text-[0.7rem] text-[#6b6355]">
                {{ $t('landing.campaigns.card.variantAStats') }}
              </p>
            </div>

            <!-- Variant B -->
            <div class="mt-3 rounded-xl border border-[#e3dccd] bg-[#fcfaf5] p-4">
              <p class="font-label text-[0.65rem] font-medium tracking-[0.14em] text-[#6b6355] uppercase">
                {{ $t('landing.campaigns.card.variantBLabel') }}
              </p>
              <p class="mt-2 text-sm font-semibold text-[#1b1813]">
                {{ $t('landing.campaigns.card.variantBSubject') }}
              </p>
              <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-[#e3dccd]" aria-hidden="true">
                <div class="h-full w-[34%] rounded-full bg-[#e8a33c]/60"></div>
              </div>
              <p class="font-label mt-2 text-[0.7rem] text-[#6b6355]">
                {{ $t('landing.campaigns.card.variantBStats') }}
              </p>
            </div>

            <p
              class="font-label mt-5 border-t border-dashed border-[#e3dccd] pt-4 text-[0.65rem] tracking-[0.14em] text-[#6b6355] uppercase"
            >
              {{ $t('landing.campaigns.card.meta') }}
            </p>
          </div>
        </div>

        <!-- Copy -->
        <div class="order-1 lg:order-2">
          <p v-reveal class="landing-eyebrow">{{ $t('landing.campaigns.eyebrow') }}</p>
          <h2
            v-reveal="{ delay: 80 }"
            class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
          >
            {{ $t('landing.campaigns.title') }}
          </h2>
          <p v-reveal="{ delay: 160 }" class="mt-5 max-w-lg text-lg leading-relaxed text-[#6b6355]">
            {{ $t('landing.campaigns.description') }}
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
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/** i18n keys of the four campaign bullets. */
const bulletKeys: string[] = [
  'landing.campaigns.bullet1',
  'landing.campaigns.bullet2',
  'landing.campaigns.bullet3',
  'landing.campaigns.bullet4',
]
</script>
