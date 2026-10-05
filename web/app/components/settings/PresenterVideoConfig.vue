<template>
  <div class="space-y-6">
    <UiLoader v-if="isLoading" />

    <template v-else>
      <section class="space-y-4">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">{{ wording.title }}</h2>
          <span v-if="activeTake?.is_clip_missing" class="app-badge app-badge--danger font-medium">
            <UIcon name="i-lucide-triangle-alert" class="h-3.5 w-3.5" />
            Fichier introuvable
          </span>
          <span v-else-if="activeTake" class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Prêt
          </span>
        </div>
        <p v-if="wording.subtitle" class="text-muted text-sm leading-relaxed">{{ wording.subtitle }}</p>

        <UiCallout v-if="activeTake?.is_clip_missing" variant="danger">
          La prise utilisée est enregistrée mais son fichier est introuvable sur le stockage : les vidéos de prospection
          ne peuvent pas être générées. Choisissez une autre prise ou ajoutez-en une.
        </UiCallout>

        <PresenterVideoTakeCapture
          v-if="isCaptureShown"
          :module="props.module"
          :auto-generate="autoGenerate"
          :can-go-back-to-takes="takes.length > 0"
          @saved="handleTakeSaved"
          @back-to-takes="isAddingTake = false"
        />

        <template v-else>
          <p class="text-muted text-sm leading-relaxed">
            Une nouvelle prise ne remplace rien : comparez leurs vidéos d’exemple, puis choisissez celle que vos vidéos
            utilisent. Les vidéos déjà générées gardent leur prise.
          </p>

          <div
            v-if="isDesktopApp"
            class="space-y-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
          >
            <div class="flex flex-col gap-3 @2xl:flex-row @2xl:items-end">
              <div class="min-w-0 flex-1">
                <label class="text-muted mb-1.5 block text-xs font-medium">{{ wording.exampleDemoLabel }}</label>
                <UiSelectField
                  v-if="exampleDemos.length > 0"
                  v-model="selectedExampleDemoId"
                  :options="exampleDemoOptions"
                  :placeholder="wording.exampleDemoPlaceholder"
                  :disabled="isBuildRunning"
                />
                <p v-else class="text-muted text-xs leading-relaxed">{{ wording.noExampleDemo }}</p>
              </div>
              <button
                type="button"
                class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
                :disabled="!selectedExampleDemo || takesWithoutExampleOnDemo.length === 0 || isBuildRunning"
                @click="buildMissingExamples"
              >
                <UIcon
                  :name="isBuildRunning ? 'i-lucide-loader-circle' : 'i-lucide-clapperboard'"
                  :class="['h-3.5 w-3.5', isBuildRunning && 'animate-spin']"
                />
                {{ buildAllButtonLabel }}
              </button>
            </div>
            <p class="text-muted text-xs leading-relaxed">{{ wording.exampleDetail }}</p>
          </div>
          <div
            v-else
            class="flex items-start gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
          >
            <UIcon name="i-lucide-monitor" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
            <p class="text-muted text-xs leading-relaxed">
              Les vidéos d’exemple se montent dans l’application desktop : ouvrez-la pour comparer vos prises. D’ici,
              vous pouvez les regarder et choisir celle à utiliser.
            </p>
          </div>

          <div class="grid gap-4 @2xl:grid-cols-2">
            <PresenterVideoTakeCard
              v-for="take in takes"
              :key="take.id"
              :take="take"
              :can-build-example="canBuildExamples"
              :is-building-example="buildingTakeId === take.id"
              :is-another-build-running="isBuildRunning && buildingTakeId !== take.id"
              :is-activating="activatingTakeId === take.id"
              :is-deleting="deletingTakeId === take.id"
              :can-delete="!take.is_active || takes.length === 1"
              :selected-example-demo-id="selectedExampleDemo?.id ?? null"
              @activate="activateTake(take)"
              @build-example="buildExample(take)"
              @delete="askDeleteTake(take)"
            />
            <button
              type="button"
              class="flex min-h-48 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--app-line)] px-6 py-8 text-center transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]"
              @click="isAddingTake = true"
            >
              <span
                class="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]"
              >
                <UIcon name="i-lucide-plus" class="h-5 w-5 text-[var(--app-ink)]" />
              </span>
              <span class="text-sm font-semibold text-[var(--app-ink)]">Nouvelle prise</span>
              <span class="text-muted text-xs leading-relaxed text-balance">
                Filmez ou importez une autre version, sans perdre celles-ci.
              </span>
            </button>
          </div>
        </template>
      </section>

      <div
        v-if="takes.length > 0"
        class="flex items-center justify-between gap-4 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
      >
        <div class="flex min-w-0 items-start gap-3">
          <UIcon name="i-lucide-sparkles" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
          <div class="min-w-0">
            <p class="text-sm font-semibold text-[var(--app-ink)]">Génération automatique</p>
            <p class="text-muted text-xs leading-relaxed">{{ wording.autoGenerateDetail }}</p>
          </div>
        </div>
        <UiSwitch
          :id="`${props.module}-auto-generate`"
          :model-value="autoGenerate"
          @update:model-value="handleAutoGenerateChange"
        />
      </div>

      <PresenterVideoTimingsCard
        v-if="timingsTake && !isCaptureShown"
        :take="timingsTake"
        :module="props.module"
        :take-options="takeOptions"
        :can-build-preview="canBuildExamples"
        :is-build-running="isBuildRunning"
        :is-building-preview="isBuildingTimingsPreview"
        :preview-video-url="timingsPreviewUrl"
        @select-take="timingsTakeId = $event"
        @saved="handleTimingsSaved"
        @preview="previewTimings"
      />
    </template>

    <UiConfirmModal
      ref="deleteModalRef"
      title="Supprimer la prise"
      :message="deleteTakeMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDeleteConfirmed"
    />

    <UiVideoGenerationModal
      :open="videoProgress.isOpen.value"
      :title="buildModalTitle"
      :steps="videoProgress.steps.value"
      :log-lines="videoProgress.logLines.value"
      :elapsed-seconds="videoProgress.elapsedSeconds.value"
      :error-message="videoProgress.errorMessage.value"
      :is-running="videoProgress.isRunning.value"
      @close="videoProgress.close()"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type { ProspectionScriptModule } from '~/composables/useProspectionScript'
