<template>
  <div class="space-y-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <NuxtLink to="/dashboard/demo-sites" class="btn-secondary inline-flex w-fit items-center gap-2">
        <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
        Retour aux sites
      </NuxtLink>
      <div class="flex flex-wrap gap-2">
        <NuxtLink
          v-if="site"
          :to="`/dashboard/demo-sites/${site.id}/edit`"
          class="btn-primary inline-flex items-center gap-2"
        >
          <UIcon name="i-lucide-square-pen" class="h-4 w-4" />
          Modifier
        </NuxtLink>
        <button
          v-if="openUrl"
          type="button"
          class="btn-secondary inline-flex items-center gap-2"
          @click="openDemoUrl(openUrl)"
        >
          <UIcon name="i-lucide-external-link" class="h-4 w-4" />
          Ouvrir le site
        </button>
      </div>
    </div>

    <UiLoader v-if="pending" />

    <div v-else-if="loadError" class="card border-red-500/30 bg-red-500/10 p-6 text-red-300">
      {{ loadError }}
    </div>

    <template v-else-if="site">
      <header class="space-y-2">
        <p class="text-xs font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Site démo</p>
        <h1 class="text-[28px] leading-tight font-semibold text-[var(--app-ink)]">{{ site.business_name }}</h1>
        <p class="text-sm text-[var(--app-ink-soft)]">{{ site.slug }} · {{ templateLabel }}</p>
      </header>

      <div class="grid items-start gap-6 xl:grid-cols-[320px_1fr]">
        <aside class="card sticky top-6 space-y-6 p-5">
          <div>
            <h2 class="text-sm font-semibold tracking-wide text-[var(--app-ink)] uppercase">Résumé</h2>
            <dl class="mt-4 space-y-3 text-xs">
              <div class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Statut</dt>
                <dd>
                  <span :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', statusClass]">
                    {{ statusLabel }}
                  </span>
                </dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Template</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ templateLabel }}</dd>
              </div>
              <div v-if="site.city" class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Ville</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ site.city }}</dd>
              </div>
              <div v-if="site.email" class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Email client</dt>
                <dd class="text-right break-all text-[var(--app-ink)]">{{ site.email }}</dd>
              </div>
              <div v-if="site.phone" class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Téléphone</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ site.phone }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Expire dans</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ daysLeft }} jours</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-[var(--app-ink-soft)]">Créé le</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ formatNumericDate(site.created_at) }}</dd>
              </div>
            </dl>
          </div>

          <div v-if="site.description" class="border-t border-[var(--app-line)] pt-4">
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Description</h3>
            <p class="mt-2 text-xs leading-relaxed whitespace-pre-wrap text-[var(--app-ink-soft)]">
              {{ site.description }}
            </p>
          </div>

          <div class="space-y-2 border-t border-[var(--app-line)] pt-4">
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Actions</h3>
            <button v-if="openUrl" type="button" class="btn-secondary w-full text-xs" @click="copyDemoUrl(openUrl)">
              {{ copied ? 'Lien copié !' : 'Copier le lien' }}
            </button>
            <button
              type="button"
              class="btn-secondary w-full text-xs"
              :disabled="regenerating"
              @click="handleRegenerate"
            >
              {{ regenerating ? 'Régénération…' : 'Régénérer le contenu' }}
            </button>
            <button type="button" class="btn-secondary w-full text-xs" :disabled="verifying" @click="handleVerify">
              {{ verifying ? 'Vérification…' : "Revérifier l'URL" }}
            </button>
            <button
              type="button"
              class="btn-secondary inline-flex w-full items-center justify-center gap-2 text-xs"
              :disabled="exporting"
              @click="handleExport"
            >
              <UIcon name="i-lucide-download" class="h-3.5 w-3.5" />
              {{ exporting ? 'Préparation du zip…' : 'Exporter le code' }}
            </button>
            <button
              type="button"
              class="btn-secondary w-full text-xs text-red-300"
              :disabled="deleting"
              @click="handleDelete"
            >
              {{ deleting ? 'Suppression…' : 'Supprimer' }}
            </button>
          </div>

          <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-4">
            <div class="flex items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Vidéo de prospection</h3>
              <span
                v-if="videoStatusLabel"
                :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', videoStatusClass]"
              >
                {{ videoStatusLabel }}
              </span>
            </div>
            <p class="mt-1.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              Votre webcam + le site du prospect qui défile, avec « Bonjour {Prénom} » à l'écran. La vignette est
              utilisable dans les emails via {vignette_video}.
            </p>

            <div v-if="isVideoGenerating" class="mt-3 flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
              <UIcon name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              Génération en cours (capture + montage)…
            </div>

            <p v-else-if="site.video_status === 'failed'" class="mt-3 text-xs text-red-300">
              {{ site.video_error || 'La génération a échoué.' }}
            </p>

            <template v-if="site.video_status === 'ready' && site.video_page_url">
              <button
                type="button"
                class="mt-3 block w-full cursor-pointer overflow-hidden rounded-lg border border-[var(--app-line)] transition-opacity hover:opacity-90"
                title="Ouvrir la page vidéo"
                @click="openVideoPage(site.video_page_url)"
              >
                <img
                  v-if="site.video_thumbnail_url"
                  :src="site.video_thumbnail_url"
                  alt="Vignette de la vidéo de prospection"
                  class="w-full"
                />
              </button>
              <div class="mt-2 space-y-2">
                <button type="button" class="btn-secondary w-full text-xs" @click="copyDemoUrl(site.video_page_url)">
                  {{ copied ? 'Lien copié !' : 'Copier le lien vidéo' }}
                </button>
                <button
                  type="button"
                  class="btn-secondary w-full text-xs"
                  :disabled="generatingVideo"
                  @click="handleGenerateVideo"
                >
                  {{ generatingVideo ? 'Lancement…' : 'Régénérer la vidéo' }}
                </button>
                <button
                  type="button"
                  class="btn-secondary w-full text-xs text-red-300"
                  :disabled="deletingVideo"
                  @click="askDeleteVideo"
                >
                  {{ deletingVideo ? 'Suppression…' : 'Supprimer la vidéo' }}
                </button>
              </div>
            </template>

            <button
              v-if="!isVideoGenerating && site.video_status !== 'ready'"
              type="button"
              class="btn-primary mt-3 w-full text-xs disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="generatingVideo"
              @click="handleGenerateVideo"
            >
              <UIcon name="i-lucide-clapperboard" class="mr-1.5 h-3.5 w-3.5" />
              {{ generatingVideo ? 'Lancement…' : site.video_status === 'failed' ? 'Réessayer' : 'Générer la vidéo' }}
            </button>

            <NuxtLink
              to="/dashboard/settings/video"
              class="mt-2 block w-full text-center text-[11px] text-[var(--app-ink-soft)] underline underline-offset-2 transition-colors hover:text-[var(--app-ink)]"
            >
              Configurer mon clip webcam (Paramètres → Vidéo de prospection)
            </NuxtLink>
          </div>

          <UiConfirmModal
            ref="deleteVideoModalRef"
            title="Supprimer la vidéo"
            message="Supprimer la vidéo de prospection de ce site ? Le lien envoyé dans les emails ne fonctionnera plus."
            confirm-text="Supprimer"
            cancel-text="Annuler"
            @confirm="handleDeleteVideoConfirmed"
          />

          <div
            v-if="site.storyblok_editor_url"
            class="rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-4"
          >
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Storyblok CMS</h3>
            <button
              type="button"
              class="mt-2 text-xs text-blue-400 underline"
              @click="openDemoUrl(site.storyblok_editor_url!)"
            >
              Ouvrir l'éditeur
            </button>
            <p v-if="site.storyblok_invite_sent" class="mt-2 text-xs text-[var(--app-green)]">
              Invitation envoyée à {{ site.storyblok_login_email || site.email }}
            </p>
            <button
              v-else
              type="button"
              class="btn-secondary mt-3 w-full text-xs"
              :disabled="inviting"
              @click="handleInvite"
            >
              {{ inviting ? 'Envoi…' : 'Inviter le client au CMS' }}
            </button>
          </div>
        </aside>

        <section class="space-y-6">
          <div
            v-if="site.verification_message && !DemoSiteService.isDemoSiteReachable(site)"
            class="card border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200"
          >
            {{ site.verification_message }}
          </div>
          <div
            v-if="site.local_demo_url && site.local_demo_url !== site.demo_url"
            class="card border-[var(--app-green)]/30 bg-[var(--app-green)]/10 p-4 text-sm text-[var(--app-green)]"
          >
            URL locale : {{ site.local_demo_url }}
          </div>

          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div v-for="stat in stats" :key="stat.label" class="card p-4">
              <p class="text-xs font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">{{ stat.label }}</p>
              <p
                class="mt-1 text-xl font-semibold text-[var(--app-ink)]"
                :class="[
                  stat.tone === 'success' && 'text-[var(--app-green)]',
                  stat.tone === 'warning' && 'text-amber-300',
                  stat.tone === 'muted' && 'truncate text-base',
                ]"
              >
                {{ stat.value }}
              </p>
            </div>
          </div>

          <div class="card overflow-hidden p-0">
            <div class="border-b border-[var(--app-line)] px-5 py-4">
              <h2 class="font-semibold text-[var(--app-ink)]">Aperçu du site</h2>
              <p class="text-xs text-[var(--app-ink-soft)]">Rendu actuel du site démo publié</p>
            </div>
            <div v-if="previewLoading" class="flex items-center justify-center py-24">
              <div class="loader-smooth"></div>
            </div>
            <DemoSitesDemoSitePreviewFrame
              v-else-if="previewContent"
              :content="previewContent"
              :business-name="site.business_name"
              :template-id="site.template_id"
              :slug="site.slug"
              preview-label="demo.dibodev.fr"
            />
            <div v-else-if="openUrl" class="p-5">
              <iframe
                :src="openUrl"
                class="h-[600px] w-full rounded-lg border border-[var(--app-line)] bg-white"
                title="Aperçu live"
              />
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { formatNumericDate } from '~/utils/date'
import type { UseCopyToClipboardReturn, UseOpenExternalUrlReturn, UseToastReturn } from '~/types/Composables'
import type { DemoSiteStat } from '~/types/DemoSiteDetailPage'
import type { ComputedRef, Ref } from 'vue'
import type { DemoSite, DemoSitePreviewResult } from '~/services/demoSiteService'
import { DemoSiteService } from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route: ReturnType<typeof useRoute> = useRoute()
const demoSiteId: number = Number(route.params.id)
const { copy, copied }: UseCopyToClipboardReturn = useCopyToClipboard()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()
const toast: UseToastReturn = useToast()

