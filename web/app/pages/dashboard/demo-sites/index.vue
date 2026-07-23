<template>
  <div>
    <div class="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-xs font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Prospection</p>
        <h1 class="mt-1 text-2xl font-semibold text-[var(--app-ink)]">Sites démo</h1>
        <p class="mt-2 max-w-xl text-sm text-[var(--app-ink-soft)]">
          Générez des sites vitrines pour vos prospects — hébergés 14 jours sur demo.dibodev.fr
        </p>
      </div>
      <NuxtLink to="/dashboard/demo-sites/create" class="btn-primary inline-flex w-fit items-center gap-2">
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        Créer un site
      </NuxtLink>
    </div>

    <div v-if="pending" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div v-for="i in 3" :key="i" class="card animate-pulse">
        <div class="h-36 bg-[var(--app-surface-2)]"></div>
        <div class="space-y-3 p-5">
          <div class="h-4 w-2/3 rounded bg-[var(--app-surface-2)]"></div>
          <div class="h-3 w-1/2 rounded bg-[var(--app-surface-2)]"></div>
        </div>
      </div>
    </div>

    <div v-else-if="!sites.length" class="card flex flex-col items-center justify-center px-8 py-16 text-center">
      <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--app-surface-2)]/50">
        <UIcon name="i-lucide-globe" class="h-6 w-6 text-[var(--app-ink-soft)]" />
      </div>
      <h2 class="text-lg font-semibold text-[var(--app-ink)]">Aucun site démo</h2>
      <p class="mt-2 max-w-sm text-sm text-[var(--app-ink-soft)]">
        Créez votre premier site vitrine en quelques minutes à partir d'un prospect ou d'une saisie manuelle.
      </p>
      <NuxtLink to="/dashboard/demo-sites/create" class="btn-primary mt-6 inline-flex items-center gap-2">
        <UIcon name="i-lucide-wand-sparkles" class="h-4 w-4" />
        Lancer le builder
      </NuxtLink>
    </div>

    <div v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      <DemoSitesDemoSiteCard
        v-for="site in sites"
        :key="site.id"
        :site="site"
        @copy="copyDemoUrl"
        @open="openDemoUrl"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UseCopyToClipboardReturn, UseOpenExternalUrlReturn } from '~/types/Composables'
import type { Ref } from 'vue'
import type { DemoSite, DemoSiteListResponse } from '~/services/demoSiteService'
import { DemoSiteService } from '~/services/demoSiteService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const sites: Ref<DemoSite[]> = ref([])
const pending: Ref<boolean> = ref(true)

const { copy }: UseCopyToClipboardReturn = useCopyToClipboard()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()

/**
 * Open the demo URL in a new browser tab.
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Copy the demo URL to the clipboard.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

onMounted(async () => {
  try {
    const response: DemoSiteListResponse = await DemoSiteService.listDemoSites()
    sites.value = response.items
  } finally {
    pending.value = false
  }
})
</script>