import type { UseVideoGenerationProgressReturn } from '~/composables/useVideoGenerationProgress'
import type {
  PresenterVideoConfigEmits,
  PresenterVideoConfigProps,
  PresenterVideoExampleDemo,
  PresenterVideoModuleWording,
  PresenterVideoTimingsPreview,
} from '~/types/PresenterVideoConfig'
import type { PresenterVideoTake, PresenterVideoTakeList } from '~/types/PresenterVideoTake'
import type { DemoSite, DemoSiteListResponse } from '~/services/demoSiteService'
import type { PreviewVideoResult } from '~/services/storyblokSidecarService'
import type { AssistantPreviewVideoResult } from '~/types/AssistantSidecar'
import type { AiAssistantListResponse, AiAssistantSummary } from '~/types/AiAssistant'
import type { SelectFieldOption } from '~/types/SelectField'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { PresenterVideoService } from '~/services/presenterVideoService'
import { DemoSiteService } from '~/services/demoSiteService'
import { AiAssistantService } from '~/services/aiAssistantService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { AssistantSidecarService } from '~/services/assistantSidecarService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import { useVideoGenerationProgress } from '~/composables/useVideoGenerationProgress'
import { PRESENTER_VIDEO_WORDINGS } from '~/constants/presenterVideoWordings'
import { RECEPTIONIST_VIDEO_BUILD_PHASES, SITE_VIDEO_BUILD_PHASES } from '~/constants/videoBuildPhases'
import { PresenterVideoTimings } from '~/utils/presenterVideoTimings'
import { useToast } from '~/composables/useToast'

const props: PresenterVideoConfigProps = defineProps({
  module: {
    type: String as PropType<ProspectionScriptModule>,
    default: 'websites',
  },
})

const emit: EmitFn<PresenterVideoConfigEmits> = defineEmits<PresenterVideoConfigEmits>()

const toast: UseToastReturn = useToast()
const videoProgress: UseVideoGenerationProgressReturn = useVideoGenerationProgress(
  props.module === 'ai-assistant' ? RECEPTIONIST_VIDEO_BUILD_PHASES : SITE_VIDEO_BUILD_PHASES,
)

