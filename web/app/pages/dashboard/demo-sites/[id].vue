<template>
  <div class="space-y-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <NuxtLink to="/dashboard/demo-sites" class="btn-secondary inline-flex w-fit items-center gap-2">
        <i class="fa-solid fa-arrow-left"></i>
        Retour aux sites
      </NuxtLink>
      <div class="flex flex-wrap gap-2">
        <NuxtLink
          v-if="site"
          :to="`/dashboard/demo-sites/${site.id}/edit`"
          class="btn-primary inline-flex items-center gap-2"
        >
          <i class="fa-solid fa-pen"></i>
          Modifier
        </NuxtLink>
        <button
          v-if="openUrl"
          type="button"
          class="btn-secondary inline-flex items-center gap-2"
          @click="openDemoUrl(openUrl)"
        >
          <i class="fa-solid fa-arrow-up-right-from-square"></i>
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
        <p class="text-xs font-semibold tracking-wider text-[#8b949e] uppercase">Site démo</p>
        <h1 class="text-[28px] leading-tight font-semibold text-[#f9f9f9]">{{ site.business_name }}</h1>
        <p class="text-sm text-[#8b949e]">{{ site.slug }} · {{ templateLabel }}</p>
      </header>

      <div class="grid items-start gap-6 xl:grid-cols-[320px_1fr]">
        <!-- Aside -->
        <aside class="card sticky top-6 space-y-6 bg-[#101216] p-5">
          <div>
            <h2 class="text-sm font-semibold tracking-wide text-[#f9f9f9] uppercase">Résumé</h2>
            <dl class="mt-4 space-y-3 text-xs">
              <div class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Statut</dt>
                <dd>
                  <span :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', statusClass]">
                    {{ statusLabel }}
                  </span>
                </dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Template</dt>
                <dd class="text-right text-[#f9f9f9]">{{ templateLabel }}</dd>
              </div>
              <div v-if="site.city" class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Ville</dt>
                <dd class="text-right text-[#f9f9f9]">{{ site.city }}</dd>
              </div>
              <div v-if="site.email" class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Email client</dt>
                <dd class="text-right break-all text-[#f9f9f9]">{{ site.email }}</dd>
              </div>
              <div v-if="site.phone" class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Téléphone</dt>
                <dd class="text-right text-[#f9f9f9]">{{ site.phone }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Expire dans</dt>
                <dd class="text-right text-[#f9f9f9]">{{ daysLeft }} jours</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-[#8b949e]">Créé le</dt>
                <dd class="text-right text-[#f9f9f9]">{{ formatDate(site.created_at) }}</dd>
              </div>
            </dl>
          </div>

          <div v-if="site.description" class="border-t border-[#30363d] pt-4">
            <h3 class="text-sm font-semibold text-[#f9f9f9]">Description</h3>
            <p class="mt-2 text-xs leading-relaxed whitespace-pre-wrap text-[#8b949e]">{{ site.description }}</p>
          </div>

          <div class="space-y-2 border-t border-[#30363d] pt-4">
            <h3 class="text-sm font-semibold text-[#f9f9f9]">Actions</h3>
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
              class="btn-secondary w-full text-xs text-red-300"
              :disabled="deleting"
              @click="handleDelete"
            >
              {{ deleting ? 'Suppression…' : 'Supprimer' }}
            </button>
          </div>

          <div v-if="site.storyblok_editor_url" class="rounded-xl border border-[#30363d] bg-[#0d1117] p-4">
            <h3 class="text-sm font-semibold text-[#f9f9f9]">Storyblok CMS</h3>
            <button
              type="button"
              class="mt-2 text-xs text-blue-400 underline"
              @click="openDemoUrl(site.storyblok_editor_url!)"
            >
              Ouvrir l'éditeur
            </button>
            <p v-if="site.storyblok_invite_sent" class="mt-2 text-xs text-[#2BAD5F]">
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

        <!-- Main -->
        <section class="space-y-6">
          <div
            v-if="site.verification_message && !isDemoSiteReachable(site)"
            class="card border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200"
          >
            {{ site.verification_message }}
          </div>
          <div
            v-if="site.local_demo_url && site.local_demo_url !== site.demo_url"
            class="card border-[#2BAD5F]/30 bg-[#2BAD5F]/10 p-4 text-sm text-[#2BAD5F]"
          >
            URL locale : {{ site.local_demo_url }}
          </div>

          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div v-for="stat in stats" :key="stat.label" class="card p-4">
              <p class="text-xs font-medium tracking-wide text-[#8b949e] uppercase">{{ stat.label }}</p>
              <p
                class="mt-1 text-xl font-semibold text-[#f9f9f9]"
                :class="[
                  stat.tone === 'success' && 'text-[#2BAD5F]',
                  stat.tone === 'warning' && 'text-amber-300',
                  stat.tone === 'muted' && 'truncate text-base',
                ]"
              >
                {{ stat.value }}
              </p>
            </div>
          </div>

          <div class="card overflow-hidden p-0">
            <div class="border-b border-[#30363d] px-5 py-4">
              <h2 class="font-semibold text-[#f9f9f9]">Aperçu du site</h2>
              <p class="text-xs text-[#8b949e]">Rendu actuel du site démo publié</p>
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
                class="h-[600px] w-full rounded-lg border border-[#30363d] bg-white"
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
import type { DemoSite } from '~/services/demoSiteService'
import {
  daysUntilExpiry,
  deleteDemoSite,
  getDemoSite,
  getDemoSiteOpenUrl,
  inviteDemoSiteClientToCms,
  isDemoSiteReachable,
  previewDemoSite,
  regenerateDemoSite,
  verifyDemoSite,
} from '~/services/demoSiteService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route = useRoute()
const demoSiteId = Number(route.params.id)
const { copy, copied } = useCopyToClipboard()
const { openExternalUrl } = useOpenExternalUrl()

const site = ref<DemoSite | null>(null)
const pending = ref(true)
const loadError = ref<string | null>(null)
const previewContent = ref<Record<string, unknown> | null>(null)
const previewLoading = ref(false)
const verifying = ref(false)
const regenerating = ref(false)
const deleting = ref(false)
const inviting = ref(false)

const templateLabel = computed(() => {
  const labels: Record<string, string> = {
    'plumber-cuivre': 'Plombier Source',
    'electrician-lumen': 'Électricien Lumen',
  }
  return labels[site.value?.template_id ?? ''] ?? site.value?.template_id ?? ''
})

const openUrl = computed(() => (site.value ? getDemoSiteOpenUrl(site.value) : null))

const statusLabel = computed(() => {
  if (!site.value) return ''
  if (isDemoSiteReachable(site.value)) return 'En ligne'
  if (site.value.status === 'failed') return 'Échec'
  if (site.value.status === 'unavailable') return 'Hors ligne'
  return site.value.status
})

const statusClass = computed(() => {
  if (site.value && isDemoSiteReachable(site.value)) return 'bg-[#2BAD5F]/20 text-[#2BAD5F]'
  if (site.value?.status === 'failed') return 'bg-red-500/20 text-red-300'
  return 'bg-amber-500/20 text-amber-300'
})

const daysLeft = computed(() => (site.value ? daysUntilExpiry(site.value.expires_at) : 0))

const stats = computed(() => {
  if (!site.value) return []
  const urlLive = isDemoSiteReachable(site.value)
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

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('fr-FR', { dateStyle: 'medium' })
}

async function loadPreview(): Promise<void> {
  if (!site.value) return
  previewLoading.value = true
  try {
    const result = await previewDemoSite({
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

async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

async function handleVerify(): Promise<void> {
  verifying.value = true
  try {
    site.value = await verifyDemoSite(demoSiteId)
  } finally {
    verifying.value = false
  }
}

async function handleRegenerate(): Promise<void> {
  regenerating.value = true
  try {
    site.value = await regenerateDemoSite(demoSiteId)
    await loadPreview()
  } finally {
    regenerating.value = false
  }
}

async function handleInvite(): Promise<void> {
  inviting.value = true
  try {
    site.value = await inviteDemoSiteClientToCms(demoSiteId)
  } catch (error) {
    alert(error instanceof Error ? error.message : "Échec de l'invitation")
  } finally {
    inviting.value = false
  }
}

async function handleDelete(): Promise<void> {
  if (!site.value || !confirm(`Supprimer le site "${site.value.business_name}" ?`)) return
  deleting.value = true
  try {
    await deleteDemoSite(demoSiteId)
    await navigateTo('/dashboard/demo-sites')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  try {
    site.value = await getDemoSite(demoSiteId)
    await loadPreview()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger le site'
  } finally {
    pending.value = false
  }
})
</script>

<style scoped>
.loader-smooth {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-left-color: #f9f9f9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
