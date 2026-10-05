<template>
  <!-- Souris : actions à côté du titre. Tactile (iPad) : actions sous le titre, en une rangée qui prend toute la largeur. -->
  <header
    class="flex flex-col gap-4 @2xl:pointer-fine:flex-row @2xl:pointer-fine:flex-wrap @2xl:pointer-fine:items-end @2xl:pointer-fine:justify-between @2xl:pointer-fine:gap-x-6"
  >
    <div class="min-w-0 @2xl:pointer-fine:min-w-64 @2xl:pointer-fine:flex-1">
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
      class="flex flex-col gap-2 @2xl:flex-row @2xl:items-center @2xl:pointer-coarse:flex-wrap @2xl:pointer-fine:ml-auto @2xl:pointer-fine:shrink-0 @2xl:pointer-coarse:[&>*]:flex-auto @2xl:pointer-coarse:[&>*>*]:flex-auto"
    >
      <div v-if="slots.actions" class="grid grid-cols-2 gap-2 @2xl:contents [&>*:last-child:nth-child(odd)]:col-span-2">
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
 * others share rows two by two. From the tablet width, with a mouse everything stands on one line and
 * the actions move below the title together when they do not fit beside it; on a touch screen they
 * always sit below the title, stretched over one finger-sized row.
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