const takes: Ref<PresenterVideoTake[]> = ref([])
const autoGenerate: Ref<boolean> = ref(true)
const isLoading: Ref<boolean> = ref(true)

/** Whether the capture UI is shown on purpose while takes already exist. */
const isAddingTake: Ref<boolean> = ref(false)

/** Whether the app runs in the desktop shell (the example videos need the sidecar). */
const isDesktopApp: Ref<boolean> = ref(false)

const exampleDemos: Ref<PresenterVideoExampleDemo[]> = ref([])

/** Site or receptionist used as the example, as a select value. */
const selectedExampleDemoId: Ref<string> = ref('')

/** One build at a time: the desktop builder keeps a single result per demo. */
const buildingTakeId: Ref<number | null> = ref(null)
const isBuildingTimingsPreview: Ref<boolean> = ref(false)
const timingsPreview: Ref<PresenterVideoTimingsPreview | null> = ref(null)
const activatingTakeId: Ref<number | null> = ref(null)
const deletingTakeId: Ref<number | null> = ref(null)
const timingsTakeId: Ref<number | null> = ref(null)
const takePendingDeletion: Ref<PresenterVideoTake | null> = ref(null)
const deleteModalRef: Ref<{ open: () => void } | null> = ref(null)

const wording: ComputedRef<PresenterVideoModuleWording> = computed(
  (): PresenterVideoModuleWording => PRESENTER_VIDEO_WORDINGS[props.module],
)

const activeTake: ComputedRef<PresenterVideoTake | null> = computed(
  (): PresenterVideoTake | null => takes.value.find((take: PresenterVideoTake): boolean => take.is_active) ?? null,
)

const isCaptureShown: ComputedRef<boolean> = computed((): boolean => takes.value.length === 0 || isAddingTake.value)

const timingsTake: ComputedRef<PresenterVideoTake | null> = computed(
  (): PresenterVideoTake | null =>
    takes.value.find((take: PresenterVideoTake): boolean => take.id === timingsTakeId.value) ??
    activeTake.value ??
    takes.value[0] ??
    null,
)

const timingsPreviewUrl: ComputedRef<string | null> = computed((): string | null => {
  if (!timingsPreview.value || timingsPreview.value.take.id !== timingsTake.value?.id) return null
  return timingsPreview.value.url
})

const takeOptions: ComputedRef<SelectFieldOption<number>[]> = computed((): SelectFieldOption<number>[] =>
  takes.value.map(
    (take: PresenterVideoTake): SelectFieldOption<number> => ({
      value: take.id,
      label: take.is_active ? `Prise ${take.take_number} (utilisée)` : `Prise ${take.take_number}`,
    }),
  ),
)

const exampleDemoOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] =>
  exampleDemos.value.map(
    (demo: PresenterVideoExampleDemo): SelectFieldOption => ({ value: String(demo.id), label: demo.name }),
  ),
)

const selectedExampleDemo: ComputedRef<PresenterVideoExampleDemo | null> = computed(
  (): PresenterVideoExampleDemo | null =>
    exampleDemos.value.find(
      (demo: PresenterVideoExampleDemo): boolean => String(demo.id) === selectedExampleDemoId.value,
    ) ?? null,
)

const canBuildExamples: ComputedRef<boolean> = computed(
  (): boolean => isDesktopApp.value && selectedExampleDemo.value !== null,
)

const isBuildRunning: ComputedRef<boolean> = computed(
  (): boolean => buildingTakeId.value !== null || isBuildingTimingsPreview.value,
)

const takesWithoutExampleOnDemo: ComputedRef<PresenterVideoTake[]> = computed((): PresenterVideoTake[] =>
  takes.value.filter(
    (take: PresenterVideoTake): boolean =>
      !take.is_clip_missing &&
      (take.example_video_url === null || take.example_subject_id !== selectedExampleDemo.value?.id),
  ),
)

const buildAllButtonLabel: ComputedRef<string> = computed((): string => {
  if (isBuildRunning.value) return 'Montage en cours…'
  const count: number = takesWithoutExampleOnDemo.value.length
  if (count === 0) return 'Exemples à jour'
  return count === 1 ? 'Générer l’exemple manquant' : `Générer les ${count} exemples`
})

