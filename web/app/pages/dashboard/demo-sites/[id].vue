<template>
  <div class="space-y-8">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-center @2xl:justify-between">
      <NuxtLink to="/dashboard/demo-sites" class="btn-secondary inline-flex w-fit items-center gap-2">
        <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
        Retour aux sites
      </NuxtLink>
      <div class="flex flex-wrap items-center gap-2">
        <template v-if="hasPendingChanges">
          <button
            type="button"
            class="btn-secondary inline-flex items-center gap-2"
            :disabled="saving"
            @click="resetPendingChanges"
          >
            Annuler
          </button>
          <button
            type="button"
            class="btn-primary inline-flex items-center gap-2"
            :disabled="saving"
            @click="savePendingChanges"
          >
            <UIcon name="i-lucide-save" class="h-4 w-4" />
            {{ saving ? 'Sauvegarde…' : 'Sauvegarder' }}
          </button>
        </template>
        <NuxtLink
          v-if="site"
          :to="`/dashboard/demo-sites/${site.id}/edit`"
          class="btn-secondary inline-flex items-center gap-2"
        >
          <UIcon name="i-lucide-square-pen" class="h-4 w-4" />
          Modifier
        </NuxtLink>
        <button
          v-if="openUrl"
          type="button"
          class="btn-secondary inline-flex items-center gap-2"
          @click="openDemoUrl(DemoSiteService.withInternalFlag(openUrl))"
        >
          <UIcon name="i-lucide-external-link" class="h-4 w-4" />
          Ouvrir le site
        </button>
      </div>
    </div>

    <UiLoader v-if="pending" />

    <div
      v-else-if="loadError"
      class="card border-[var(--app-red)]/30 bg-[var(--app-red-soft)] p-6 text-[var(--app-red)]"
    >
      {{ loadError }}
    </div>

    <template v-else-if="site">
      <header class="space-y-2">
        <p class="text-xs font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Site démo</p>
        <h1 class="app-page-title">{{ site.business_name }}</h1>
        <p class="text-sm text-[var(--app-ink-soft)]">{{ site.slug }} · {{ templateLabel }}</p>
      </header>

      <div class="grid items-start gap-6 @4xl:grid-cols-[360px_1fr]">
        <aside ref="asideRef" class="card sticky top-6 max-h-[calc(100vh-3rem)] space-y-5 overflow-y-auto p-5">
          <UiTabs v-model="activeTab" :tabs="asideTabs" />

          <template v-if="activeTab === 'resume'">
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
                  <dd class="text-right text-[var(--app-ink)]">
                    <template v-if="site && DemoSiteService.isTtlPending(site)">En attente d'envoi</template>
                    <template v-else>{{ daysLeft }} jours</template>
                  </dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-[var(--app-ink-soft)]">Créé le</dt>
                  <dd class="text-right text-[var(--app-ink)]">{{ formatNumericDate(site.created_at) }}</dd>
                </div>
              </dl>
            </div>

            <div v-if="openUrl" class="border-t border-[var(--app-line)] pt-4">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Lien de la démo</h3>
              <div class="mt-2 flex items-center gap-2">
                <input :value="openUrl" readonly class="input-field h-9 flex-1 truncate text-xs" />
                <button
                  type="button"
                  class="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded border border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
                  :title="copied ? 'Lien copié !' : 'Copier le lien'"
                  @click="copyDemoUrl(openUrl)"
                >
                  <UIcon :name="copied ? 'i-lucide-check' : 'i-lucide-copy'" class="h-4 w-4" />
                </button>
              </div>
            </div>

            <div v-if="site.description" class="border-t border-[var(--app-line)] pt-4">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Description</h3>
              <p class="mt-2 text-xs leading-relaxed whitespace-pre-wrap text-[var(--app-ink-soft)]">
                {{ site.description }}
              </p>
            </div>

            <div class="space-y-2 border-t border-[var(--app-line)] pt-4">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Actions</h3>
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
                class="btn-secondary w-full text-xs text-[var(--app-red)]"
                :disabled="deleting"
                @click="deleteSiteModalRef?.open()"
              >
                {{ deleting ? 'Suppression…' : 'Supprimer' }}
              </button>

              <UiConfirmModal
                ref="deleteSiteModalRef"
                title="Supprimer le site"
                :message="`Supprimer le site « ${site?.business_name} » ? La démo et son espace CMS seront retirés. Cette action est irréversible.`"
                confirm-text="Supprimer"
                cancel-text="Annuler"
                @confirm="handleDelete"
              />
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

              <p v-else-if="site.video_status === 'failed'" class="mt-3 text-xs text-[var(--app-red)]">
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
                  <button type="button" class="btn-secondary w-full text-xs" @click="copyVideoUrl(site.video_page_url)">
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
                    class="btn-secondary w-full text-xs text-[var(--app-red)]"
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

              <p v-if="videoPrepStatus" class="text-muted mt-3 text-center text-[11px] leading-relaxed">
                {{ videoPrepStatus }}
              </p>

              <NuxtLink
                to="/dashboard/settings/video"
                class="mt-2 block w-full text-center text-[11px] text-[var(--app-ink-soft)] underline underline-offset-2 transition-colors hover:text-[var(--app-ink)]"
              >
                Configurer mon clip webcam (Paramètres
                <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Vidéo de prospection)
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
              <div class="flex items-center justify-between gap-3">
                <h3 class="text-sm font-semibold text-[var(--app-ink)]">Storyblok CMS</h3>
                <span
                  v-if="cmsStatusLabel"
                  :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', cmsStatusClass]"
                >
                  {{ cmsStatusLabel }}
                </span>
              </div>
              <button
                type="button"
                class="mt-2 text-xs text-blue-400 underline"
                @click="openDemoUrl(site.storyblok_editor_url!)"
              >
                Ouvrir l'éditeur
              </button>

              <p v-if="cmsStatus === 'joined'" class="mt-2 text-xs text-[var(--app-green)]">
                Le client a rejoint le CMS{{ cmsJoinedAtLabel ? ` le ${cmsJoinedAtLabel}` : '' }} ({{
                  site.storyblok_login_email || site.email
                }}).
              </p>

              <template v-else-if="cmsStatus === 'pending'">
                <p class="mt-2 text-xs text-[var(--app-ink-soft)]">
                  Invitation envoyée à {{ site.storyblok_login_email || site.email }} — en attente qu'il rejoigne
                  l'espace.
                </p>
                <button
                  type="button"
                  class="btn-secondary mt-3 w-full text-xs disabled:opacity-50"
                  :disabled="refreshingCms"
                  @click="handleRefreshCmsStatus"
                >
                  {{ refreshingCms ? 'Vérification…' : 'Vérifier s’il a rejoint' }}
                </button>
              </template>

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
          </template>

          <template v-else>
            <DemoSitesColorEditor
              :template="selectedTemplate"
              :theme="selectedTheme"
              :use-brand-color="selectedUseBrandColor"
              :brand-color="site.brand_color ?? null"
              @update:theme="selectedTheme = $event"
              @update:use-brand-color="selectedUseBrandColor = $event"
            />

            <div v-if="siteImages && siteImages.pool.length" class="border-t border-[var(--app-line)] pt-4">
              <DemoSitesImageSlots :pool="siteImages.pool" :order="imagesOrder" @update:order="onImageOrderChange" />
            </div>
            <p
              v-else
              class="rounded-xl border border-dashed border-[var(--app-line)] p-4 text-xs text-[var(--app-ink-soft)]"
            >
              Aucune photo exploitable pour ce prospect : le site garde les images par défaut du template.
            </p>
          </template>
        </aside>

        <section class="space-y-6">
          <div
            v-if="site.verification_message && !DemoSiteService.isDemoSiteReachable(site)"
            class="card border-[var(--app-red)]/30 bg-[var(--app-red-soft)] p-4 text-sm text-[var(--app-red)]"
          >
            {{ site.verification_message }}
          </div>
          <div
            v-if="site.local_demo_url && site.local_demo_url !== site.demo_url"
            class="card border-[var(--app-green)]/30 bg-[var(--app-green)]/10 p-4 text-sm text-[var(--app-green)]"
          >
            URL locale : {{ site.local_demo_url }}
          </div>

          <div class="grid grid-cols-2 gap-4 @4xl:grid-cols-4">
            <div v-for="stat in stats" :key="stat.label" class="card p-4">
              <p class="text-xs font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">{{ stat.label }}</p>
              <p
                class="mt-1 text-xl font-semibold text-[var(--app-ink)]"
                :class="[
                  stat.tone === 'success' && 'text-[var(--app-green)]',
                  stat.tone === 'danger' && 'text-[var(--app-red)]',
                  stat.tone === 'muted' && 'truncate text-base',
                ]"
              >
                {{ stat.value }}
              </p>
            </div>
          </div>

          <div class="card overflow-hidden p-0">
            <div class="border-b border-[var(--app-line)] px-5 py-4">
              <h2 class="font-semibold text-[var(--app-ink)]">Aperçu &amp; template</h2>
              <p class="text-xs text-[var(--app-ink-soft)]">
                Votre vrai site, mis à jour en direct : couleurs, images et template s'y reflètent instantanément —
                sauvegardez pour publier.
              </p>
            </div>
            <div class="space-y-4 p-5">
              <div v-if="loadingTemplates" class="flex items-center justify-center py-24">
                <div class="loader-smooth"></div>
              </div>
              <DemoSitesTemplatePicker
                v-else-if="templates.length"
                v-model="selectedTemplateId"
                :templates="templates"
                :theme="selectedTheme"
                :use-brand-color="selectedUseBrandColor"
                :brand-color="site?.brand_color ?? null"
                :published-site-url="openUrl"
                :reload-nonce="previewReloadNonce"
                :show-colors="false"
                :preview-photos="previewPhotos"
                :preview-theme="previewTheme"
                templates-below-preview
                @update:theme="selectedTheme = $event"
                @update:use-brand-color="selectedUseBrandColor = $event"
              />
              <div v-else-if="openUrl">
                <iframe
                  :src="openUrl"
                  class="h-[600px] w-full rounded-lg border border-[var(--app-line)] bg-white"
                  title="Aperçu live"
                />
              </div>
            </div>
          </div>
        </section>
      </div>
    </template>

    <UiVideoGenerationModal
      :open="videoProgress.isOpen.value"
      title="Génération de la vidéo"
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
import { formatNumericDate } from '~/utils/date'
import type { UseCopyToClipboardReturn, UseOpenExternalUrlReturn, UseToastReturn } from '~/types/Composables'
import type { DemoSiteStat } from '~/types/DemoSiteDetailPage'
import type { UiTab } from '~/types/UiTabs'
import type { TemplateThemeColorKey } from '~/types/TemplatePicker'
import type { ComputedRef, Ref } from 'vue'
import type {
  DemoSite,
  DemoSiteImages,
  DemoSiteTemplate,
  DemoSiteTheme,
  DemoSiteUpdatePayload,
  StoryblokCollaboratorStatus,
} from '~/services/demoSiteService'
import { DEFAULT_DEMO_SITE_THEME, DemoSiteService } from '~/services/demoSiteService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { useToast } from '~/composables/useToast'
import type { UseVideoGenerationProgressReturn } from '~/composables/useVideoGenerationProgress'
import { useVideoGenerationProgress } from '~/composables/useVideoGenerationProgress'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route: ReturnType<typeof useRoute> = useRoute()
const demoSiteId: number = Number(route.params.id)
const { copy, copied }: UseCopyToClipboardReturn = useCopyToClipboard()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()
const toast: UseToastReturn = useToast()
const videoProgress: UseVideoGenerationProgressReturn = useVideoGenerationProgress()

