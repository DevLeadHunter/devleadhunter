<template>
  <section id="delivered-site" class="px-5 py-24 md:px-8 md:py-36">
    <div class="mx-auto max-w-6xl">
      <div class="grid items-center gap-14 lg:grid-cols-[1fr_1.15fr] lg:gap-20">
        <!-- Copy -->
        <div>
          <p v-reveal class="landing-eyebrow">{{ $t('landing.proof.eyebrow') }}</p>
          <h2
            v-reveal="{ delay: 80 }"
            class="font-display mt-6 text-4xl leading-[1.06] font-semibold tracking-[-0.015em] text-[#1b1813] md:text-5xl"
          >
            {{ $t('landing.proof.title') }}
          </h2>
          <p v-reveal="{ delay: 160 }" class="mt-5 max-w-lg text-lg leading-relaxed text-[#6b6355]">
            {{ $t('landing.proof.description') }}
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

        <!-- Demo site mockup -->
        <div v-reveal="{ delay: 150 }" class="relative">
          <div class="landing-card landing-tilt overflow-hidden">
            <!-- Browser chrome -->
            <div class="flex items-center gap-2 border-b border-[#e3dccd] px-5 py-3.5">
              <span class="h-2.5 w-2.5 rounded-full bg-[#e3dccd]" aria-hidden="true"></span>
              <span class="h-2.5 w-2.5 rounded-full bg-[#e3dccd]" aria-hidden="true"></span>
              <span class="h-2.5 w-2.5 rounded-full bg-[#e3dccd]" aria-hidden="true"></span>
              <span
                class="font-label ml-3 flex-1 truncate rounded-full bg-[#f6f3ec] px-3.5 py-1 text-center text-xs text-[#1b1813]"
              >
                {{ $t('landing.story.visual.siteUrl') }}
              </span>
            </div>
            <!-- Fake generated site -->
            <div class="p-7 md:p-9">
              <div class="flex items-center justify-between">
                <p class="font-display text-lg font-semibold text-[#1b1813]">
                  {{ $t('landing.story.visual.siteTitle') }}
                </p>
                <div class="flex gap-3" aria-hidden="true">
                  <span class="h-1.5 w-10 rounded-full bg-[#e3dccd]"></span>
                  <span class="h-1.5 w-10 rounded-full bg-[#e3dccd]"></span>
                  <span class="h-1.5 w-10 rounded-full bg-[#e3dccd]"></span>
                </div>
              </div>
              <div class="mt-8">
                <p class="font-display text-3xl leading-tight font-semibold text-[#1b1813] md:text-4xl">
                  {{ $t('landing.story.visual.siteTagline') }}
                </p>
                <span class="mt-5 inline-flex rounded-full bg-[#1b1813] px-5 py-2 text-sm font-semibold text-[#fcfaf5]">
                  {{ $t('landing.story.visual.siteCta') }}
                </span>
              </div>
              <div class="mt-9 grid grid-cols-3 gap-3" aria-hidden="true">
                <div class="space-y-2 rounded-xl border border-[#e3dccd] bg-[#f6f3ec] p-4">
                  <span class="block h-8 w-8 rounded-full bg-[#ece5d8]"></span>
                  <span class="block h-2 w-3/4 rounded-full bg-[#e3dccd]"></span>
                  <span class="block h-2 w-1/2 rounded-full bg-[#e3dccd]"></span>
                </div>
                <div class="space-y-2 rounded-xl border border-[#e3dccd] bg-[#f6f3ec] p-4">
                  <span class="block h-8 w-8 rounded-full bg-[#ece5d8]"></span>
                  <span class="block h-2 w-3/4 rounded-full bg-[#e3dccd]"></span>
                  <span class="block h-2 w-2/3 rounded-full bg-[#e3dccd]"></span>
                </div>
                <div class="space-y-2 rounded-xl border border-[#e3dccd] bg-[#f6f3ec] p-4">
                  <span class="block h-8 w-8 rounded-full bg-[#ece5d8]"></span>
                  <span class="block h-2 w-2/3 rounded-full bg-[#e3dccd]"></span>
                  <span class="block h-2 w-1/2 rounded-full bg-[#e3dccd]"></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Floating CMS chip -->
          <p
            class="font-label absolute -bottom-5 left-6 inline-flex rotate-[-2deg] items-center gap-2 rounded-full border border-[#e3dccd] bg-[#fcfaf5] px-4 py-2 text-xs text-[#1b1813] shadow-lg md:left-10"
          >
            <i class="fa-solid fa-pen text-[0.65rem] text-[#e8a33c]" aria-hidden="true"></i>
            {{ $t('landing.story.visual.siteChip') }} — Storyblok
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/** i18n keys of the three proof bullets. */
const bulletKeys: string[] = ['landing.proof.bullet1', 'landing.proof.bullet2', 'landing.proof.bullet3']
</script>
