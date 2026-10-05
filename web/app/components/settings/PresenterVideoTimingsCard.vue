<template>
  <section class="space-y-5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex min-w-0 items-start gap-3">
        <UIcon name="i-lucide-scissors" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
        <div class="min-w-0">
          <p class="text-sm font-semibold text-[var(--app-ink)]">
            Déroulé de la vidéo · prise {{ props.take.take_number }}
          </p>
          <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ wording.flowDetail }}</p>
        </div>
      </div>
      <div v-if="props.takeOptions.length > 1" class="w-full @2xl:w-44">
        <UiSelectField
          :model-value="props.take.id"
          :options="props.takeOptions"
          @update:model-value="emit('select-take', $event)"
        />
      </div>
    </div>

    <div>
      <div
        class="flex h-9 w-full overflow-hidden rounded-lg border border-[var(--app-line)]"
        role="img"
        :aria-label="timelineAriaLabel"
      >
        <div
          v-for="segment in timelineSegments"
          :key="segment.key"
          :class="['flex min-w-0 items-center justify-center', segment.tone]"
          :style="{ width: segment.width }"
        >
          <span class="truncate px-1.5 text-[10px] font-semibold">{{ segment.shortLabel }}</span>
        </div>
      </div>
      <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[var(--app-ink-soft)]">
        <span
          v-for="segment in timelineSegments"
          :key="`legend-${segment.key}`"
          class="inline-flex items-center gap-1.5"
        >
          <span
            :class="['h-2.5 w-2.5 shrink-0 rounded-sm border border-[var(--app-line)]', segment.tone]"
            aria-hidden="true"
          />
          {{ segment.label }} · {{ PresenterVideoTimings.formatSeconds(segment.seconds) }}
        </span>
      </div>
    </div>

    <div v-if="hasEditableCuts" :class="['grid gap-3', timingGridClass]">
      <div v-if="!isRecordedTake">
        <label class="text-muted mb-1.5 block text-xs font-medium" :for="`${fieldIdPrefix}-intro`">Intro (s)</label>
        <input
          :id="`${fieldIdPrefix}-intro`"
          v-model.number="introSeconds"
          type="number"
          min="0"
          max="30"
          step="0.5"
          class="input-field"
          placeholder="5"
        />
      </div>
      <div v-if="!isReceptionistTake">
        <label class="text-muted mb-1.5 block text-xs font-medium" :for="`${fieldIdPrefix}-site`"
          >Partie site (s)</label
        >
        <input
          :id="`${fieldIdPrefix}-site`"
          v-model.number="siteScrollSeconds"
          type="number"
          min="0"
          :max="Math.round(middleSeconds)"
          step="0.5"
          class="input-field"
          placeholder="12"
        />
      </div>
      <div v-if="!isRecordedTake">
        <label class="text-muted mb-1.5 block text-xs font-medium" :for="`${fieldIdPrefix}-outro`">Outro (s)</label>
        <input
          :id="`${fieldIdPrefix}-outro`"
          v-model.number="outroSeconds"
          type="number"
          min="0"
          max="30"
          step="0.5"
          class="input-field"
          placeholder="8"
        />
      </div>
    </div>
    <p v-if="isRecordedTake" class="text-muted text-xs leading-relaxed">
      Intro ({{ PresenterVideoTimings.formatSeconds(introSeconds) }}) et outro ({{
        PresenterVideoTimings.formatSeconds(outroSeconds)
      }}) sont mesurées sur vos prises — {{ wording.recordedCutsDetail }}
    </p>
    <p v-if="!isReceptionistTake" class="text-muted text-xs leading-relaxed">
      Partie Storyblok :
      <span class="font-medium text-[var(--app-ink)]">{{
        PresenterVideoTimings.formatSeconds(storyblokSegmentSeconds)
      }}</span>
      (le reste du milieu). Plus la partie site est longue, plus le défilement est lent.
    </p>
    <UiCallout v-if="isStoryblokSegmentShort" variant="warning">
      Moins de {{ STORYBLOK_COMFORT_SECONDS }} s pour la séquence Storyblok : la démonstration d'édition sera coupée
      avant la fin. Raccourcissez la partie site si vous voulez la montrer en entier.
    </UiCallout>
    <UiCallout v-if="isSpaceChapterDropped" variant="warning">
      Moins de {{ MIN_WIDGET_SCENE_SECONDS + RECEPTIONIST_SPACE_CHAPTER_SECONDS }} s au milieu : la vidéo montrera le
      chat sans l'espace client. Allongez la prise du milieu pour le montrer.
    </UiCallout>

    <div class="space-y-3 border-t border-[var(--app-line)] pt-4">
      <div class="flex flex-col gap-2 @2xl:flex-row @2xl:justify-end">
        <button
          v-if="props.canBuildPreview"
          type="button"
          class="app-btn-secondary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          :disabled="props.isBuildRunning"
          @click="emit('preview', takeWithFormTimings())"
        >
          <UIcon
            :name="props.isBuildingPreview ? 'i-lucide-loader-circle' : 'i-lucide-play'"
            :class="['h-3.5 w-3.5', props.isBuildingPreview && 'animate-spin']"
          />
          {{ props.isBuildingPreview ? 'Génération en cours (~2-3 min)…' : 'Générer un aperçu' }}
        </button>
        <button
          v-if="hasEditableCuts"
          type="button"
          class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          :disabled="!hasUnsavedChanges || isSaving"
          @click="handleSave"
        >
          <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
          {{ isSaving ? 'Enregistrement…' : 'Enregistrer le déroulé' }}
        </button>
      </div>
      <template v-if="props.previewVideoUrl">
        <p class="text-muted text-xs leading-relaxed">
          Aperçu de ces réglages : rien n’est publié. Enregistrez le déroulé pour en faire l’exemple de la prise.
        </p>
        <video
          :key="props.previewVideoUrl"
          :src="props.previewVideoUrl"
          controls
          preload="auto"
          playsinline
          class="aspect-video w-full rounded-xl border border-[var(--app-line)] bg-black"
        />
      </template>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type { ProspectionScriptModule } from '~/composables/useProspectionScript'