/** Tabs of the sticky side panel: the site's summary/actions, and its visual configuration. */
const asideTabs: UiTab[] = [
  { key: 'resume', label: 'Résumé', icon: 'i-lucide-clipboard-list' },
  { key: 'config', label: 'Configuration', icon: 'i-lucide-sliders-horizontal' },
]

const site: Ref<DemoSite | null> = ref(null)
const pending: Ref<boolean> = ref(true)
const loadError: Ref<string | null> = ref(null)
const templates: Ref<DemoSiteTemplate[]> = ref([])
const loadingTemplates: Ref<boolean> = ref(true)
const activeTab: Ref<string> = ref('resume')
const selectedTemplateId: Ref<string> = ref('')
const selectedTheme: Ref<DemoSiteTheme> = ref({ ...DEFAULT_DEMO_SITE_THEME })
/** Action colour source: logo (true) / template (false) — #13. */
const selectedUseBrandColor: Ref<boolean> = ref(true)
/** Candidate photo placement (hero/about/gallery), edited live and saved with the other changes. */
const imagesOrder: Ref<string[]> = ref([])
const siteImages: Ref<DemoSiteImages | null> = ref(null)
const saving: Ref<boolean> = ref(false)
/** Bumped after a save to force the live preview iframe to reload the published content. */
const previewReloadNonce: Ref<number> = ref(0)
const deleting: Ref<boolean> = ref(false)
const inviting: Ref<boolean> = ref(false)
const refreshingCms: Ref<boolean> = ref(false)
const exporting: Ref<boolean> = ref(false)
const generatingVideo: Ref<boolean> = ref(false)
const videoPrepStatus: Ref<string> = ref('')
const deletingVideo: Ref<boolean> = ref(false)
const deleteVideoModalRef: Ref<{ open: () => void } | null> = ref(null)
const deleteSiteModalRef: Ref<{ open: () => void } | null> = ref(null)
const asideRef: Ref<HTMLElement | null> = ref(null)
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
  return 'bg-[var(--app-red)]/20 text-[var(--app-red)]'
})

