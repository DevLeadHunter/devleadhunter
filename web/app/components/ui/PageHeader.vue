<template>
  <header class="flex flex-col gap-4 @2xl:flex-row @2xl:flex-wrap @2xl:items-end @2xl:justify-between @2xl:gap-x-6">
    <div class="min-w-0 @2xl:min-w-64 @2xl:flex-1">
      <p v-if="props.eyebrow" class="app-label flex items-center gap-2">
        <LandingAsterisk v-if="props.hasEyebrowMark" class="text-[0.6rem] text-[var(--app-accent)]" />
        {{ props.eyebrow }}
      </p>
      <h1 :class="['app-page-title', props.eyebrow && 'mt-2']">{{ props.title }}</h1>
      <p v-if="props.description || slots.description" class="mt-1.5 max-w-2xl text-sm text-[var(--app-ink-soft)]">
        <slot name="description">{{ props.description }}</slot>
      </p>
    </div>

    <div
      v-if="slots.actions || slots['primary-action']"
      class="flex flex-col gap-2 @2xl:ml-auto @2xl:shrink-0 @2xl:flex-row @2xl:items-center"
    >
      <div
        v-if="slots.actions"
        class="grid grid-cols-2 gap-2 @2xl:flex @2xl:items-center [&>*:last-child:nth-child(odd)]:col-span-2"
      >
        <slot name="actions" />
      </div>
      <div v-if="slots['primary-action']" class="order-first flex flex-col @2xl:order-none">
        <slot name="primary-action" />
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
import type { PropType, Slots } from 'vue'
import type { UiPageHeaderProps } from '~/types/UiPageHeader'
import { useSlots } from 'vue'

/**
 * Title of a dashboard page with its actions. On a phone the primary action spans the width and the
 * others share rows two by two; from the tablet width everything stands on one line, and when the
 * actions do not fit beside the title they move below it together, never split over two lines.
 */
const props: UiPageHeaderProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  eyebrow: {
    type: String as PropType<string | null>,
    default: null,
  },
  hasEyebrowMark: {
    type: Boolean,
    default: true,
  },
  description: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const slots: Slots = useSlots()
</script>