const site: Ref<DemoSite | null> = ref(null)
const pending: Ref<boolean> = ref(true)
const loadError: Ref<string | null> = ref(null)
const previewContent: Ref<Record<string, unknown> | null> = ref(null)
const previewLoading: Ref<boolean> = ref(false)
const verifying: Ref<boolean> = ref(false)
const regenerating: Ref<boolean> = ref(false)
const deleting: Ref<boolean> = ref(false)
const inviting: Ref<boolean> = ref(false)
const exporting: Ref<boolean> = ref(false)
const generatingVideo: Ref<boolean> = ref(false)
const deletingVideo: Ref<boolean> = ref(false)
const deleteVideoModalRef: Ref<{ open: () => void } | null> = ref(null)
let videoPollTimer: ReturnType<typeof setInterval> | null = null

const templateLabel: ComputedRef<string> = computed(() => {
  const labels: Record<string, string> = {
    'plumber-cuivre': 'Plombier Source',
    'electrician-lumen': 'Électricien Lumen',
  }
  return labels[site.value?.template_id ?? ''] ?? site.value?.template_id ?? ''
})

const openUrl: ComputedRef<string | null> = computed(() =>
  site.value ? DemoSiteService.getDemoSiteOpenUrl(site.value) : null,
)

const statusLabel: ComputedRef<string> = computed(() => {
  if (!site.value) return ''
  if (DemoSiteService.isDemoSiteReachable(site.value)) return 'En ligne'
  if (site.value.status === 'failed') return 'Échec'
  if (site.value.status === 'unavailable') return 'Hors ligne'
  return site.value.status
})