const daysLeft: ComputedRef<number> = computed(() =>
  site.value ? DemoSiteService.daysUntilExpiry(site.value.expires_at) : 0,
)

/** The template currently selected in the picker (drives the colour editor's roles). */
const selectedTemplate: ComputedRef<DemoSiteTemplate | null> = computed(
  (): DemoSiteTemplate | null =>
    templates.value.find((template: DemoSiteTemplate): boolean => template.id === selectedTemplateId.value) ?? null,
)

/** Whether the picked template differs from the published one. */
const templateChanged: ComputedRef<boolean> = computed(
  (): boolean => Boolean(site.value) && selectedTemplateId.value !== site.value?.template_id,
)

/** Whether the edited colours differ from the published theme. */
const themeChanged: ComputedRef<boolean> = computed((): boolean => {
  if (!site.value) return false
  const publishedTheme: DemoSiteTheme = site.value.theme ?? DEFAULT_DEMO_SITE_THEME
  return (['primary', 'secondary', 'accent'] as const).some(
    (key: keyof DemoSiteTheme): boolean => publishedTheme[key] !== selectedTheme.value[key],
  )
})

/** Whether the Logo ⟷ Template action-colour source differs from the published choice. */
const brandSourceChanged: ComputedRef<boolean> = computed(
  (): boolean => Boolean(site.value) && selectedUseBrandColor.value !== (site.value?.use_brand_color ?? true),
)

