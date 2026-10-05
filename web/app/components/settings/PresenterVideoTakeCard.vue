<template>
  <article
    :class="[
      'flex min-w-0 flex-col overflow-hidden rounded-xl border bg-[var(--app-surface)]',
      props.take.is_active ? 'border-[var(--app-ink)]' : 'border-[var(--app-line)]',
    ]"
  >
    <header class="flex items-start justify-between gap-3 px-4 pt-3.5 pb-3">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-[var(--app-ink)]">Prise {{ props.take.take_number }}</p>
        <p class="text-muted mt-0.5 truncate text-xs">{{ recordingDetailsLabel }}</p>
      </div>
      <div class="flex shrink-0 items-center gap-1.5">
        <span v-if="props.take.is_clip_missing" class="app-badge app-badge--danger font-medium">
          <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5" />
          Fichier introuvable
        </span>
        <span v-else-if="props.take.is_active" class="app-badge app-badge--success font-medium">
          <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
          Utilisée
        </span>
        <button
          v-if="props.canDelete"
          type="button"
          class="-mr-1.5 flex h-9 w-9 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-red)] disabled:cursor-not-allowed disabled:opacity-50 @2xl:pointer-fine:h-7 @2xl:pointer-fine:w-7"
          :disabled="props.isDeleting"
          :aria-label="`Supprimer la prise ${props.take.take_number}`"
          :title="`Supprimer la prise ${props.take.take_number}`"
          @click="emit('delete')"
        >
          <UIcon
            :name="props.isDeleting ? 'i-lucide-loader-circle' : 'i-lucide-trash-2'"
            :class="['h-4 w-4', props.isDeleting && 'animate-spin']"
          />
        </button>
      </div>
    </header>

    <div class="aspect-video bg-black">
      <video
        v-if="shownVideoUrl"
        :key="shownVideoUrl"
        :src="shownVideoUrl"
        controls
        playsinline
        preload="metadata"
        class="h-full w-full"
        @loadeddata="revealFirstFrame"
      />
      <div v-else class="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <UIcon name="i-lucide-clapperboard" class="h-6 w-6 text-white/60" />
        <p class="text-xs text-white/70">Aucune vidéo à montrer pour cette prise.</p>
      </div>
    </div>

    <div class="flex flex-1 flex-col gap-3 px-4 py-3">
      <p class="text-muted text-xs leading-relaxed">
        {{ videoCaption }}
        <button
          v-if="hasExample && props.take.clip_url"
          type="button"
          class="cursor-pointer font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
          @click="isShowingClipAlone = !isShowingClipAlone"
        >
          {{ isShowingClipAlone ? 'Revoir l’exemple' : 'Voir le clip seul' }}
        </button>
      </p>
      <div v-if="!props.take.is_active || props.canBuildExample" class="mt-auto flex flex-wrap items-center gap-2">
        <button
          v-if="!props.take.is_active"
          type="button"
          class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-8 @2xl:pointer-fine:px-3 @2xl:pointer-fine:text-xs"
          :disabled="props.isActivating || props.take.is_clip_missing"
          @click="emit('activate')"
        >
          <UIcon
            :name="props.isActivating ? 'i-lucide-loader-circle' : 'i-lucide-check'"
            :class="['h-3.5 w-3.5', props.isActivating && 'animate-spin']"
          />
          Utiliser cette prise
        </button>
        <button
          v-if="props.canBuildExample"
          type="button"
          class="app-btn-secondary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-8 @2xl:pointer-fine:px-3 @2xl:pointer-fine:text-xs"
          :disabled="props.isBuildingExample || props.isAnotherBuildRunning || props.take.is_clip_missing"
          @click="emit('build-example')"
        >
          <UIcon
            :name="props.isBuildingExample ? 'i-lucide-loader-circle' : 'i-lucide-clapperboard'"
            :class="['h-3.5 w-3.5', props.isBuildingExample && 'animate-spin']"
          />
          {{ buildButtonLabel }}
        </button>
      </div>
    </div>
  </article>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { PresenterVideoTake } from '~/types/PresenterVideoTake'
import type { PresenterVideoTakeCardEmits, PresenterVideoTakeCardProps } from '~/types/PresenterVideoTakeCard'
import { computed, ref } from 'vue'
import { formatShortMonthDayTime } from '~/utils/date'

const props: PresenterVideoTakeCardProps = defineProps({
  take: {
    type: Object as PropType<PresenterVideoTake>,
    required: true,
  },
  canBuildExample: {
    type: Boolean,
    default: false,
  },
  isBuildingExample: {
    type: Boolean,
    default: false,
  },
  isAnotherBuildRunning: {
    type: Boolean,
    default: false,
  },
  isActivating: {
    type: Boolean,
    default: false,
  },
  isDeleting: {
    type: Boolean,
    default: false,
  },
  canDelete: {
    type: Boolean,
    default: false,
  },
  selectedExampleDemoId: {
    type: Number as PropType<number | null>,
    default: null,
  },
})

const emit: EmitFn<PresenterVideoTakeCardEmits> = defineEmits<PresenterVideoTakeCardEmits>()

const isShowingClipAlone: Ref<boolean> = ref(false)

const hasExample: ComputedRef<boolean> = computed((): boolean => Boolean(props.take.example_video_url))

const shownVideoUrl: ComputedRef<string | null> = computed((): string | null =>
  hasExample.value && !isShowingClipAlone.value ? props.take.example_video_url : props.take.clip_url,
)

const recordingDetailsLabel: ComputedRef<string> = computed((): string => {
  const durationLabel: string = `${Math.round(props.take.duration_seconds)} s`
  const sourceLabel: string = props.take.source === 'recorded' ? 'Filmée dans l’application' : 'Fichier importé'
  if (!props.take.created_at) return `${durationLabel} · ${sourceLabel}`
  return `${formatShortMonthDayTime(props.take.created_at)} · ${durationLabel} · ${sourceLabel}`
})

const videoCaption: ComputedRef<string> = computed((): string => {
  if (!hasExample.value) {
    return props.take.clip_url ? 'Pas encore d’exemple : vous voyez le clip seul.' : 'Pas encore d’exemple.'
  }
  if (isShowingClipAlone.value) return 'Le clip seul, tel que vous l’avez filmé.'
  const builtOn: string = `Exemple monté sur ${props.take.example_subject_name ?? 'une démo'}`
  const isOnAnotherDemo: boolean =
    props.selectedExampleDemoId !== null && props.take.example_subject_id !== props.selectedExampleDemoId
  return isOnAnotherDemo ? `${builtOn}, pas sur la démo choisie.` : `${builtOn}.`
})

const buildButtonLabel: ComputedRef<string> = computed((): string => {
  if (props.isBuildingExample) return 'Montage en cours…'
  return hasExample.value ? 'Refaire l’exemple' : 'Générer l’exemple'
})

/**
 * Force the first decoded frame so the preview is not a black box on load.
 * @param event - The video's loadeddata event.
 */
function revealFirstFrame(event: Event): void {
  const video: HTMLVideoElement | null = event.target as HTMLVideoElement | null
  if (!video || video.currentTime > 0) return
  try {
    video.currentTime = Math.min(0.1, (video.duration || 1) / 2)
  } catch {
    // Some engines throw if the media is not seekable yet — safe to ignore.
  }
}
</script>
