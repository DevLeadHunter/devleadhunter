<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Stockage</h1>
        <p class="text-muted mt-1 text-sm">
          Fichiers hébergés sur Cloudflare R2 — vidéos de prospection, vignettes d'email, clips webcam et pièces jointes
          du support.
        </p>
      </div>
      <div class="flex shrink-0 flex-wrap gap-2">
        <button type="button" class="btn-secondary h-9 px-3 text-xs" :disabled="isLoading" @click="load">
          <UIcon name="i-lucide-refresh-cw" :class="['mr-1.5 h-3.5 w-3.5', isLoading ? 'animate-spin' : '']" />
          Rafraîchir
        </button>
        <button type="button" class="btn-secondary h-9 px-3 text-xs" :disabled="isPurging" @click="askPurge">
          <UIcon name="i-lucide-trash-2" class="mr-1.5 h-3.5 w-3.5" />
          Purger les expirés
        </button>
      </div>
    </div>

    <div
      v-if="error"
      class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-sm text-[var(--app-red)]"
    >
      {{ error }}
    </div>

    <!-- Totaux -->
    <div v-if="listing" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Bucket</p>
        <p class="mt-1 truncate text-sm font-semibold text-[var(--app-ink)]">{{ listing.bucket }}</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Fichiers</p>
        <p class="mt-1 text-sm font-semibold text-[var(--app-ink)] tabular-nums">{{ listing.total }}</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Espace utilisé</p>
        <p class="mt-1 text-sm font-semibold text-[var(--app-ink)] tabular-nums">
          {{ formatSize(listing.total_size) }}
        </p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Expirés</p>
        <p
          class="mt-1 text-sm font-semibold tabular-nums"
          :style="{ color: expiredCount > 0 ? 'var(--app-red)' : 'var(--app-ink)' }"
        >
          {{ expiredCount }}
        </p>
      </div>
    </div>

    <!-- Cohérence R2 ↔ base -->
    <UiCollapsibleCard icon="i-lucide-stethoscope" title="Cohérence R2 ↔ base" :suffix="healthSuffix">
      <div class="space-y-4 px-4 py-4">
        <p class="text-muted text-xs leading-relaxed">
          Vérifie que le nettoyage à {{ TTL_DAYS }} jours fonctionne : fichiers présents sur R2 sans démo côté base
          (orphelins), démos marquées « prête » dont le fichier a disparu, et fichiers au-delà du TTL.
        </p>
        <div v-if="health" class="grid gap-3 sm:grid-cols-3">
          <div v-for="group in healthGroups" :key="group.label">
            <p class="text-[11px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
              {{ group.label }} ({{ group.keys.length }})
            </p>
            <p v-if="!group.keys.length" class="text-muted mt-1 text-xs">Aucun ✅</p>
            <ul v-else class="mt-1 space-y-1">
              <li v-for="key in group.keys.slice(0, 5)" :key="key" class="truncate text-xs text-[var(--app-ink)]">
                {{ key }}
              </li>
              <li v-if="group.keys.length > 5" class="text-muted text-xs">+ {{ group.keys.length - 5 }} autre(s)</li>
            </ul>
          </div>
        </div>
      </div>
    </UiCollapsibleCard>

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

    <!-- Liste -->
    <div v-else-if="listing && listing.items.length" class="space-y-2">
      <div
        v-for="item in listing.items"
        :key="item.key"
        class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="app-badge">{{ kindLabel(item.kind) }}</span>
              <span v-if="item.prospect_name" class="text-sm font-medium text-[var(--app-ink)]">
                {{ item.prospect_name }}
              </span>
              <span
                v-if="item.is_expired"
                class="app-badge app-badge--danger font-medium"
                title="Au-delà du TTL, devrait être purgé"
              >
                Expiré
              </span>
              <span v-else-if="item.expires_in_days !== null" class="text-muted text-xs">
                expire dans {{ item.expires_in_days }} j
              </span>
            </div>
            <p class="text-muted mt-1 truncate text-xs">{{ item.key }}</p>
            <p class="text-muted mt-0.5 text-xs">{{ formatSize(item.size) }} · {{ formatDate(item.last_modified) }}</p>
          </div>

          <div class="flex shrink-0 items-center gap-2">
            <button
              v-if="item.kind === 'website_video' || item.kind === 'presenter'"
              type="button"
              class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
              title="Visionner"
              @click="preview(item)"
            >
              <UIcon name="i-lucide-play" class="h-3.5 w-3.5" />
            </button>
            <a
              :href="item.url"
              target="_blank"
              rel="noopener"
              class="btn-secondary flex h-8 min-h-8 items-center px-2.5 text-xs"
              title="Ouvrir dans un onglet"
            >
              <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
            </a>
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

        <!-- Lecteur inline -->
        <video
          v-if="previewKey === item.key"
          :src="item.url"
          controls
          autoplay
          playsinline
          class="mt-3 aspect-video w-full max-w-2xl rounded-lg border border-[var(--app-line)] bg-black"
        />
      </div>
    </div>

    <div v-else-if="listing" class="rounded-xl border border-dashed border-[var(--app-line)] px-6 py-12 text-center">
      <p class="text-muted text-sm">Aucun fichier dans ce filtre.</p>
    </div>

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