/** Whether the edited photo placement differs from the published one. */
const imagesChanged: ComputedRef<boolean> = computed((): boolean => {
  if (!siteImages.value) return false
  return imagesOrder.value.join('\n') !== siteImages.value.order.join('\n')
})

/** Any pending edit → the Annuler / Sauvegarder pair shows up top right. */
const hasPendingChanges: ComputedRef<boolean> = computed(
  (): boolean => templateChanged.value || themeChanged.value || brandSourceChanged.value || imagesChanged.value,
)

/** Candidate placement pushed live into the preview — only when it differs from the published one. */
const previewPhotos: ComputedRef<string[] | null> = computed((): string[] | null =>
  imagesChanged.value ? imagesOrder.value : null,
)

/** Candidate colours pushed live into the preview — only when a colour or template edit is pending. */
const previewTheme: ComputedRef<DemoSiteTheme | null> = computed((): DemoSiteTheme | null =>
  templateChanged.value || themeChanged.value || brandSourceChanged.value ? selectedTheme.value : null,
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
  if (site.value?.video_status === 'failed') return 'bg-[var(--app-red)]/20 text-[var(--app-red)]'
  return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
})

/** CMS handover state, derived from the persisted status with a sensible fallback. */
const cmsStatus: ComputedRef<StoryblokCollaboratorStatus> = computed((): StoryblokCollaboratorStatus => {
  const current: DemoSite | null = site.value
  if (!current) return 'not_invited'
  if (current.storyblok_collaborator_status) return current.storyblok_collaborator_status
  return current.storyblok_invite_sent ? 'pending' : 'not_invited'
})

/** Badge label for the CMS handover (null hides the badge — nothing sent yet). */
const cmsStatusLabel: ComputedRef<string | null> = computed((): string | null => {
  switch (cmsStatus.value) {
    case 'joined':
      return 'Rejoint'
    case 'pending':
      return 'En attente'
    default:
      return null
  }
})

