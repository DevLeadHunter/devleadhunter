<template>
  <section id="platforms" class="relative scroll-mt-20 overflow-hidden bg-[#0d1117] py-24 md:py-32">
    <div class="landing-glow top-0 right-1/4 h-[280px] w-[480px] bg-[#58a6ff]/8"></div>

    <div class="relative z-10 container mx-auto px-4 md:px-6 lg:px-8">
      <div class="mx-auto mb-16 max-w-2xl text-center">
        <div
          v-reveal
          class="mb-5 inline-flex items-center gap-2 rounded-full border border-[#58a6ff]/30 bg-[#58a6ff]/10 px-4 py-1.5"
        >
          <i class="fa-solid fa-layer-group text-xs text-[#58a6ff]"></i>
          <span class="text-xs font-semibold tracking-wide text-[#58a6ff] uppercase">{{ $t('platforms.badge') }}</span>
        </div>
        <h2 v-reveal class="mb-5 text-3xl font-bold tracking-tight text-[#f9f9f9] md:text-4xl lg:text-5xl">
          {{ $t('platforms.title') }}
        </h2>
        <p v-reveal class="text-base leading-relaxed text-[#8b949e] md:text-lg">{{ $t('platforms.subtitle') }}</p>
      </div>

      <div class="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">
        <!-- Web -->
        <div
          v-reveal
          class="flex flex-col rounded-2xl border border-[#30363d] bg-[#161b22] p-7 transition-all duration-300 hover:-translate-y-1 hover:border-[#58a6ff]/40"
        >
          <span class="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-[#58a6ff]/10 text-[#58a6ff]">
            <i class="fa-solid fa-globe text-xl"></i>
          </span>
          <h3 class="mb-2 text-lg font-semibold text-[#f9f9f9]">{{ $t('platforms.web.title') }}</h3>
          <p class="mb-6 flex-1 text-sm leading-relaxed text-[#8b949e]">{{ $t('platforms.web.description') }}</p>
          <NuxtLink
            :to="localePath('/signup')"
            class="inline-flex items-center gap-2 text-sm font-semibold text-[#58a6ff] transition-colors hover:text-[#79b8ff]"
          >
            {{ $t('platforms.web.cta') }}<i class="fa-solid fa-arrow-right text-xs"></i>
          </NuxtLink>
        </div>

        <!-- Desktop (highlighted) -->
        <div
          v-reveal="{ delay: 80 }"
          class="relative flex flex-col rounded-2xl border border-[#2BAD5F]/40 bg-[#161b22] p-7 shadow-[0_0_40px_-12px_rgba(43,173,95,0.4)] transition-all duration-300 hover:-translate-y-1"
        >
          <span class="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-[#2BAD5F]/15 text-[#3fb950]">
            <i class="fa-solid fa-display text-xl"></i>
          </span>
          <div class="mb-2 flex items-center gap-2">
            <h3 class="text-lg font-semibold text-[#f9f9f9]">{{ $t('platforms.desktop.title') }}</h3>
          </div>
          <div class="mb-3 flex items-center gap-2">
            <span
              class="inline-flex items-center gap-1.5 rounded-md bg-[#21262d] px-2 py-1 text-[11px] font-medium text-[#c9d1d9]"
            >
              <i class="fa-brands fa-windows text-[#58a6ff]"></i>Windows
            </span>
            <span
              class="inline-flex items-center gap-1.5 rounded-md bg-[#21262d] px-2 py-1 text-[11px] font-medium text-[#c9d1d9]"
            >
              <i class="fa-brands fa-apple"></i>macOS
            </span>
          </div>
          <p class="mb-6 flex-1 text-sm leading-relaxed text-[#8b949e]">{{ $t('platforms.desktop.description') }}</p>
          <NuxtLink :to="localePath('/downloads')" class="btn-emerald py-2.5 text-sm">
            <i class="fa-solid fa-download text-xs"></i>{{ $t('platforms.desktop.cta') }}
          </NuxtLink>
        </div>

        <!-- Mobile -->
        <div
          v-reveal="{ delay: 160 }"
          class="flex flex-col rounded-2xl border border-[#30363d] bg-[#161b22] p-7 transition-all duration-300 hover:-translate-y-1 hover:border-[#58a6ff]/40"
        >
          <span class="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-[#bc8cff]/10 text-[#bc8cff]">
            <i class="fa-solid fa-mobile-screen-button text-xl"></i>
          </span>
          <h3 class="mb-2 text-lg font-semibold text-[#f9f9f9]">{{ $t('platforms.mobile.title') }}</h3>
          <p class="mb-6 flex-1 text-sm leading-relaxed text-[#8b949e]">{{ $t('platforms.mobile.description') }}</p>
          <span
            class="inline-flex w-fit items-center gap-1.5 rounded-lg bg-[#21262d] px-3 py-1.5 text-xs font-medium text-[#c9d1d9]"
          >
            <i class="fa-solid fa-check text-[#3fb950]"></i>{{ $t('platforms.mobile.badge') }}
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
const localePath = useLocalePath()
</script>