const buildModalTitle: ComputedRef<string> = computed((): string => {
  if (isBuildingTimingsPreview.value) return `Aperçu de la prise ${timingsTake.value?.take_number ?? ''}`
  const buildingTake: PresenterVideoTake | undefined = takes.value.find(
    (take: PresenterVideoTake): boolean => take.id === buildingTakeId.value,
  )
  return buildingTake ? `Exemple de la prise ${buildingTake.take_number}` : 'Exemple'
})

const deleteTakeMessage: ComputedRef<string> = computed((): string => {
  const take: PresenterVideoTake | null = takePendingDeletion.value
  if (!take) return ''
  const deletedContentLabel: string = take.example_video_url
    ? `la prise ${take.take_number} et sa vidéo d’exemple`
    : `la prise ${take.take_number}`
  return `Supprimer ${deletedContentLabel} ? Les vidéos déjà générées pour vos prospects ne changent pas.`
})

/**
 * Show a fresh take list from the API.
 * @param list - The module's takes and its auto-generation setting.
 */
function applyTakeList(list: PresenterVideoTakeList): void {
  takes.value = list.takes
  autoGenerate.value = list.auto_generate
}

/** Reload the module's takes. */
async function loadTakes(): Promise<void> {
  try {
    applyTakeList(await PresenterVideoService.listTakes(props.module))
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de charger vos prises')
  }
}

/**
 * Put an updated take in place of its previous version.
 * @param updatedTake - The take as the API returned it.
 */
function replaceTake(updatedTake: PresenterVideoTake): void {
  takes.value = takes.value.map(
    (take: PresenterVideoTake): PresenterVideoTake => (take.id === updatedTake.id ? updatedTake : take),
  )
}

/**
 * Show the takes again with the new one, then build the missing examples so the comparison is ready.
 * @param take - The take just stored.
 */
async function handleTakeSaved(take: PresenterVideoTake): Promise<void> {
  isAddingTake.value = false
  await loadTakes()
  timingsTakeId.value = take.id
  if (canBuildExamples.value && takes.value.length > 1) await buildMissingExamples()
}

/**
 * Make a take the one the module's next videos are built with.
 * @param take - The take to use.
 */