/** Colour of the CMS handover badge (green once joined, accent while pending). */
const cmsStatusClass: ComputedRef<string> = computed((): string =>
  cmsStatus.value === 'joined'
    ? 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
    : 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]',
)

/** Human date the client joined the CMS, when known. */
const cmsJoinedAtLabel: ComputedRef<string | null> = computed((): string | null =>
  site.value?.storyblok_joined_at ? formatNumericDate(site.value.storyblok_joined_at) : null,
)

const stats: ComputedRef<DemoSiteStat[]> = computed(() => {
  if (!site.value) return []
  const urlLive: boolean = DemoSiteService.isDemoSiteReachable(site.value)
  return [
    {
      label: 'Statut URL',
      value: urlLive ? 'Live' : 'Offline',
      tone: urlLive ? 'success' : 'danger',
    },
    {
      label: 'Jours restants',
      value: site.value && DemoSiteService.isTtlPending(site.value) ? 'En attente' : String(daysLeft.value),
      tone: undefined,
    },
    {
      label: 'CMS',
      value: cmsStatus.value === 'joined' ? 'Rejoint' : cmsStatus.value === 'pending' ? 'Invité' : 'Non invité',
      tone: cmsStatus.value === 'joined' ? 'success' : undefined,
    },
    {
      label: 'Slug',
      value: site.value.slug,
      tone: 'muted',
    },
  ]
})

/**
 * Apply a new photo placement while keeping the scrollable panel steady — removing or moving a
 * row otherwise reflows the aside and makes the next click land on the wrong photo.
 * @param next - The reordered list of placed photo URLs.
 */
function onImageOrderChange(next: string[]): void {
  const scrollTop: number = asideRef.value?.scrollTop ?? 0
  imagesOrder.value = next
  nextTick((): void => {
    if (asideRef.value) asideRef.value.scrollTop = scrollTop
  })
}

/**
 * Drop every pending edit: back to the published template, colours and photo placement.
 */
function resetPendingChanges(): void {
  if (!site.value) return
  selectedTemplateId.value = site.value.template_id
  selectedTheme.value = { ...(site.value.theme ?? DEFAULT_DEMO_SITE_THEME) }
  selectedUseBrandColor.value = site.value.use_brand_color ?? true
  imagesOrder.value = [...(siteImages.value?.order ?? [])]
}

/**
 * Save every pending edit (template, colours, photo placement) in ONE call — the API regenerates
 * the published site once — then reload the preview on the fresh content.
 * @returns A promise resolved once the site has been regenerated.
 */
async function savePendingChanges(): Promise<void> {
  if (!site.value || !hasPendingChanges.value) return
  saving.value = true
  try {
    const payload: DemoSiteUpdatePayload = {}
    if (templateChanged.value || themeChanged.value || brandSourceChanged.value) {
      payload.template_id = selectedTemplateId.value
      payload.theme = { ...selectedTheme.value }
      payload.use_brand_color = selectedUseBrandColor.value
    }
    if (imagesChanged.value) {
      payload.image_order = [...imagesOrder.value]
    }
    site.value = await DemoSiteService.updateDemoSite(demoSiteId, payload)
    await loadImages()
    resetPendingChanges()
    previewReloadNonce.value += 1
    toast.success('Changements sauvegardés, site mis à jour')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la sauvegarde')
  } finally {
    saving.value = false
  }
}

/**
 * Load the photo pool and current placement for the image editor.
 * Silent on failure: the editor block simply stays hidden.
 */
async function loadImages(): Promise<void> {
  try {
    siteImages.value = await DemoSiteService.getDemoSiteImages(demoSiteId)
  } catch {
    siteImages.value = null
  }
}

/**
 * Open the live demo URL in a new browser tab.
 */
async function openDemoUrl(url: string | null): Promise<void> {
  if (!url) return
  await openExternalUrl(url)
}

/**
 * Copy the live demo URL to the clipboard.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

/**
 * Invite the client to the Storyblok CMS workspace.
 */
async function handleInvite(): Promise<void> {
  inviting.value = true
  try {
    site.value = await DemoSiteService.inviteDemoSiteClientToCms(demoSiteId)
    toast.success('Invitation au CMS envoyée au client')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Échec de l'invitation")
  } finally {
    inviting.value = false
  }
}

