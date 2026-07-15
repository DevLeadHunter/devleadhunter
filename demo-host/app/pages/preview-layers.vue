<template>
  <div v-if="!site" class="preview-loading">Template inconnu : {{ templateId }}</div>
  <DemoSiteView v-else :site="site" />
</template>

<script lang="ts" setup>
/**
 * Harnais de validation local — vérifie le rendu d'une template (Nuxt layer via extends)
 * en rejouant le VRAI chemin de prod : DemoSiteView dispatche `template_id` vers le
 * composant racine du layer, alimenté par un `SiteContent` plat identique à celui produit
 * par l'API (`build_site_content`). Les SiteContents vivent dans
 * app/utils/previewLayers.json (régénérables : un mock prospect + enrichment par métier
 * passés dans la logique API). Outil de DEV uniquement — les vraies démos passent par
 * [slug].vue (fetch API par slug). Ne pas servir en démo réelle.
 *
 * Usage : /preview-layers?t=<template_id>   (défaut : plumber-signature)
 */
import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import previewLayers from '~/utils/previewLayers.json'

/** Les 5 SiteContents plats, générés par l'API (bundlés → dispo SSR + client). */
const CONTENTS: Record<string, Record<string, unknown>> = previewLayers as Record<string, Record<string, unknown>>

const route = useRoute()

/** template_id ciblé via ?t= (défaut : plumber-signature). */
const templateId: ComputedRef<string> = computed(
  (): string => (typeof route.query.t === 'string' ? route.query.t : 'plumber-signature'),
)

/** Optional business-name override (?business=) so the builder preview shows the client's name. */
const businessOverride: ComputedRef<string> = computed(
  (): string => (typeof route.query.business === 'string' ? route.query.business.trim() : ''),
)

/** Faux DemoSitePublic (status draft → aucun tracking) pour nourrir DemoSiteView. */
const site: ComputedRef<DemoSitePublic | null> = computed((): DemoSitePublic | null => {
  const base: Record<string, unknown> | undefined = CONTENTS[templateId.value]
  if (!base) {
    return null
  }
  const name: string = businessOverride.value || String(base.businessName ?? 'Preview')
  const content: Record<string, unknown> = businessOverride.value ? { ...base, businessName: name } : base
  return {
    slug: `preview-${templateId.value}`,
    business_name: name,
    template_id: templateId.value,
    content_json: content,
    status: 'draft',
    storyblok_preview_token: null,
    storyblok_region: null,
  }
})
</script>

<style scoped>
.preview-loading {
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  color: #64748b;
}
</style>