const statusClass: ComputedRef<string> = computed(() => {
  if (site.value && DemoSiteService.isDemoSiteReachable(site.value))
    return 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
  if (site.value?.status === 'failed') return 'bg-red-500/20 text-red-300'
  return 'bg-amber-500/20 text-amber-300'
})

const daysLeft: ComputedRef<number> = computed(() =>
  site.value ? DemoSiteService.daysUntilExpiry(site.value.expires_at) : 0,
)

const isVideoGenerating: ComputedRef<boolean> = computed(
  () => site.value?.video_status === 'pending' || site.value?.video_status === 'generating',
)

const videoStatusLabel: ComputedRef<string | null> = computed(() => {
  switch (site.value?.video_status) {
    case 'pending':
    case 'generating':
      return 'En cours'
    case 'ready':
      return 'Prête'
    case 'failed':
      return 'Échec'
    default:
      return null
  }
})

const videoStatusClass: ComputedRef<string> = computed(() => {
  if (site.value?.video_status === 'ready') return 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
  if (site.value?.video_status === 'failed') return 'bg-red-500/20 text-red-300'
  return 'bg-amber-500/20 text-amber-300'
})

const stats: ComputedRef<DemoSiteStat[]> = computed(() => {
  if (!site.value) return []
  const urlLive: boolean = DemoSiteService.isDemoSiteReachable(site.value)
  return [
    {
      label: 'Statut URL',
      value: urlLive ? 'Live' : 'Offline',
      tone: urlLive ? 'success' : 'warning',
    },
    {
      label: 'Jours restants',
      value: String(daysLeft.value),
      tone: undefined,
    },
    {
      label: 'CMS',
      value: site.value.storyblok_invite_sent ? 'Invité' : 'Non invité',
      tone: site.value.storyblok_invite_sent ? 'success' : undefined,
    },
    {
      label: 'Slug',
      value: site.value.slug,
      tone: 'muted',
    },
  ]
})

/**
 * Load the Storyblok preview payload for the current site.
 */