/**
 * Re-read whether the client has joined the CMS (manual « Vérifier » click).
 */
async function handleRefreshCmsStatus(): Promise<void> {
  refreshingCms.value = true
  try {
    site.value = await DemoSiteService.refreshDemoSiteCmsStatus(demoSiteId)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la vérification du statut CMS')
  } finally {
    refreshingCms.value = false
  }
}

/**
 * Silently re-read the CMS handover status on load, so a client who joined shows up without a click.
 */
async function refreshCmsStatusSilently(): Promise<void> {
  try {
    site.value = await DemoSiteService.refreshDemoSiteCmsStatus(demoSiteId)
  } catch {
    // Best-effort : en cas d'échec on garde le statut déjà affiché.
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
    toast.error(error instanceof Error ? error.message : "Échec de l'export du code")
  } finally {
    exporting.value = false
  }
}

/**
 * Delete the demo site after user confirmation.
 */
async function handleDelete(): Promise<void> {
  if (!site.value) return
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
 * Run the desktop Storyblok background capture once, surfacing errors as a toast.
 * @returns What the sidecar did (`uploaded` / `needs_login` / `skipped` / `unavailable`).
 */
async function runStoryblokBackgroundPrep(): Promise<
  Awaited<ReturnType<typeof StoryblokSidecarService.prepareVideoBackground>>
> {
  videoPrepStatus.value = 'Enregistrement du site + de la séquence Storyblok (~1-2 min, une fenêtre peut s’ouvrir)…'
  try {
    return await StoryblokSidecarService.prepareVideoBackground(demoSiteId)
  } catch (backgroundError) {
    toast.error(
      backgroundError instanceof Error
        ? `Séquence Storyblok ignorée : ${backgroundError.message}`
        : 'Séquence Storyblok ignorée.',
    )
    return 'skipped'
  } finally {
    videoPrepStatus.value = ''
  }
}

/**
 * Open the Storyblok sign-in window and wait until the session is connected.
 *
 * The window stays open until the user signs in or closes it themselves; this
 * resolves true once connected, false if the user closes it or the wait elapses.
 * @returns Whether Storyblok is connected afterwards.
 */
async function waitForStoryblokConnection(): Promise<boolean> {
  videoPrepStatus.value = 'Connecte-toi dans la fenêtre Storyblok qui vient de s’ouvrir…'
  const opened: boolean = await StoryblokSidecarService.openLogin()
  if (!opened) return false
  // The window stays open until the user acts; give them up to 10 min to sign in.
  const deadline: number = Date.now() + 10 * 60 * 1000
  try {
    while (Date.now() < deadline) {
      await new Promise<void>((resolve: () => void): void => {
        window.setTimeout(resolve, 3000)
      })
      const info: Awaited<ReturnType<typeof StoryblokSidecarService.getSessionState>> =
        await StoryblokSidecarService.getSessionState()
      if (info.state === 'ready') return true
      if (!info.loginWindowOpen) return false // user closed the window without signing in
    }
    return false
  } finally {
    videoPrepStatus.value = ''
  }
}

/**
 * Try to build the ENTIRE video on the desktop (capture + montage), setting the status text.
 * @returns The build result (`done` / `needs_login` / `unavailable` / `failed`).
 */
async function runDesktopFullBuild(): Promise<Awaited<ReturnType<typeof StoryblokSidecarService.buildFullVideo>>> {
  videoPrepStatus.value = 'Génération de la vidéo sur votre ordinateur (~2-3 min, une fenêtre peut s’ouvrir)…'
  try {
    return await StoryblokSidecarService.buildFullVideo(demoSiteId)
  } finally {
    videoPrepStatus.value = ''
  }
}

/**
 * Start (or restart) the prospection-video generation.
 */
async function handleGenerateVideo(): Promise<void> {
  generatingVideo.value = true
  const slug: string = site.value?.slug ?? ''
  try {
    // Desktop: build the ENTIRE video locally (capture + montage) with the bundled
    // ffmpeg — the VPS is never involved. The modal follows the sidecar's phases so
    // the wait is never opaque. If the Storyblok session expired, open the sign-in
    // window, wait, then retry automatically. Any local failure (or the web build,
    // which has no sidecar) falls back to the server-side generation.
    videoProgress.start(slug, 'Publication de la vidéo')
    let build: Awaited<ReturnType<typeof StoryblokSidecarService.buildFullVideo>> = await runDesktopFullBuild()

    if (build.status === 'needs_login') {
      videoProgress.close()
      const connected: boolean = await waitForStoryblokConnection()
      if (!connected) {
        toast.error('Storyblok non reconnecté — génération annulée. Reconnecte-toi puis relance.')
        return
      }
      toast.success('Storyblok reconnecté — reprise de la génération…')
      videoProgress.start(slug, 'Publication de la vidéo')
      build = await runDesktopFullBuild()
    }

    if (build.status === 'done') {
      videoProgress.finish()
      site.value = await DemoSiteService.getDemoSite(demoSiteId)
      videoProgress.close()
      toast.success('Vidéo générée sur votre ordinateur ✓')
      return
    }
    if (build.status === 'unavailable') {
      videoProgress.close()
    } else if (build.status === 'failed') {
      // Keep the modal open with the error + logs, and narrate the server fallback in it.
      videoProgress.fail(build.message ?? 'Échec de la génération locale.')
      videoProgress.note('Bascule sur le serveur…')
    }

    // 'unavailable' (web) or 'failed' → server-side generation (memory-guarded). Best-effort
    // desktop background first so the server montage stays light; else the VPS captures too.
    const prepared: Awaited<ReturnType<typeof StoryblokSidecarService.prepareVideoBackground>> =
      await runStoryblokBackgroundPrep()
    if (prepared === 'uploaded') {
      toast.success('Séquence Storyblok prête, montage en cours…')
    }
    site.value = await DemoSiteService.generateDemoSiteVideo(demoSiteId)
    startVideoPolling()
    videoProgress.note('Montage lancé sur le serveur — suivi sur la carte « Vidéo de prospection ».')
    toast.success('Génération de la vidéo lancée (montage en tâche de fond)')
  } catch (error) {
    const message: string = error instanceof Error ? error.message : 'Échec du lancement de la génération'
    videoProgress.fail(message)
    toast.error(message)
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
 * Open the tracked player page as the owner (close button + no tracking/notification).
 * @param url - Player page URL of the site's prospection video.
 */
async function openVideoPage(url: string): Promise<void> {
  await openExternalUrl(`${url}${url.includes('?') ? '&' : '?'}from=app&internal=1`)
}

/**
 * Copy the player page URL as an owner-preview link (excluded from tracking).
 * @param url - Player page URL of the site's prospection video.
 */
async function copyVideoUrl(url: string): Promise<void> {
  await copy(`${url}${url.includes('?') ? '&' : '?'}internal=1`)
}

watch(selectedTemplateId, (templateId: string, previous: string): void => {
  if (!site.value || !previous) return
  // Back to the published template → restore the published colours; another template → its
  // defaults, with the logo colour re-applied on its action key (what the server does on save).
  if (templateId === site.value.template_id) {
    selectedTheme.value = { ...(site.value.theme ?? DEFAULT_DEMO_SITE_THEME) }
    return
  }
  const picked: DemoSiteTemplate | null = selectedTemplate.value
  if (!picked) return
  const theme: DemoSiteTheme = { ...picked.default_theme }
  const actionKey: TemplateThemeColorKey | undefined = picked.color_roles?.action ?? picked.brand_color_key
  if (selectedUseBrandColor.value && site.value.brand_color && actionKey) {
    theme[actionKey] = site.value.brand_color
  }
  selectedTheme.value = theme
})

onMounted(async () => {
  try {
    site.value = await DemoSiteService.getDemoSite(demoSiteId)
    resetPendingChanges()
    if (isVideoGenerating.value) startVideoPolling()
    if (site.value.storyblok_invite_sent && site.value.storyblok_collaborator_status !== 'joined') {
      refreshCmsStatusSilently()
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger le site'
  } finally {
    pending.value = false
  }
  try {
    templates.value = await DemoSiteService.listDemoSiteTemplates()
  } catch {
    // Sans le catalogue, la fiche reste lisible : seul le bloc de sélection disparaît.
  } finally {
    loadingTemplates.value = false
  }
  await loadImages()
  // Second sync now that the photo pool is known (imagesOrder starts on the published placement).
  resetPendingChanges()
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
