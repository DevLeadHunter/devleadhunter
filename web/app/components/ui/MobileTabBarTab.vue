<template>
  <NuxtLink
    :to="props.to"
    :title="props.label"
    :aria-label="accessibleLabel"
    :aria-current="props.isActive ? 'page' : undefined"
    class="flex min-w-0 flex-1 flex-col items-center justify-center gap-1.5 transition-opacity [-webkit-tap-highlight-color:transparent] active:opacity-60"
    :class="props.isActive ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)]'"
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
    <span
      class="h-1 w-1 rounded-full"
      :class="props.isActive ? 'bg-[var(--app-accent)]' : 'bg-transparent'"
      aria-hidden="true"
    ></span>
  </NuxtLink>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { UiMobileTabBarTabProps } from '~/types/UiMobileTabBarTab'
import { computed } from 'vue'

const MAXIMUM_SHOWN_BADGE_COUNT: number = 99

/** One link of the installed app's tab bar: an icon, an amber dot when active, an optional count. */
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
