<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-[#f9f9f9]">Demo websites</h1>
        <p class="text-muted mt-1 text-sm">Sites generated for your prospects (14-day hosting)</p>
      </div>
      <NuxtLink to="/dashboard/demo-sites/create" class="btn-primary">Create demo site</NuxtLink>
    </div>

    <div v-if="pending" class="text-muted text-sm">Loading…</div>
    <div
      v-else-if="!sites.length"
      class="text-muted rounded-lg border border-[#30363d] bg-[#1a1a1a] p-8 text-center text-sm"
    >
      No demo sites yet.
      <NuxtLink to="/dashboard/demo-sites/create" class="ml-1 text-blue-400 underline">Create your first one</NuxtLink>
    </div>
    <div v-else class="space-y-3">
      <article v-for="site in sites" :key="site.id" class="rounded-lg border border-[#30363d] bg-[#1a1a1a] p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="font-medium text-[#f9f9f9]">{{ site.business_name }}</h2>
            <p class="text-muted text-xs">{{ site.template_id }} · {{ statusLabel(site) }}</p>
            <p v-if="site.verification_message && !site.demo_url_live" class="mt-2 text-xs text-amber-300/90">
              {{ site.verification_message }}
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <NuxtLink :to="`/dashboard/demo-sites/${site.id}`" class="btn-secondary px-3 py-1.5 text-xs">
              Edit
            </NuxtLink>
            <button
              type="button"
              class="btn-secondary px-3 py-1.5 text-xs"
              :disabled="regeneratingId === site.id"
              @click="handleRegenerate(site.id)"
            >
              {{ regeneratingId === site.id ? 'Regenerating…' : 'Regenerate' }}
            </button>
            <button
              v-if="site.demo_url"
              type="button"
              class="text-sm text-blue-400 underline"
              @click="openDemoUrl(site.demo_url)"
            >
              Open demo
            </button>
            <button
              v-if="shareUrl(site)"
              type="button"
              class="btn-secondary px-3 py-1.5 text-xs"
              @click="copyDemoUrl(shareUrl(site)!)"
            >
              {{ copiedUrl === shareUrl(site) ? 'Copied!' : 'Copy link' }}
            </button>
            <button
              v-if="site.status !== 'failed'"
              type="button"
              class="btn-secondary px-3 py-1.5 text-xs"
              :disabled="verifyingId === site.id"
              @click="handleVerify(site.id)"
            >
              {{ verifyingId === site.id ? 'Checking…' : 'Check again' }}
            </button>
          </div>
        </div>
        <p class="text-muted mt-2 text-xs">Expires {{ formatDate(site.expires_at) }}</p>
      </article>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import type { DemoSite } from '~/services/demoSiteService'
import { listDemoSites, regenerateDemoSite, verifyDemoSite } from '~/services/demoSiteService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const sites: Ref<DemoSite[]> = ref([])
const pending: Ref<boolean> = ref(true)
const copiedUrl: Ref<string | null> = ref(null)
const verifyingId: Ref<number | null> = ref(null)
const regeneratingId: Ref<number | null> = ref(null)

const { copy } = useCopyToClipboard()
const { openExternalUrl } = useOpenExternalUrl()

/**
 * Open a demo URL in the system browser (desktop) or a new tab (web).
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Human-readable status for a demo site card.
 */
function statusLabel(site: DemoSite): string {
  if (site.status === 'active' && site.demo_url_live) {
    return 'live'
  }
  if (site.status === 'unavailable') {
    return 'not live'
  }
  return site.status
}

/**
 * Return the best URL to share for a demo site.
 */
function shareUrl(site: DemoSite): string | null {
  return site.demo_url ?? null
}

/**
 * Copy a demo site URL to the clipboard.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
  copiedUrl.value = url
  window.setTimeout((): void => {
    copiedUrl.value = null
  }, 2000)
}

/**
 * Re-run verification for a listed demo site.
 */
async function handleVerify(demoSiteId: number): Promise<void> {
  verifyingId.value = demoSiteId
  try {
    const updatedSite: DemoSite = await verifyDemoSite(demoSiteId)
    sites.value = sites.value.map((site: DemoSite): DemoSite => (site.id === demoSiteId ? updatedSite : site))
  } catch (error) {
    console.error(error)
    alert(error instanceof Error ? error.message : 'Verification failed')
  } finally {
    verifyingId.value = null
  }
}

/**
 * Regenerate content for a listed demo site.
 */
async function handleRegenerate(demoSiteId: number): Promise<void> {
  regeneratingId.value = demoSiteId
  try {
    const updatedSite: DemoSite = await regenerateDemoSite(demoSiteId)
    sites.value = sites.value.map((site: DemoSite): DemoSite => (site.id === demoSiteId ? updatedSite : site))
  } catch (error) {
    console.error(error)
    alert(error instanceof Error ? error.message : 'Regeneration failed')
  } finally {
    regeneratingId.value = null
  }
}

/**
 * Format an ISO datetime for display.
 */
function formatDate(value: string): string {
  return new Date(value).toLocaleString('en-GB', { dateStyle: 'medium' })
}

onMounted(async (): Promise<void> => {
  try {
    const response = await listDemoSites()
    sites.value = response.items
  } finally {
    pending.value = false
  }
})
</script>
