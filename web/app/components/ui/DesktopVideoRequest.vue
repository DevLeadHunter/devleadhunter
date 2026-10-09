<template>
  <div>
    <p class="flex items-start gap-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
      <UIcon :name="statusIcon" :class="['mt-0.5 h-4 w-4 shrink-0', { 'animate-spin': props.isBuildStarted }]" />
      <span>{{ statusLabel }}</span>
    </p>
    <button
      v-if="!props.isBuildStarted"
      type="button"
      class="btn-secondary mt-2 w-full text-xs"
      :disabled="props.isCancelling"
      @click="emit('cancel')"
    >
      {{ props.isCancelling ? 'Annulation…' : 'Annuler la demande' }}
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn } from 'vue'
import type { UiDesktopVideoRequestEmits, UiDesktopVideoRequestProps } from '~/types/UiDesktopVideoRequest'
import { computed } from 'vue'

/** A video left to the owner's PC: what it waits for, and the button to withdraw the request. */
const props: UiDesktopVideoRequestProps = defineProps({
  isBuildStarted: {
    type: Boolean,
    required: true,
  },
  isDesktopAppOnline: {
    type: Boolean,
    required: true,
  },
  isWaitingForStoryblokSpace: {
    type: Boolean,
    default: false,
  },
  isCancelling: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiDesktopVideoRequestEmits> = defineEmits<UiDesktopVideoRequestEmits>()

const statusIcon: ComputedRef<string> = computed((): string => {
  if (props.isBuildStarted) {
    return 'i-lucide-loader-circle'
  }
  return props.isWaitingForStoryblokSpace ? 'i-lucide-hourglass' : 'i-lucide-monitor'
})

const statusLabel: ComputedRef<string> = computed((): string => {
  if (props.isBuildStarted) {
    return 'Votre PC génère la vidéo (2 à 3 minutes). Vous pouvez quitter cette page.'
  }
  if (props.isWaitingForStoryblokSpace) {
    return "En attente de l'espace Storyblok du site : votre PC fera la vidéo dès qu'il sera créé."
  }
  if (props.isDesktopAppOnline) {
    return 'Demande envoyée à votre PC : il lance la génération dans la minute.'
  }
  return "En attente de votre PC : l'application DevLeadHunter générera la vidéo dès qu'elle sera ouverte. Elle démarre avec Windows."
})
</script>
