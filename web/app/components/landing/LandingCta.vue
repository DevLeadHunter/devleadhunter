<template>
  <section class="relative overflow-hidden bg-[#050505] py-24 md:py-32">
    <div
      class="landing-glow top-1/2 left-1/2 h-[360px] w-[680px] -translate-x-1/2 -translate-y-1/2 bg-[#2BAD5F]/12"
    ></div>

    <div class="relative z-10 container mx-auto px-4 md:px-6 lg:px-8">
      <div
        v-reveal
        class="mx-auto max-w-4xl overflow-hidden rounded-3xl border border-[#2BAD5F]/25 bg-gradient-to-b from-[#0d1117] to-[#050505] px-6 py-14 text-center md:px-12 md:py-16"
      >
        <h2 class="mx-auto mb-5 max-w-2xl text-3xl font-bold tracking-tight text-[#f9f9f9] md:text-4xl lg:text-5xl">
          {{ $t('cta.title') }}
        </h2>
        <p class="mx-auto mb-9 max-w-2xl text-base leading-relaxed text-[#8b949e] md:text-lg">
          {{ $t('cta.subtitle') }}
        </p>
        <div class="flex flex-col items-center justify-center gap-3 sm:flex-row">
          <NuxtLink :to="localePath('/signup')" class="btn-emerald w-full py-3.5 text-base sm:w-auto">
            {{ $t('cta.primary') }}<i class="fa-solid fa-arrow-right text-sm"></i>
          </NuxtLink>
          <NuxtLink :to="localePath('/login')" class="btn-ghost w-full py-3.5 text-base sm:w-auto">
            {{ $t('nav.login') }}
          </NuxtLink>
        </div>
        <p class="mt-6 inline-flex items-center gap-2 text-sm text-[#8b949e]">
          <i class="fa-solid fa-shield-halved text-[#3fb950]"></i>{{ $t('cta.note') }}
        </p>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
const localePath = useLocalePath()
</script>
