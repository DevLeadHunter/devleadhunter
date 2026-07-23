<template>
  <Transition name="cookie-rise">
    <div
      v-if="isMounted && needsChoice"
      class="fixed inset-x-0 bottom-0 z-[55] px-4 pb-4 sm:px-6 sm:pb-6"
      role="dialog"
      aria-live="polite"
      :aria-label="$t('cookies.title')"
    >
      <div
        class="landing-card mx-auto flex max-w-3xl flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between md:gap-8 md:p-6"
      >
        <div class="flex items-start gap-3">
          <LandingAsterisk class="mt-1 shrink-0 text-base text-[#e8a33c]" />
          <p class="text-sm leading-relaxed text-[#6b6355]">
            {{ $t('cookies.message') }}
            <NuxtLink
              :to="localePath('/privacy')"
              class="font-medium whitespace-nowrap text-[#1b1813] underline decoration-[#e3dccd] underline-offset-4 transition-colors hover:decoration-[#1b1813]"
            >
              {{ $t('cookies.learnMore') }}
            </NuxtLink>
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-3">
          <button type="button" class="landing-btn-ghost px-5 py-2.5 text-sm" @click="refuse">
            {{ $t('cookies.decline') }}
          </button>
          <button type="button" class="landing-btn-primary px-5 py-2.5 text-sm" @click="accept">
            {{ $t('cookies.accept') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref, onMounted } from 'vue'

const localePath = useLocalePath()
const { needsChoice, accept, refuse } = useCookieConsent()

/** Gate rendering to after client mount so the localStorage-based choice avoids an SSR flash. */
const isMounted: Ref<boolean> = ref(false)

onMounted((): void => {
  isMounted.value = true
})
</script>

<style scoped>
/* Slide + fade the banner up from the bottom */
.cookie-rise-enter-active,
.cookie-rise-leave-active {
  transition:
    opacity 0.35s ease,
    transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.cookie-rise-enter-from,
.cookie-rise-leave-to {
  opacity: 0;
  transform: translateY(16px);
}

@media (prefers-reduced-motion: reduce) {
  .cookie-rise-enter-active,
  .cookie-rise-leave-active {
    transition: opacity 0.2s ease;
  }
  .cookie-rise-enter-from,
  .cookie-rise-leave-to {
    transform: none;
  }
}
</style>
