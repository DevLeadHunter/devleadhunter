<template>
  <article
    class="card group relative overflow-hidden transition-all duration-300 hover:border-[var(--app-ink-soft)] hover:shadow-lg hover:shadow-black/20"
  >
    <NuxtLink :to="`/dashboard/demo-sites/${site.id}`" class="block">
      <!-- Preview header -->
      <div
        class="relative h-36 overflow-hidden border-b border-[var(--app-line)] transition-transform duration-500 group-hover:scale-[1.02]"
        :style="{ background: cardGradient }"
      >
        <div class="absolute inset-0 bg-gradient-to-t from-[var(--app-surface)] via-transparent to-transparent"></div>
        <div class="relative px-5 pt-5">
          <span
            :class="[
              'inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase',
              statusClass,
            ]"
          >
            {{ statusLabel }}
          </span>
          <h2 class="mt-3 truncate text-lg font-semibold text-white">{{ site.business_name }}</h2>
          <p class="text-xs text-white/60">{{ templateLabel }}</p>
        </div>
      </div>

      <div class="space-y-4 p-5">
        <div class="flex items-center justify-between text-xs text-[var(--app-ink-soft)]">
          <span class="flex items-center gap-1.5">
            <i class="fa-solid fa-clock"></i>
            Expire {{ formatDate(site.expires_at) }}
          </span>
          <span v-if="site.city" class="flex items-center gap-1.5">
            <i class="fa-solid fa-location-dot"></i>
            {{ site.city }}
          </span>
        </div>

        <p v-if="site.verification_message && !isDemoSiteReachable(site)" class="text-xs text-amber-300/90">
          {{ site.verification_message }}
        </p>

        <div class="flex flex-wrap gap-2" @click.prevent.stop>
          <button v-if="openUrl" type="button" class="btn-primary h-9 px-4 text-xs" @click="openDemoUrl(openUrl)">
            Ouvrir
          </button>
          <NuxtLink :to="`/dashboard/demo-sites/${site.id}`" class="btn-secondary h-9 px-4 text-xs"> Détails </NuxtLink>
          <button v-if="openUrl" type="button" class="btn-secondary h-9 px-4 text-xs" @click="copyDemoUrl(openUrl)">
            {{ copied ? 'Copié !' : 'Copier' }}
          </button>
        </div>
      </div>
    </NuxtLink>
  </article>
</template>

<script lang="ts" setup>
import type { DemoSite } from '~/services/demoSiteService'
import { getDemoSiteOpenUrl, isDemoSiteReachable } from '~/services/demoSiteService'

const props = defineProps<{
  site: DemoSite
}>()

const emit = defineEmits<{
  copy: [url: string]
  open: [url: string]
}>()

const copied = ref(false)

const openUrl = computed(() => getDemoSiteOpenUrl(props.site))

const cardGradient = computed(() => {
  if (isDemoSiteReachable(props.site)) {
    return 'linear-gradient(135deg, #0f172a 0%, #0284c7 100%)'
  }
  return 'linear-gradient(135deg, #1a1a1a 0%, #30363d 100%)'
})

const statusLabel = computed(() => {
  if (isDemoSiteReachable(props.site)) return 'En ligne'
  if (props.site.status === 'unavailable') return 'Hors ligne'
  if (props.site.status === 'failed') return 'Échec'
  return props.site.status
})

const statusClass = computed(() => {
  if (isDemoSiteReachable(props.site)) {
    return 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
  }
  if (props.site.status === 'failed') return 'bg-red-500/20 text-red-300'
  return 'bg-amber-500/20 text-amber-300'
})

const templateLabel = computed(() => {
  const labels: Record<string, string> = {
    'plumber-cuivre': 'Plombier Source',
    'electrician-lumen': 'Électricien Lumen',
  }
  return labels[props.site.template_id] ?? props.site.template_id
})

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('fr-FR', { dateStyle: 'medium' })
}

async function copyDemoUrl(url: string): Promise<void> {
  emit('copy', url)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

async function openDemoUrl(url: string): Promise<void> {
  emit('open', url)
}
</script>
