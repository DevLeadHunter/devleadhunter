<template>
  <div v-if="isLoading" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Chargement…
  </div>
  <div
    v-else-if="hasFailed || !site?.legal"
    class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300"
  >
    Site introuvable.
  </div>
  <SiteLegalPage
    v-else
    :legal-notice="site.legal"
    page="legal"
    :business-name="site.business_name"
    :logo-url="logoUrl"
    :page-paths="pagePaths"
  />
</template>

<script lang="ts" setup>
import type { SiteLegalPageData } from '~/types/SiteLegalPage'

const { site, isLoading, hasFailed, logoUrl, pagePaths }: SiteLegalPageData = await useSiteLegalPageData()
</script>
