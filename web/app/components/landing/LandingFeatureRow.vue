<template>
  <div class="grid grid-cols-1 items-center gap-12 md:grid-cols-2 md:gap-16 lg:gap-20">
    <!-- Copy -->
    <div :class="reversed ? 'md:order-2' : 'md:order-1'">
      <div v-reveal class="mb-6 inline-flex items-center gap-2 rounded-full border px-4 py-1.5" :class="badgeClasses">
        <i :class="['fa-solid', icon, 'text-xs']"></i>
        <span class="text-xs font-semibold tracking-wide uppercase">{{ badge }}</span>
      </div>
      <h3 v-reveal class="mb-5 text-2xl font-bold tracking-tight text-[#f9f9f9] md:text-3xl lg:text-4xl">
        {{ heading }}
      </h3>
      <p v-reveal class="mb-8 max-w-xl text-base leading-relaxed text-[#8b949e]">
        {{ description }}
      </p>
      <ul class="space-y-3.5">
        <li
          v-for="(item, index) in features"
          :key="index"
          v-reveal="{ delay: index * 60 }"
          class="flex items-start gap-3"
        >
          <span
            class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full"
            :class="checkClasses"
          >
            <i class="fa-solid fa-check text-[10px]"></i>
          </span>
          <span class="text-[15px] leading-relaxed text-[#c9d1d9]">{{ item }}</span>
        </li>
      </ul>
    </div>

    <!-- Visual (provided by the parent) -->
    <div v-reveal="{ delay: 80 }" :class="reversed ? 'md:order-1' : 'md:order-2'">
      <slot />
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { LandingFeatureRowAccent, LandingFeatureRowProps } from '~/types/LandingFeatureRow'

/**
 * Alternating feature row: badge + heading + description + checklist on one
 * side, and a parent-provided visual mockup (default slot) on the other.
 */
const props: LandingFeatureRowProps = defineProps({
  icon: {
    type: String,
    required: true,
  },
  badge: {
    type: String,
    required: true,
  },
  heading: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  features: {
    type: Array as PropType<string[]>,
    required: true,
  },
  reversed: {
    type: Boolean,
    default: false,
  },
  accent: {
    type: String as PropType<LandingFeatureRowAccent>,
    default: 'emerald',
  },
})

/**
 * Badge border/background/text classes for the active accent.
 * @returns Tailwind class string for the badge pill.
 */
const badgeClasses: ComputedRef<string> = computed((): string =>
  props.accent === 'blue'
    ? 'border-[#58a6ff]/30 bg-[#58a6ff]/10 text-[#58a6ff]'
    : 'border-[#2BAD5F]/30 bg-[#2BAD5F]/10 text-[#3fb950]',
)

/**
 * Check-bullet background/text classes for the active accent.
 * @returns Tailwind class string for the bullet badge.
 */
const checkClasses: ComputedRef<string> = computed((): string =>
  props.accent === 'blue' ? 'bg-[#58a6ff]/15 text-[#58a6ff]' : 'bg-[#2BAD5F]/15 text-[#3fb950]',
)
</script>
