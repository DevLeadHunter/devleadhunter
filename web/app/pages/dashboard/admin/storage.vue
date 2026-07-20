<template>
  <div class="mx-auto max-w-3xl space-y-8">
    <!-- Header — le contexte tient dans le sous-titre, pas dans des cartes -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 class="text-3xl font-bold text-[var(--app-ink)]">Stockage</h1>
        <p class="text-muted mt-2 text-sm leading-relaxed">
          <template v-if="listing">
            {{ listing.total }} fichier{{ listing.total > 1 ? 's' : '' }} · {{ formatSize(listing.total_size) }} ·
            <span class="text-[var(--app-ink)]">{{ listing.bucket }}</span>
          </template>
          <template v-else>Fichiers hébergés sur Cloudflare R2.</template>
        </p>
      </div>
      <button
        type="button"
        class="btn-secondary h-9 min-h-9 shrink-0 px-2.5"
        title="Actualiser"
        :disabled="isLoading"
        @click="load"
      >
        <UIcon name="i-lucide-rotate-cw" :class="['h-4 w-4', isLoading ? 'animate-spin' : '']" />
      </button>
    </div>

    <p v-if="error" class="text-sm text-[var(--app-red)]">{{ error }}</p>

    <!-- Purge : proposée seulement quand il y a vraiment quelque chose à purger -->
    <div
      v-if="expiredCount > 0"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
    >
      <div class="flex min-w-0 items-start gap-3">
        <UIcon name="i-lucide-circle-alert" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-red)]" />
        <div class="min-w-0">
          <p class="text-sm font-semibold text-[var(--app-ink)]">
            {{ expiredCount }} fichier{{ expiredCount > 1 ? 's' : '' }} au-delà de {{ TTL_DAYS }} jours
          </p>
          <p class="text-muted text-xs leading-relaxed">Le nettoyage automatique aurait dû les supprimer.</p>
        </div>
      </div>
      <button type="button" class="btn-danger shrink-0 text-xs" :disabled="isActing" @click="askPurge">Purger</button>
    </div>

    <!-- Filtres -->
    <div class="flex flex-wrap gap-2">
      <button
        v-for="filter in FILTERS"
        :key="filter.prefix"
        type="button"
        :class="[
          'rounded-full border px-3 py-1 text-xs transition-colors',
          activePrefix === filter.prefix
            ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-surface)]'
            : 'border-[var(--app-line)] text-[var(--app-ink)] hover:bg-[var(--app-surface-2)]',
        ]"
        @click="applyFilter(filter.prefix)"
      >
        {{ filter.label }}
      </button>
    </div>

    <UiLoader v-if="isLoading" />

    <!-- Liste : la ligne s'ouvre au clic, seules 2 actions restent visibles -->
    <div v-else-if="listing && listing.items.length" class="space-y-2">
      <div
        v-for="item in listing.items"
        :key="item.key"
        class="overflow-hidden rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)]"
      >
        <div class="flex items-center gap-3 px-4 py-3">
          <button
            type="button"
            class="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-left"
            :aria-expanded="openKey === item.key"
            @click="togglePreview(item)"
          >
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
              <UIcon :name="kindIcon(item.kind)" class="h-4 w-4 text-[var(--app-ink-soft)]" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-medium text-[var(--app-ink)]">{{ displayName(item) }}</span>
              <span class="text-muted block truncate text-xs">
                {{ kindLabel(item.kind) }} · {{ formatSize(item.size) }} · {{ formatDate(item.last_modified) }}
                <template v-if="item.is_expired"> · <span class="text-[var(--app-red)]">expiré</span></template>
                <template v-else-if="item.expires_in_days !== null">
                  · expire dans {{ item.expires_in_days }} j
                </template>
              </span>
            </span>
          </button>

          <div class="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
              title="Copier le lien"
              @click="copyLink(item.url)"
            >
              <UIcon name="i-lucide-link" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              class="btn-danger flex h-8 min-h-8 items-center justify-center px-2.5 text-xs"
              title="Supprimer"
              @click="askDelete(item)"
            >
              <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <!-- Aperçu déplié : c'est ici que vivent la clé technique et le lien -->
        <div
          class="grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none"
          :class="openKey === item.key ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
        >
          <div class="overflow-hidden">
            <div class="space-y-3 border-t border-[var(--app-line)] px-4 py-4">
              <video
                v-if="openKey === item.key && isVideo(item)"
                :src="item.url"
                controls
                playsinline
                preload="metadata"
                class="aspect-video w-full max-w-lg rounded-lg border border-[var(--app-line)] bg-black"
              />
              <img
                v-else-if="openKey === item.key && isImage(item)"
                :src="item.url"
                :alt="displayName(item)"
                class="max-h-64 rounded-lg border border-[var(--app-line)]"
              />
              <p class="text-muted font-mono text-xs break-all">{{ item.key }}</p>
              <a
                :href="item.url"
                target="_blank"
                rel="noopener"
                class="text-muted inline-flex items-center gap-1.5 text-xs font-medium hover:text-[var(--app-ink)]"
              >
                <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                Ouvrir dans un onglet
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Vide -->
    <div
      v-else-if="listing"
      class="flex flex-col items-center gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-14 text-center"
    >
      <span class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--app-surface-2)]">
        <UIcon name="i-lucide-hard-drive" class="h-5 w-5 text-[var(--app-ink-soft)]" />
      </span>
      <p class="text-sm font-medium text-[var(--app-ink)]">Aucun fichier</p>
      <p class="text-muted max-w-xs text-sm leading-relaxed">
        {{ activePrefix ? 'Rien dans ce filtre.' : 'Le bucket est vide — les vidéos générées apparaîtront ici.' }}
      </p>
    </div>

    <!-- Cohérence : repliée, avec un verdict lisible dès le titre -->
    <UiCollapsibleCard icon="i-lucide-stethoscope" title="Cohérence avec la base" :suffix="healthSuffix">
      <div class="space-y-4 px-4 py-4">
        <p v-if="!hasHealthIssues" class="text-muted text-xs leading-relaxed">
          Chaque vidéo marquée « prête » a bien son fichier, et rien ne traîne au-delà de {{ TTL_DAYS }} jours.
        </p>
        <div v-for="group in healthGroups" v-else :key="group.label">
          <template v-if="group.keys.length">
            <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
              {{ group.label }} ({{ group.keys.length }})
            </p>
            <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ group.hint }}</p>
            <ul class="mt-1.5 space-y-1">
              <li v-for="key in group.keys.slice(0, 5)" :key="key" class="truncate font-mono text-xs">{{ key }}</li>
              <li v-if="group.keys.length > 5" class="text-muted text-xs">+ {{ group.keys.length - 5 }} autre(s)</li>
            </ul>
          </template>
        </div>
      </div>
    </UiCollapsibleCard>

    <UiConfirmModal
      ref="confirmModal"
      :title="confirmTitle"
      :message="confirmMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="runConfirmed"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { StorageHealthResponse, StorageListResponse, StorageObject } from '~/services/adminStorageService'
