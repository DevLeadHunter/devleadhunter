<template>
  <div class="relative overflow-hidden border-y border-[#e3dccd] py-3.5" :aria-label="t('landing.ticker.ariaLabel')">
    <!-- Edge fade masks -->
    <div
      class="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-[#f6f3ec] to-transparent md:w-32"
    ></div>
    <div
      class="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-[#f6f3ec] to-transparent md:w-32"
    ></div>

    <div class="landing-ticker-track flex w-max items-center">
      <div v-for="copy in 2" :key="copy" class="flex items-center" :aria-hidden="copy === 2 ? 'true' : undefined">
        <span v-for="item in tickerItems" :key="`${copy}-${item}`" class="flex items-center">
          <span class="font-label px-6 text-sm whitespace-nowrap text-[#6b6355]">{{ item }}</span>
          <span class="text-xs text-[#e8a33c]" aria-hidden="true">✳</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'

const { t } = useI18n()

/** Number of trade examples available in the i18n ticker namespace. */
const tickerItemCount: number = 8

/** Trade · city examples scrolled in the infinite ticker. */
const tickerItems: ComputedRef<string[]> = computed((): string[] =>
  Array.from({ length: tickerItemCount }, (_: unknown, index: number): string => t(`landing.ticker.item${index + 1}`)),
)
</script>