async function activateTake(take: PresenterVideoTake): Promise<void> {
  activatingTakeId.value = take.id
  try {
    await PresenterVideoService.activateTake(take.id)
    await loadTakes()
    toast.success(`Prise ${take.take_number} utilisée pour vos prochaines vidéos`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de changer de prise')
  } finally {
    activatingTakeId.value = null
  }
}

/**
 * Have the desktop app render the video a take gives on a demo; nothing is published.
 * @param demoId - The site or receptionist filmed.
 * @param take - The take montaged, with the cut points to use.
 * @returns The rendered mp4, or why it could not be made.
 */
function renderTake(
  demoId: number,
  take: PresenterVideoTake,
): Promise<PreviewVideoResult | AssistantPreviewVideoResult> {
  if (props.module === 'ai-assistant') {
    return AssistantSidecarService.buildPreviewVideo(
      demoId,
      PresenterVideoTimings.receptionistBuildTimings(take),
      take.id,
    )
  }
  return StoryblokSidecarService.buildPreviewVideo(demoId, PresenterVideoTimings.siteBuildTimings(take), take.id)
}

/**
 * Render a take on a demo while the progress modal follows the build.
 * @param demo - The site or receptionist filmed.
 * @param take - The take montaged, with the cut points to use.
 * @param finalStepLabel - The modal's last step, once the video is rendered.
 * @returns The rendered mp4, or null when it could not be made (the user is told why).
 */
async function renderTakeWithProgress(
  demo: PresenterVideoExampleDemo,
  take: PresenterVideoTake,
  finalStepLabel: string,
): Promise<Blob | null> {
  videoProgress.start(demo.slug, finalStepLabel)
  try {
    const result: PreviewVideoResult | AssistantPreviewVideoResult = await renderTake(demo.id, take)
    if (result.status === 'done' && result.video) return result.video
    if (result.status === 'needs_login') {
      videoProgress.close()
      toast.error('Session Storyblok expirée — reconnectez-vous via la carte « Connexion Storyblok ».')
      return null
    }
    if (result.status === 'unavailable') {
      videoProgress.close()
      toast.error("Disponible uniquement dans l'application desktop.")
      return null
    }
    const message: string = result.message ?? 'Échec du montage de la vidéo.'
    videoProgress.fail(message)
    toast.error(message)
    return null
  } catch (error: unknown) {
    const message: string = error instanceof Error ? error.message : 'Échec du montage de la vidéo.'
    videoProgress.fail(message)
    toast.error(message)
    return null
  }
}

/**
 * Keep a rendered video as a take's example and show it on its card.
 * @param takeId - The take the video was montaged with.
 * @param video - The rendered mp4.
 * @param demo - The site or receptionist filmed.
 */
async function keepExample(takeId: number, video: Blob, demo: PresenterVideoExampleDemo): Promise<void> {
  replaceTake(await PresenterVideoService.uploadTakeExample(takeId, video, demo.id, demo.name))
}

/**
 * Build a take's example video on the chosen demo, then keep it on the take.
 * @param take - The take to show.
 * @returns Whether the example is ready.
 */
async function buildExample(take: PresenterVideoTake): Promise<boolean> {
  const demo: PresenterVideoExampleDemo | null = selectedExampleDemo.value
  if (!demo || isBuildRunning.value) return false

  buildingTakeId.value = take.id
  try {
    const video: Blob | null = await renderTakeWithProgress(demo, take, "Enregistrement de l'exemple")
    if (!video) return false
    await keepExample(take.id, video, demo)
    videoProgress.finish()
    videoProgress.close()
    return true
  } catch (error: unknown) {
    const message: string = error instanceof Error ? error.message : "Impossible d'enregistrer l'exemple."
    videoProgress.fail(message)
    toast.error(message)
    return false
  } finally {
    buildingTakeId.value = null
  }
}

/** Build, one after the other, every example missing on the chosen demo; stops at the first failure. */
async function buildMissingExamples(): Promise<void> {
  const pendingTakes: PresenterVideoTake[] = [...takesWithoutExampleOnDemo.value]
  for (const take of pendingTakes) {
    if (!(await buildExample(take))) return
  }
  if (pendingTakes.length > 0) toast.success('Exemples prêts : comparez-les, puis choisissez la prise à utiliser.')
}

/** Drop the preview of unsaved cut points (avoids leaking its blob). */
function releaseTimingsPreview(): void {
  if (timingsPreview.value) URL.revokeObjectURL(timingsPreview.value.url)
  timingsPreview.value = null
}

/**
 * Render a take with cut points not saved yet, to judge them before saving; nothing is published.
 * @param take - The take carrying the cut points of the timeline form.
 */
async function previewTimings(take: PresenterVideoTake): Promise<void> {
  const demo: PresenterVideoExampleDemo | null = selectedExampleDemo.value
  if (!demo || isBuildRunning.value) return

  isBuildingTimingsPreview.value = true
  try {
    const video: Blob | null = await renderTakeWithProgress(demo, take, "Récupération de l'aperçu")
    if (!video) return
    releaseTimingsPreview()
    timingsPreview.value = { take, demo, video, url: URL.createObjectURL(video) }
    videoProgress.finish()
    videoProgress.close()
    toast.success('Aperçu prêt — rien n’a été publié')
  } finally {
    isBuildingTimingsPreview.value = false
  }
}

/**
 * Show a take with its saved cut points; the preview made with exactly these becomes its example.
 * @param savedTake - The take as the API saved it.
 */
async function handleTimingsSaved(savedTake: PresenterVideoTake): Promise<void> {
  replaceTake(savedTake)
  const preview: PresenterVideoTimingsPreview | null = timingsPreview.value
  if (!preview || preview.take.id !== savedTake.id) return
  if (!PresenterVideoTimings.haveSameCutPoints(preview.take, savedTake)) return
  try {
    await keepExample(savedTake.id, preview.video, preview.demo)
    releaseTimingsPreview()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Impossible d'enregistrer l'exemple.")
  }
}

/**
 * Ask before deleting a take.
 * @param take - The take to delete.
 */
function askDeleteTake(take: PresenterVideoTake): void {
  takePendingDeletion.value = take
  deleteModalRef.value?.open()
}

/** Delete the take once confirmed in the modal. */
async function handleDeleteConfirmed(): Promise<void> {
  const take: PresenterVideoTake | null = takePendingDeletion.value
  if (!take) return
  deletingTakeId.value = take.id
  try {
    await PresenterVideoService.deleteTake(take.id)
    if (timingsTakeId.value === take.id) timingsTakeId.value = null
    if (timingsPreview.value?.take.id === take.id) releaseTimingsPreview()
    await loadTakes()
    toast.success(`Prise ${take.take_number} supprimée`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    deletingTakeId.value = null
    takePendingDeletion.value = null
  }
}

/**
 * Save the module's auto-generation right away, back to the previous value if it fails.
 * @param isOn - Whether every new demo gets its video on its own.
 */
async function handleAutoGenerateChange(isOn: boolean): Promise<void> {
  autoGenerate.value = isOn
  try {
    applyTakeList(await PresenterVideoService.setAutoGenerate(isOn, props.module))
  } catch (err: unknown) {
    autoGenerate.value = !isOn
    toast.error(err instanceof Error ? err.message : 'Échec de la mise à jour')
  }
}

/**
 * The user's demo sites that can be filmed: live, with the Storyblok space the editor sequence opens.
 * @returns Them as example demos.
 */
async function loadSiteExampleDemos(): Promise<PresenterVideoExampleDemo[]> {
  const response: DemoSiteListResponse = await DemoSiteService.listDemoSites()
  return response.items
    .filter(
      (site: DemoSite): boolean =>
        site.status === 'active' && Boolean(site.demo_url) && Boolean(site.storyblok_editor_url),
    )
    .map((site: DemoSite): PresenterVideoExampleDemo => ({ id: site.id, slug: site.slug, name: site.business_name }))
}

/**
 * The user's receptionists that can be filmed: the live demos, a sold one is never filmed again.
 * @returns Them as example demos.
 */
async function loadReceptionistExampleDemos(): Promise<PresenterVideoExampleDemo[]> {
  const response: AiAssistantListResponse = await AiAssistantService.list()
  return response.assistants
    .filter((assistant: AiAssistantSummary): boolean => assistant.status === 'active')
    .map(
      (assistant: AiAssistantSummary): PresenterVideoExampleDemo => ({
        id: assistant.id,
        slug: assistant.slug,
        name: assistant.business_name,
      }),
    )
}

/**
 * The demo the most recent example was built on, so a new example is compared on the same one.
 * @returns Its id, or null when no take has an example yet.
 */
function latestExampleDemoId(): number | null {
  let latestTake: PresenterVideoTake | null = null
  for (const take of takes.value) {
    if (!take.example_generated_at) continue
    if (!latestTake || take.example_generated_at > (latestTake.example_generated_at ?? '')) latestTake = take
  }
  return latestTake?.example_subject_id ?? null
}

/** Load the demos usable as examples; keep the one of the latest example, else take one at random. */
async function loadExampleDemos(): Promise<void> {
  try {
    exampleDemos.value =
      props.module === 'ai-assistant' ? await loadReceptionistExampleDemos() : await loadSiteExampleDemos()
  } catch {
    // Pas bloquant : le sélecteur reste vide et la génération des exemples désactivée.
    return
  }
  if (exampleDemos.value.length === 0) return

  const previousDemoId: number | null = latestExampleDemoId()
  const previousDemo: PresenterVideoExampleDemo | undefined = exampleDemos.value.find(
    (demo: PresenterVideoExampleDemo): boolean => demo.id === previousDemoId,
  )
  const randomDemo: PresenterVideoExampleDemo =
    exampleDemos.value[Math.floor(Math.random() * exampleDemos.value.length)]!
  selectedExampleDemoId.value = String((previousDemo ?? randomDemo).id)
}

// Let the host know whether a take is in place (used by the setup wizard).
watch(
  (): boolean => takes.value.length > 0,
  (hasVideo: boolean): void => {
    emit('has-video', hasVideo)
  },
)

onMounted(async (): Promise<void> => {
  await loadTakes()
  isLoading.value = false
  isDesktopApp.value = (await getScraperSidecarInfo()) !== null
  if (isDesktopApp.value) await loadExampleDemos()
})

onBeforeUnmount((): void => {
  releaseTimingsPreview()
})
</script>