import type { PresenterVideoModuleWording } from '~/types/PresenterVideoConfig'
import type { PresenterVideoTake } from '~/types/PresenterVideoTake'
import type {
  PresenterVideoTimelinePart,
  PresenterVideoTimelineSegment,
  PresenterVideoTimingsCardEmits,
  PresenterVideoTimingsCardProps,
} from '~/types/PresenterVideoTimingsCard'
import type { SelectFieldOption } from '~/types/SelectField'
import { computed, ref, watch } from 'vue'
import { PresenterVideoService } from '~/services/presenterVideoService'
import { PRESENTER_VIDEO_WORDINGS } from '~/constants/presenterVideoWordings'
import {
  MIN_WIDGET_SCENE_SECONDS,
  PresenterVideoTimings,
  RECEPTIONIST_SPACE_CHAPTER_SECONDS,
  STORYBLOK_COMFORT_SECONDS,
} from '~/utils/presenterVideoTimings'
import { useToast } from '~/composables/useToast'

const props: PresenterVideoTimingsCardProps = defineProps({
  take: {
    type: Object as PropType<PresenterVideoTake>,
    required: true,
  },
  module: {
    type: String as PropType<ProspectionScriptModule>,
    required: true,
  },
  takeOptions: {
    type: Array as PropType<SelectFieldOption<number>[]>,
    required: true,
  },
  canBuildPreview: {
    type: Boolean,
    default: false,
  },
  isBuildRunning: {
    type: Boolean,
    default: false,
  },
  isBuildingPreview: {
    type: Boolean,
    default: false,
  },
  previewVideoUrl: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const emit: EmitFn<PresenterVideoTimingsCardEmits> = defineEmits<PresenterVideoTimingsCardEmits>()

const toast: UseToastReturn = useToast()

const introSeconds: Ref<number> = ref(4)
const outroSeconds: Ref<number> = ref(5)
const siteScrollSeconds: Ref<number> = ref(12)
const isSaving: Ref<boolean> = ref(false)

const wording: ComputedRef<PresenterVideoModuleWording> = computed(
  (): PresenterVideoModuleWording => PRESENTER_VIDEO_WORDINGS[props.module],
)

const isReceptionistTake: ComputedRef<boolean> = computed((): boolean => props.module === 'ai-assistant')

/** Whether the take was filmed in-app (its cut points are measured). */
const isRecordedTake: ComputedRef<boolean> = computed((): boolean => props.take.source === 'recorded')

/** Prefix of the form ids, so the site's clip and the receptionist's can sit on one page. */
const fieldIdPrefix: ComputedRef<string> = computed((): string =>
  isReceptionistTake.value ? 'receptionist-video' : 'video',
)

/** Seconds between intro and outro — shared by the site scroll and the Storyblok sequence. */
const middleSeconds: ComputedRef<number> = computed((): number =>
  PresenterVideoTimings.middleSeconds(props.take.duration_seconds, introSeconds.value, outroSeconds.value),
)

/** Seconds left for the Storyblok editor sequence (the middle minus the site part). */
const storyblokSegmentSeconds: ComputedRef<number> = computed((): number =>
  Math.max(0, middleSeconds.value - siteScrollSeconds.value),
)

/** Whether the Storyblok demo will be visibly cut with the current split. */
const isStoryblokSegmentShort: ComputedRef<boolean> = computed(
  (): boolean => !isReceptionistTake.value && storyblokSegmentSeconds.value < STORYBLOK_COMFORT_SECONDS,
)

/** Seconds of the receptionist's middle given to the client space, 0 when the chat would be left too short. */
const spaceChapterSeconds: ComputedRef<number> = computed((): number =>
  PresenterVideoTimings.receptionistSpaceChapterSeconds(middleSeconds.value),
)

/** Whether the receptionist's video will skip its client-space chapter with the current cuts. */
const isSpaceChapterDropped: ComputedRef<boolean> = computed(
  (): boolean => isReceptionistTake.value && spaceChapterSeconds.value === 0,
)

/** Whether any cut point is edited by hand: the intro and outro of an imported clip, the site part of the site's. */
const hasEditableCuts: ComputedRef<boolean> = computed(
  (): boolean => !isReceptionistTake.value || !isRecordedTake.value,
)

const timingGridClass: ComputedRef<string> = computed((): string => {
  if (isReceptionistTake.value) return 'max-w-xs grid-cols-2'
  return isRecordedTake.value ? 'max-w-xs grid-cols-1' : 'max-w-md grid-cols-3'
})

const savedSiteSeconds: ComputedRef<number> = computed((): number => PresenterVideoTimings.siteSeconds(props.take))

const hasUnsavedChanges: ComputedRef<boolean> = computed((): boolean => {
  const hasIntroMoved: boolean = !PresenterVideoTimings.isSameCutPoint(introSeconds.value, props.take.intro_seconds)
  const hasOutroMoved: boolean = !PresenterVideoTimings.isSameCutPoint(outroSeconds.value, props.take.outro_seconds)
  const hasSiteMoved: boolean =
    !isReceptionistTake.value && !PresenterVideoTimings.isSameCutPoint(siteScrollSeconds.value, savedSiteSeconds.value)
  return hasIntroMoved || hasOutroMoved || hasSiteMoved
})

/** The parts of the timeline bar, widths proportional to their durations. */
const timelineSegments: ComputedRef<PresenterVideoTimelineSegment[]> = computed((): PresenterVideoTimelineSegment[] => {
  const duration: number = props.take.duration_seconds
  if (duration <= 0) return []
  const parts: PresenterVideoTimelinePart[] = isReceptionistTake.value
    ? receptionistTimelineParts()
    : siteTimelineParts()
  return parts.map(
    (part: PresenterVideoTimelinePart): PresenterVideoTimelineSegment => ({
      ...part,
      width: `${Math.max(2, (part.seconds / duration) * 100)}%`,
    }),
  )
})

/** Spoken description of the timeline for assistive tech. */
const timelineAriaLabel: ComputedRef<string> = computed((): string =>
  timelineSegments.value
    .map(
      (segment: PresenterVideoTimelineSegment): string =>
        `${segment.label} ${PresenterVideoTimings.formatSeconds(segment.seconds)}`,
    )
    .join(', '),
)

/** The form starts over only when the saved cut points change, so a refreshed take list never wipes an edit. */
const savedTimingsSignature: ComputedRef<string> = computed(
  (): string => `${props.take.id}:${props.take.intro_seconds}:${props.take.outro_seconds}:${props.take.site_seconds}`,
)

/**
 * The site video's timeline: intro, the site scrolling, the Storyblok editor, outro.
 * @returns The parts, without their widths.
 */
function siteTimelineParts(): PresenterVideoTimelinePart[] {
  return [
    {
      key: 'intro',
      label: 'Intro webcam',
      shortLabel: 'Intro',
      seconds: introSeconds.value,
      tone: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
    },
    {
      key: 'site',
      label: 'Site qui défile',
      shortLabel: 'Site',
      seconds: Math.min(siteScrollSeconds.value, middleSeconds.value),
      tone: 'bg-[var(--app-ink)] text-[var(--app-bg)]',
    },
    {
      key: 'storyblok',
      label: 'Éditeur Storyblok',
      shortLabel: 'Storyblok',
      seconds: storyblokSegmentSeconds.value,
      tone: 'bg-[var(--app-ink-soft)] text-[var(--app-bg)]',
    },
    {
      key: 'outro',
      label: 'Outro webcam',
      shortLabel: 'Outro',
      seconds: outroSeconds.value,
      tone: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
    },
  ]
}

/**
 * The receptionist video's timeline: intro, the chat answering, the client space when there is room, outro.
 * @returns The parts, without their widths.
 */
function receptionistTimelineParts(): PresenterVideoTimelinePart[] {
  const intro: PresenterVideoTimelinePart = {
    key: 'intro',
    label: 'Intro webcam',
    shortLabel: 'Intro',
    seconds: introSeconds.value,
    tone: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
  }
  const chat: PresenterVideoTimelinePart = {
    key: 'chat',
    label: 'Chat de la réceptionniste',
    shortLabel: 'Chat',
    seconds: middleSeconds.value - spaceChapterSeconds.value,
    tone: 'bg-[var(--app-ink)] text-[var(--app-bg)]',
  }
  const space: PresenterVideoTimelinePart = {
    key: 'space',
    label: 'Espace client',
    shortLabel: 'Espace',
    seconds: spaceChapterSeconds.value,
    tone: 'bg-[var(--app-ink-soft)] text-[var(--app-bg)]',
  }
  const outro: PresenterVideoTimelinePart = {
    key: 'outro',
    label: 'Outro webcam',
    shortLabel: 'Outro',
    seconds: outroSeconds.value,
    tone: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
  }
  return spaceChapterSeconds.value > 0 ? [intro, chat, space, outro] : [intro, chat, outro]
}

/** Start the form over from the take's saved cut points. */
function applySavedTimings(): void {
  introSeconds.value = props.take.intro_seconds
  outroSeconds.value = props.take.outro_seconds
  siteScrollSeconds.value = savedSiteSeconds.value
}

/**
 * Save the cut points of the take; its example, built with the previous ones, is dropped by the API.
 * @returns The take as saved, or null when the save failed (the user is told).
 */
async function saveTimings(): Promise<PresenterVideoTake | null> {
  isSaving.value = true
  try {
    const take: PresenterVideoTake = await PresenterVideoService.updateTakeTimings(
      props.take.id,
      introSeconds.value,
      outroSeconds.value,
      isReceptionistTake.value ? null : siteScrollSeconds.value,
    )
    emit('saved', take)
    return take
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la mise à jour')
    return null
  } finally {
    isSaving.value = false
  }
}

/** Save the cut points, as they are. */
async function handleSave(): Promise<void> {
  if (await saveTimings()) toast.success('Déroulé enregistré')
}

/**
 * The take as the form would save it, to preview its video before saving.
 * @returns A copy of the take with the cut points of the form.
 */
function takeWithFormTimings(): PresenterVideoTake {
  return {
    ...props.take,
    intro_seconds: introSeconds.value,
    outro_seconds: outroSeconds.value,
    site_seconds: isReceptionistTake.value ? null : siteScrollSeconds.value,
  }
}

watch(savedTimingsSignature, applySavedTimings, { immediate: true })

// Shrinking the middle (longer intro/outro) must never leave the site part overflowing it.
watch(middleSeconds, (middle: number): void => {
  if (siteScrollSeconds.value > middle) {
    siteScrollSeconds.value = Math.max(0, Math.round(middle * 2) / 2)
  }
})
</script>
