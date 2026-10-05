<template>
  <UiCollapsibleCard icon="i-lucide-clapperboard" title="Comment enregistrer votre clip">
    <div class="space-y-6 px-4 py-5">
      <ol class="space-y-4">
        <li v-for="(step, index) in workflowSteps" :key="step.title" class="flex items-start gap-3">
          <span
            class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] text-[11px] font-bold text-[var(--app-ink)]"
          >
            {{ index + 1 }}
          </span>
          <div class="min-w-0 pt-0.5">
            <p class="text-sm font-medium text-[var(--app-ink)]">{{ step.title }}</p>
            <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ step.detail }}</p>
          </div>
        </li>
      </ol>
      <div class="space-y-4 rounded-lg bg-[var(--app-bg)] p-4">
        <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
          Le speech à lire (~{{ speechTotalSeconds }} s)
        </p>
        <div v-for="line in speechLines" :key="line.timing + line.role" class="flex items-start gap-3">
          <span
            class="mt-0.5 w-16 shrink-0 rounded-md bg-[var(--app-surface-2)] px-2 py-1 text-center text-[10px] font-bold tracking-wide text-[var(--app-ink-soft)] uppercase"
          >
            {{ line.timing }}
          </span>
          <div class="min-w-0">
            <p class="text-[10px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
              {{ line.role }}
            </p>
            <p class="mt-0.5 text-sm leading-relaxed text-[var(--app-ink)] italic">« {{ line.text }} »</p>
          </div>
        </div>
      </div>
      <div class="space-y-3">
        <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">Conseils de tournage</p>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="tip in RECORDING_TIPS"
            :key="tip"
            class="rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-1 text-xs text-[var(--app-ink)]"
          >
            {{ tip }}
          </span>
        </div>
        <p class="text-muted flex items-start gap-2 text-xs leading-relaxed">
          <UIcon name="i-lucide-circle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
          <span>
            <strong class="font-semibold text-[var(--app-ink)]">Restez générique</strong> :
            {{ PRESENTER_VIDEO_WORDINGS[props.module].stayGenericTip }}
          </span>
        </p>
      </div>
    </div>
  </UiCollapsibleCard>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { UseAuthReturn } from '~/types/Composables'
import type { ProspectionScriptModule, ProspectionScriptSegment } from '~/composables/useProspectionScript'
import type {
  PresenterVideoGuideStep,
  PresenterVideoRecordingGuideProps,
  PresenterVideoSpeechLine,
} from '~/types/PresenterVideoRecordingGuide'
import { computed } from 'vue'
import { buildScriptFor } from '~/composables/useProspectionScript'
import { PRESENTER_VIDEO_WORDINGS } from '~/constants/presenterVideoWordings'
import { useAuth } from '~/composables/useAuth'

const props: PresenterVideoRecordingGuideProps = defineProps({
  module: {
    type: String as PropType<ProspectionScriptModule>,
    required: true,
  },
  isImporting: {
    type: Boolean,
    default: false,
  },
})

const { user }: UseAuthReturn = useAuth()

/** Short recording tips rendered as pills. */
const RECORDING_TIPS: string[] = ['1080p suffit', 'Lumière face à vous', 'Regardez l’objectif']

/** The recommended parts of this module's speech, as the teleprompter shows them. */
const scriptSegments: ComputedRef<ProspectionScriptSegment[]> = computed((): ProspectionScriptSegment[] =>
  buildScriptFor(props.module, user.value?.name ?? '', user.value?.company_name ?? ''),
)

/** Length of the whole recommended speech, for the guide. */
const speechTotalSeconds: ComputedRef<number> = computed((): number =>
  scriptSegments.value.reduce((total: number, segment: ProspectionScriptSegment): number => {
    return total + segment.targetSeconds
  }, 0),
)

const speechLines: ComputedRef<PresenterVideoSpeechLine[]> = computed((): PresenterVideoSpeechLine[] =>
  scriptSegments.value.map(
    (segment: ProspectionScriptSegment): PresenterVideoSpeechLine => ({
      timing: `~${segment.targetSeconds} s`,
      role: segment.title,
      text: segment.text,
    }),
  ),
)

/** The three steps of the folded guide, worded for the chosen capture method. */
const workflowSteps: ComputedRef<PresenterVideoGuideStep[]> = computed((): PresenterVideoGuideStep[] => [
  {
    title: `Filmez-vous ~${speechTotalSeconds.value} s, une seule fois`,
    detail: props.isImporting
      ? 'Webcam + micro, face caméra, en lisant le speech ci-dessous.'
      : 'En trois prises courtes dans l’application, ou avec l’outil de votre choix puis en important le fichier.',
  },
  {
    title: props.isImporting ? 'Déposez le fichier' : 'Gardez vos prises',
    detail: 'C’est votre seule action : le découpage et la personnalisation sont ensuite automatiques.',
  },
  {
    title: 'Chaque prospect reçoit sa vidéo',
    detail: PRESENTER_VIDEO_WORDINGS[props.module].resultStepDetail,
  },
])
</script>