async function loadPreview(): Promise<void> {
  if (!site.value) return
  previewLoading.value = true
  try {
    const result: DemoSitePreviewResult = await DemoSiteService.previewDemoSite({
      business_name: site.value.business_name,
      template_id: site.value.template_id,
      email: site.value.email ?? undefined,
      phone: site.value.phone ?? undefined,
      city: site.value.city ?? undefined,
      description: site.value.description ?? undefined,
      theme: site.value.theme ?? undefined,
    })
    previewContent.value = result.content_json
  } catch {
    previewContent.value = null
  } finally {
    previewLoading.value = false
  }
}

/**
 * Open the live demo URL in a new browser tab.
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Copy the live demo URL to the clipboard.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

/**
 * Verify that the deployed demo site is reachable.
 */
async function handleVerify(): Promise<void> {
  verifying.value = true
  try {
    site.value = await DemoSiteService.verifyDemoSite(demoSiteId)
  } finally {
    verifying.value = false
  }
}

/**
 * Regenerate the demo site content and refresh the preview.
 */
async function handleRegenerate(): Promise<void> {
  regenerating.value = true
  try {
    site.value = await DemoSiteService.regenerateDemoSite(demoSiteId)
    await loadPreview()
  } finally {
    regenerating.value = false
  }
}

/**
 * Invite the client to the Storyblok CMS workspace.
 */
async function handleInvite(): Promise<void> {
  inviting.value = true
  try {
    site.value = await DemoSiteService.inviteDemoSiteClientToCms(demoSiteId)
  } catch (error) {
    alert(error instanceof Error ? error.message : "Échec de l'invitation")
  } finally {
    inviting.value = false
  }
}

/**
 * Export the demo site source code as a downloadable archive.
 */
async function handleExport(): Promise<void> {
  if (!site.value) return
  exporting.value = true
  try {
    await DemoSiteService.exportDemoSiteCode(demoSiteId, site.value.slug)
  } catch (error) {
    alert(error instanceof Error ? error.message : "Échec de l'export du code")
  } finally {
    exporting.value = false
  }
}

/**
 * Delete the demo site after user confirmation.
 */
async function handleDelete(): Promise<void> {
  if (!site.value || !confirm(`Supprimer le site "${site.value.business_name}" ?`)) return
  deleting.value = true
  try {
    await DemoSiteService.deleteDemoSite(demoSiteId)
    await navigateTo('/dashboard/demo-sites')
  } finally {
    deleting.value = false
  }
}

/**
 * Stop the video-status polling loop.
 */
function stopVideoPolling(): void {
  if (videoPollTimer !== null) {
    clearInterval(videoPollTimer)
    videoPollTimer = null
  }
}

/**
 * Poll the site every 5 s while the video is generating (background job).
 */
function startVideoPolling(): void {
  if (videoPollTimer !== null) return
  videoPollTimer = setInterval(async (): Promise<void> => {
    try {
      site.value = await DemoSiteService.getDemoSite(demoSiteId)
    } catch {
      // Erreur transitoire : on retentera au prochain tick.
    }
    if (!isVideoGenerating.value) stopVideoPolling()
  }, 5000)
}

/**
 * Start (or restart) the prospection-video generation.
 */
async function handleGenerateVideo(): Promise<void> {
  generatingVideo.value = true
  try {
    site.value = await DemoSiteService.generateDemoSiteVideo(demoSiteId)
    startVideoPolling()
    toast.success('Génération de la vidéo lancée (capture + montage en tâche de fond)')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec du lancement de la génération')
  } finally {
    generatingVideo.value = false
  }
}

/**
 * Open the delete-video confirmation modal.
 */
function askDeleteVideo(): void {
  deleteVideoModalRef.value?.open()
}

/**
 * Delete the generated video once confirmed in the modal.
 */
async function handleDeleteVideoConfirmed(): Promise<void> {
  deletingVideo.value = true
  try {
    site.value = await DemoSiteService.deleteDemoSiteVideo(demoSiteId)
    toast.success('Vidéo supprimée')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la suppression de la vidéo')
  } finally {
    deletingVideo.value = false
  }
}

/**
 * Open the tracked player page with the in-app marker (adds a close button).
 * @param url - Player page URL of the site's prospection video.
 */
async function openVideoPage(url: string): Promise<void> {
  await openExternalUrl(`${url}${url.includes('?') ? '&' : '?'}from=app`)
}

onMounted(async () => {
  try {
    site.value = await DemoSiteService.getDemoSite(demoSiteId)
    await loadPreview()
    if (isVideoGenerating.value) startVideoPolling()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger le site'
  } finally {
    pending.value = false
  }
})

onBeforeUnmount((): void => {
  stopVideoPolling()
})
</script>

<style scoped>
.loader-smooth {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-left-color: var(--app-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