import { computed, onMounted, ref } from 'vue'
import {
  deleteStorageObject,
  getStorageHealth,
  getStorageObjects,
  purgeExpiredStorage,
} from '~/services/adminStorageService'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: ['auth'] })

/** Demo deliverables TTL, mirrored from the API. */
const TTL_DAYS: number = 14

/** Prefix filters shown as pills. */
const FILTERS: Array<{ label: string; prefix: string }> = [
  { label: 'Tout', prefix: '' },
  { label: 'Vidéos', prefix: 'videos/websites/' },
  { label: 'Vignettes', prefix: 'images/websites/' },
  { label: 'Clips webcam', prefix: 'videos/presenter/' },
  { label: 'Support', prefix: 'images/support/' },
]

/** Icon per object category. */
const KIND_ICONS: Record<string, string> = {
  website_video: 'i-lucide-video',
  website_thumbnail: 'i-lucide-image',
  presenter: 'i-lucide-webcam',
  support: 'i-lucide-paperclip',
  other: 'i-lucide-file',
}

/** Human label per object category — distinguishes a prospect's video from its thumbnail. */
const KIND_LABELS: Record<string, string> = {
  website_video: 'Vidéo',
  website_thumbnail: 'Vignette',
  presenter: 'Clip webcam',
  support: 'Pièce jointe',
  other: 'Fichier',
}

const toast = useToast()

const listing: Ref<StorageListResponse | null> = ref<StorageListResponse | null>(null)
const health: Ref<StorageHealthResponse | null> = ref<StorageHealthResponse | null>(null)
const isLoading: Ref<boolean> = ref<boolean>(true)
const isActing: Ref<boolean> = ref<boolean>(false)
const error: Ref<string> = ref<string>('')
const activePrefix: Ref<string> = ref<string>('')
const openKey: Ref<string | null> = ref<string | null>(null)
const pendingKey: Ref<string | null> = ref<string | null>(null)
const confirmTitle: Ref<string> = ref<string>('')
const confirmMessage: Ref<string> = ref<string>('')
const confirmModal: Ref<{ open: () => void } | null> = ref<{ open: () => void } | null>(null)

/** Number of objects past their TTL in the current listing. */
const expiredCount: ComputedRef<number> = computed(
  (): number => listing.value?.items.filter((item: StorageObject): boolean => item.is_expired).length ?? 0,
)

