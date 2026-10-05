<template>
  <NuxtLink
    :to="props.to"
    :title="props.label"
    :aria-label="accessibleLabel"
    :aria-current="props.isActive ? 'page' : undefined"
    class="flex min-w-0 flex-1 flex-col items-center justify-center gap-1 transition-opacity [-webkit-tap-highlight-color:transparent] active:opacity-60"
    :class="props.isActive ? 'text-[var(--app-accent-ink)]' : 'text-[var(--app-ink-soft)]'"
  >
    <span class="relative">
      <UIcon :name="props.icon" class="size-6" />
      <span
        v-if="props.badgeCount > 0"
        class="font-label absolute -top-1.5 -right-2.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--app-accent)] px-1 text-[10px] leading-none font-semibold text-[#1b1508] tabular-nums ring-2 ring-[var(--app-surface)]"
        aria-hidden="true"
      >
        {{ badgeLabel }}
      </span>
    </span>
    <!-- La place de l'iPad permet d'écrire chaque onglet sous son icône ; le téléphone garde les icônes seules. -->
    <span
      class="hidden max-w-full truncate px-1 text-[11px] leading-3 md:block"
      :class="props.isActive ? 'font-semibold' : 'font-medium'"
      aria-hidden="true"
    >
      {{ props.caption ?? props.label }}
    </span>
  </NuxtLink>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { UiMobileTabBarTabProps } from '~/types/UiMobileTabBarTab'
import { computed } from 'vue'

const MAXIMUM_SHOWN_BADGE_COUNT: number = 99

/**
 * One link of the installed app's tab bar: an icon turning amber when its section is open, an optional count,
 * and from the iPad's width a short caption under the icon (the full label otherwise).
 */
const props: UiMobileTabBarTabProps = defineProps({
  to: {
    type: String,
    required: true,
  },
  icon: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  caption: {
    type: String as PropType<string | null>,
    default: null,
  },
  isActive: {
    type: Boolean,
    required: true,
  },
  badgeCount: {
    type: Number,
    default: 0,
  },
  badgeDescription: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const badgeLabel: ComputedRef<string> = computed((): string =>
  props.badgeCount > MAXIMUM_SHOWN_BADGE_COUNT ? `${MAXIMUM_SHOWN_BADGE_COUNT}+` : String(props.badgeCount),
)

const accessibleLabel: ComputedRef<string> = computed((): string =>
  props.badgeCount > 0 && props.badgeDescription ? `${props.label}, ${props.badgeDescription}` : props.label,
)
</script>