const toast = useToast()

const listing: Ref<StorageListResponse | null> = ref<StorageListResponse | null>(null)
const health: Ref<StorageHealthResponse | null> = ref<StorageHealthResponse | null>(null)
const isLoading: Ref<boolean> = ref<boolean>(true)
const isPurging: Ref<boolean> = ref<boolean>(false)
const error: Ref<string> = ref<string>('')
const activePrefix: Ref<string> = ref<string>('')
const previewKey: Ref<string | null> = ref<string | null>(null)
const pendingKey: Ref<string | null> = ref<string | null>(null)
const confirmTitle: Ref<string> = ref<string>('')
const confirmMessage: Ref<string> = ref<string>('')
const confirmModal: Ref<{ open: () => void } | null> = ref<{ open: () => void } | null>(null)

/** Number of objects past their TTL in the current listing. */
const expiredCount: ComputedRef<number> = computed(
  (): number => listing.value?.items.filter((item: StorageObject): boolean => item.is_expired).length ?? 0,
)

/** Consistency groups rendered in the health card. */
const healthGroups: ComputedRef<Array<{ label: string; keys: string[] }>> = computed(
  (): Array<{ label: string; keys: string[] }> => [
    { label: 'Orphelins', keys: health.value?.orphan_objects ?? [] },
    { label: 'Fichiers manquants', keys: health.value?.missing_objects ?? [] },
    { label: 'Au-delà du TTL', keys: health.value?.expired_objects ?? [] },
  ],
)

/** Short summary shown next to the health card title. */
const healthSuffix: ComputedRef<string> = computed((): string => {
  if (!health.value) return ''
  const total =
    health.value.orphan_objects.length + health.value.missing_objects.length + health.value.expired_objects.length
  return total === 0 ? 'tout est cohérent' : `${total} à vérifier`
})

/**
 * Human label for an object category.
 * @param kind - Raw category from the API.
 * @returns Localised label.
 */
function kindLabel(kind: string): string {
  const labels: Record<string, string> = {
    website_video: 'Vidéo',
    website_thumbnail: 'Vignette',
    presenter: 'Clip webcam',
    support: 'Support',
    other: 'Autre',
  }
  return labels[kind] ?? kind
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
  return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
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
  previewKey.value = null
  await load()
}

/**
 * Toggle the inline player for an object.
 * @param item - Object to preview.
 */
function preview(item: StorageObject): void {
  previewKey.value = previewKey.value === item.key ? null : item.key
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
  confirmMessage.value = `Supprimer « ${item.key} » ? Cette action est irréversible.`
  confirmModal.value?.open()
}

/**
 * Ask confirmation before purging every expired object.
 */
function askPurge(): void {
  pendingKey.value = null
  confirmTitle.value = 'Purger les fichiers expirés'
  confirmMessage.value = `Supprimer toutes les vidéos et vignettes de plus de ${TTL_DAYS} jours ?`
  confirmModal.value?.open()
}

/**
 * Run the confirmed action (single delete or purge), then reload.
 * @returns A promise resolving once the action completed.
 */
async function runConfirmed(): Promise<void> {
  isPurging.value = true
  try {
    const result = pendingKey.value ? await deleteStorageObject(pendingKey.value) : await purgeExpiredStorage()
    toast.success(result.message || 'Action effectuée')
    previewKey.value = null
    await load()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la suppression')
  } finally {
    isPurging.value = false
    pendingKey.value = null
  }
}

onMounted(async (): Promise<void> => {
  await load()
})
</script>
