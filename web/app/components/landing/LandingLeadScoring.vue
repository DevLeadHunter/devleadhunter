<template>
  <section id="lead-scoring" class="px-5 py-24 md:px-8 md:py-36">
    <div class="mx-auto max-w-6xl">
      <div class="grid items-center gap-14 lg:grid-cols-[1.15fr_1fr] lg:gap-20">
        <div v-reveal="{ delay: 150 }" class="order-2 lg:order-1">
          <div class="landing-card landing-tilt mx-auto max-w-md p-6 md:p-7 lg:mx-0">
            <div class="flex items-start justify-between gap-4">
              <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
                {{ $t('landing.behavior.card.label') }}
              </p>
              <span
                class="inline-flex items-center gap-1.5 rounded-full bg-[#e8a33c] px-3 py-1 text-xs font-semibold text-[#1b1813]"
              >
                <i class="fa-solid fa-fire text-[0.65rem]" aria-hidden="true"></i>
                {{ $t('landing.behavior.card.badge') }}
              </span>
            </div>
            <p class="font-display mt-3 text-2xl font-semibold text-[#1b1813]">
              {{ $t('landing.behavior.card.name') }}
            </p>

            <ol class="relative mt-6 space-y-4 border-t border-dashed border-[#e3dccd] pt-5">
              <li
                v-for="eventKey in behaviorEventKeys"
                :key="eventKey"
                class="flex items-start gap-3 text-sm text-[#1b1813]"
              >
                <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#e8a33c]" aria-hidden="true"></span>
                {{ $t(eventKey) }}
              </li>
            </ol>

            <div class="mt-6 rounded-xl border border-[#e3dccd] bg-[#f6f3ec] p-4">
              <p class="font-label text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase">
                <i class="fa-solid fa-wand-magic-sparkles mr-1 text-[0.6rem] text-[#e8a33c]" aria-hidden="true"></i>
                {{ $t('landing.behavior.card.aiLabel') }}
              </p>
              <p class="font-display mt-2 text-base leading-snug text-[#1b1813] italic">
                {{ $t('landing.behavior.card.aiSummary') }}
              </p>
            </div>
          </div>
        </div>

        <div class="order-1 lg:order-2">
          <p v-reveal class="landing-eyebrow">{{ $t('landing.behavior.eyebrow') }}</p>
          <h2
            v-reveal="{ delay: 80 }"
            class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
          >
            {{ $t('landing.behavior.title') }}
          </h2>
          <p v-reveal="{ delay: 160 }" class="mt-5 max-w-lg text-lg leading-relaxed text-[#6b6355]">
            {{ $t('landing.behavior.description') }}
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
/** i18n keys of the three prospect-behavior events shown in the timeline. */
const behaviorEventKeys: string[] = [
  'landing.behavior.card.event1',
  'landing.behavior.card.event2',
  'landing.behavior.card.event3',
]

/** i18n keys of the three scoring bullets. */
const bulletKeys: string[] = ['landing.behavior.bullet1', 'landing.behavior.bullet2', 'landing.behavior.bullet3']
</script>
