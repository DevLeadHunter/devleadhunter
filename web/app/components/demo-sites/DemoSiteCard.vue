<template>
  <article
    class="card group relative overflow-hidden transition-all duration-300 hover:border-[var(--app-ink-soft)] hover:shadow-lg hover:shadow-black/20"
  >
    <!-- Lien étiré : toute la carte navigue ; les actions vivent au-dessus (z-20) — jamais de liens imbriqués. -->
    <NuxtLink
      :to="`/dashboard/demo-sites/${site.id}`"
      class="absolute inset-0 z-10"
      :aria-label="`Voir le détail du site de ${site.business_name}`"
    />

    <div
      ref="previewContainer"
      class="relative h-36 overflow-hidden border-b border-[var(--app-line)] bg-[var(--app-surface-2)] transition-transform duration-500 group-hover:scale-[1.02]"
    >
      <div
        v-if="!isPreviewLoaded"
        :class="[
          'absolute inset-0 flex items-center justify-center',
          previewUrl && shouldRenderPreview ? 'animate-pulse' : '',
        ]"
      >
        <UIcon name="i-lucide-globe" class="h-6 w-6 text-[var(--app-faint)]" />
      </div>
      <iframe
        v-if="previewUrl && shouldRenderPreview"
        :src="previewUrl"
        :class="[
          'pointer-events-none absolute top-0 left-0 h-[400%] w-[400%] origin-top-left scale-[0.25] border-0 bg-white transition-opacity duration-500',
          isPreviewLoaded ? 'opacity-100' : 'opacity-0',
        ]"
        loading="lazy"
        tabindex="-1"
        aria-hidden="true"
        title="Aperçu du site démo"
        sandbox="allow-scripts allow-same-origin"
        @load="onPreviewLoad"
      ></iframe>
      <span
        class="absolute top-3 left-3 inline-flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-0.5 text-[10px] font-bold tracking-wide text-white uppercase backdrop-blur-sm"
      >
        <span :class="['h-1.5 w-1.5 rounded-full', statusDotClass]"></span>
        {{ statusLabel }}
      </span>
    </div>

    <div class="space-y-4 p-5">
      <div class="min-w-0">
        <h2 class="truncate text-lg font-semibold text-[var(--app-ink)]">{{ site.business_name }}</h2>
        <p class="text-xs text-[var(--app-ink-soft)]">{{ templateLabel }}</p>
      </div>

      <div class="flex items-center justify-between text-xs text-[var(--app-ink-soft)]">
        <span v-if="site.is_showcase" class="flex items-center gap-1.5 font-medium text-[var(--app-ink)]">
          <UIcon name="i-lucide-store" class="h-3.5 w-3.5" />
          Vitrine · jamais retirée
        </span>
        <span v-else class="flex items-center gap-1.5">
          <UIcon name="i-lucide-clock" class="h-3.5 w-3.5" />
          <template v-if="DemoSiteService.isKeptAliveByClient(site)">Client dans son espace</template>
          <template v-else-if="DemoSiteService.isTtlPending(site)">En attente d'envoi</template>
          <template v-else>Expire {{ formatNumericDate(site.expires_at) }}</template>
        </span>
        <span v-if="site.city" class="flex items-center gap-1.5">
          <UIcon name="i-lucide-map-pin" class="h-3.5 w-3.5" />
          {{ site.city }}
        </span>
      </div>

      <p
        v-if="site.verification_message && !DemoSiteService.isDemoSiteReachable(site)"
        class="text-xs text-[var(--app-red)]"
      >
        {{ site.verification_message }}
      </p>

      <div class="relative z-20 flex flex-wrap gap-2">
        <button
          v-if="openUrl"
          type="button"
          class="btn-primary h-9 px-4 text-xs"
          @click="openDemoUrl(DemoSiteService.withInternalFlag(openUrl))"
        >
          Ouvrir
        </button>
        <NuxtLink :to="`/dashboard/demo-sites/${site.id}`" class="btn-secondary h-9 px-4 text-xs"> Détails </NuxtLink>
        <button v-if="openUrl" type="button" class="btn-secondary h-9 px-4 text-xs" @click="copyDemoUrl(openUrl)">
          {{ copied ? 'Copié !' : 'Copier' }}
        </button>
      </div>
    </div>
  </article>
</template>

<script lang="ts" setup>
import { formatNumericDate } from '~/utils/date'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { DemoSite } from '~/services/demoSiteService'
import type { DemoSiteCardEmits, DemoSiteCardProps } from '~/types/DemoSiteCard'
import type { UseLazyPreviewReturn } from '~/types/Composables'
import { DemoSiteService } from '~/services/demoSiteService'
import { useLazyPreview } from '~/composables/useLazyPreview'

/** Demo site summary card: live scaled preview, stretched-link navigation, copy and open shortcuts. */
const props: DemoSiteCardProps = defineProps({
  site: {
    type: Object as PropType<DemoSite>,
    required: true,
  },
  templateName: {
    type: String as PropType<string | null>,
    default: null,
  },
})

const emit: EmitFn<DemoSiteCardEmits> = defineEmits<DemoSiteCardEmits>()

const copied: Ref<boolean> = ref(false)
const isPreviewLoaded: Ref<boolean> = ref(false)
/** Preview container observed to mount the iframe only once the card is on screen. */
const previewContainer: Ref<HTMLElement | null> = ref(null)

const openUrl: ComputedRef<string | null> = computed(() => DemoSiteService.getDemoSiteOpenUrl(props.site))

/** URL rendered in the scaled preview — only when the site actually responds. */
const previewUrl: ComputedRef<string | null> = computed(() =>
  DemoSiteService.isDemoSiteReachable(props.site) ? openUrl.value : null,
)

// Aperçu monté à l'entrée dans le viewport, sous un plafond global de chargements
// simultanés : une grille de dizaines de sites ne lance pas autant d'iframes d'un coup.
const { shouldRenderPreview, markPreviewLoaded }: UseLazyPreviewReturn = useLazyPreview(
  previewContainer,
  (): boolean => previewUrl.value !== null,
)

const statusLabel: ComputedRef<string> = computed(() => {
  if (DemoSiteService.isDemoSiteReachable(props.site)) return 'En ligne'
  if (props.site.status === 'unavailable') return 'Hors ligne'
  if (props.site.status === 'failed') return 'Échec'
  return props.site.status
})

const statusDotClass: ComputedRef<string> = computed(() => {
  if (DemoSiteService.isDemoSiteReachable(props.site)) {
    return 'bg-[var(--app-green)]'
  }
  return 'bg-[var(--app-red)]'
})

const templateLabel: ComputedRef<string> = computed(() => props.templateName ?? props.site.template_id)

/**
 * L'iframe a fini de charger : on l'affiche et on libère un créneau de chargement.
 */
function onPreviewLoad(): void {
  isPreviewLoaded.value = true
  markPreviewLoaded()
}

/**
 * Copy the demo URL and show a short confirmation state.
 */
async function copyDemoUrl(url: string): Promise<void> {
  emit('copy', url)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

/**
 * Open the demo URL in a new browser tab.
 */
async function openDemoUrl(url: string | null): Promise<void> {
  if (!url) return
  emit('open', url)
}
</script>