/** Consistency groups, each with a plain-French explanation. */
const healthGroups: ComputedRef<Array<{ label: string; hint: string; keys: string[] }>> = computed(
  (): Array<{ label: string; hint: string; keys: string[] }> => [
    {
      label: 'Orphelins',
      hint: 'Présents sur R2 mais plus rattachés à une démo.',
      keys: health.value?.orphan_objects ?? [],
    },
    {
      label: 'Fichiers manquants',
      hint: 'Démos marquées « prête » dont la vidéo a disparu.',
      keys: health.value?.missing_objects ?? [],
    },
    {
      label: `Au-delà de ${TTL_DAYS} jours`,
      hint: 'Auraient dû être purgés automatiquement.',
      keys: health.value?.expired_objects ?? [],
    },
  ],
)

/** Whether the consistency report found anything. */
const hasHealthIssues: ComputedRef<boolean> = computed((): boolean =>
  healthGroups.value.some((group: { keys: string[] }): boolean => group.keys.length > 0),
)

/** Short verdict shown next to the health card title. */
const healthSuffix: ComputedRef<string> = computed((): string => {
  if (!health.value) return ''
  const total = healthGroups.value.reduce(
    (sum: number, group: { keys: string[] }): number => sum + group.keys.length,
    0,
  )
  return total === 0 ? 'tout est cohérent' : `${total} à vérifier`
})

/**
 * Icon matching an object category.
 * @param kind - Raw category from the API.
 * @returns Lucide icon name.
 */
function kindIcon(kind: string): string {
  return KIND_ICONS[kind] ?? KIND_ICONS.other!
}

/**
 * Human label matching an object category.
 * @param kind - Raw category from the API.
 * @returns Localised label.
 */
function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? KIND_LABELS.other!
}

/**
 * Readable name for an object: the prospect when known, else the file name.
 * @param item - Storage object.
 * @returns Label shown as the row title.
 */
function displayName(item: StorageObject): string {
  if (item.prospect_name) return item.prospect_name
  if (item.slug) return item.slug
  return item.key.split('/').pop() || item.key
}

/**
 * Whether an object can be played inline.
 * @param item - Storage object.
 * @returns True for videos.
 */
function isVideo(item: StorageObject): boolean {
  return item.kind === 'website_video' || item.kind === 'presenter'
}

/**
 * Whether an object can be shown as an image.
 * @param item - Storage object.
 * @returns True for thumbnails and support attachments.
 */
function isImage(item: StorageObject): boolean {
  return item.kind === 'website_thumbnail' || item.kind === 'support'
}

/**
 * Format a byte count in a readable unit.
 * @param bytes - Raw size.
 * @returns Formatted label (e.g. « 12,4 Mo »).
 */
function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} Go`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${bytes} o`
}

/**
 * Format an ISO date for display.
 * @param value - ISO timestamp or null.
 * @returns Localised date, or a dash.
 */
function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Load the listing and the consistency report.
 * @returns A promise resolving once both are loaded.
 */
async function load(): Promise<void> {
  isLoading.value = true
  error.value = ''
  try {
    listing.value = await getStorageObjects(activePrefix.value)
    health.value = await getStorageHealth().catch((): StorageHealthResponse | null => null)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Impossible de charger le stockage'
  } finally {
    isLoading.value = false
  }
}

/**
 * Apply a prefix filter and reload.
 * @param prefix - Key prefix to filter on.
 * @returns A promise resolving once reloaded.
 */
async function applyFilter(prefix: string): Promise<void> {
  activePrefix.value = prefix
  openKey.value = null
  await load()
}

/**
 * Toggle the inline preview of an object.
 * @param item - Object to preview.
 */
function togglePreview(item: StorageObject): void {
  openKey.value = openKey.value === item.key ? null : item.key
}

/**
 * Copy a public URL to the clipboard.
 * @param url - URL to copy.
 * @returns A promise resolving once copied.
 */
async function copyLink(url: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(url)
    toast.success('Lien copié')
  } catch {
    toast.error('Impossible de copier le lien')
  }
}

/**
 * Ask confirmation before deleting one object.
 * @param item - Object to delete.
 */
function askDelete(item: StorageObject): void {
  pendingKey.value = item.key
  confirmTitle.value = 'Supprimer le fichier'
  confirmMessage.value = `Supprimer « ${displayName(item)} » ? Cette action est irréversible.`
  confirmModal.value?.open()
}

/**
 * Ask confirmation before purging every expired object.
 */
function askPurge(): void {
  pendingKey.value = null
  confirmTitle.value = 'Purger les fichiers expirés'
  confirmMessage.value = `Supprimer les ${expiredCount.value} fichier(s) de plus de ${TTL_DAYS} jours ?`
  confirmModal.value?.open()
}

/**
 * Run the confirmed action (single delete or purge), then reload.
 * @returns A promise resolving once the action completed.
 */
async function runConfirmed(): Promise<void> {
  isActing.value = true
  try {
    const result = pendingKey.value ? await deleteStorageObject(pendingKey.value) : await purgeExpiredStorage()
    toast.success(result.message || 'Action effectuée')
    openKey.value = null
    await load()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    isActing.value = false
    pendingKey.value = null
  }
}

onMounted(async (): Promise<void> => {
  await load()
})
</script>
