<template>
  <div class="mx-auto max-w-4xl space-y-8">
    <div>
      <NuxtLink
        :to="`/dashboard/demo-sites/${demoSiteId}`"
        class="inline-flex items-center gap-2 text-sm text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
      >
        <i class="fa-solid fa-arrow-left text-xs"></i>
        Retour à la fiche
      </NuxtLink>
      <h1 class="mt-4 text-2xl font-semibold text-[var(--app-ink)]">Modifier le site démo</h1>
      <p v-if="site" class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ site.business_name }} · {{ site.slug }}</p>
    </div>

    <UiLoader v-if="pending" />

    <div v-else-if="loadError" class="card border-red-500/30 bg-red-500/10 p-6 text-red-300">{{ loadError }}</div>

    <form v-else-if="site" class="space-y-6" @submit.prevent="handleSave">
      <div class="card space-y-5 p-6">
        <h2 class="font-semibold text-[var(--app-ink)]">Informations entreprise</h2>
        <div>
          <label class="mb-1 block text-sm text-[var(--app-ink-soft)]">Nom de l'entreprise *</label>
          <input v-model="form.business_name" type="text" class="input-field w-full" required />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm text-[var(--app-ink-soft)]">Téléphone</label>
            <input v-model="form.phone" type="text" class="input-field w-full" />
          </div>
          <div>
            <label class="mb-1 block text-sm text-[var(--app-ink-soft)]">Ville</label>
            <input v-model="form.city" type="text" class="input-field w-full" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-sm text-[var(--app-ink-soft)]">Email client *</label>
          <input v-model="form.email" type="email" required class="input-field w-full" />
        </div>
        <div>
          <label class="mb-1 block text-sm text-[var(--app-ink-soft)]">Description</label>
          <textarea v-model="form.description" rows="3" class="input-field w-full" />
        </div>
      </div>

      <div class="card space-y-5 p-6">
        <h2 class="font-semibold text-[var(--app-ink)]">Template & couleurs</h2>
        <DemoSitesTemplatePicker
          v-model="form.template_id"
          :templates="templates"
          :theme="form.theme"
          @update:theme="form.theme = $event"
        />
      </div>

      <div
        v-if="saveMessage"
        :class="[
          'card p-4 text-sm',
          saveSuccess ? 'border-[var(--app-green)]/30 text-[var(--app-green)]' : 'border-red-500/30 text-red-300',
        ]"
      >
        {{ saveMessage }}
      </div>

      <div class="flex flex-wrap gap-3">
        <button type="submit" class="btn-primary" :disabled="isSaving || !canSave">
          {{ isSaving ? 'Enregistrement…' : 'Enregistrer & régénérer' }}
        </button>
        <button type="button" class="btn-secondary" :disabled="isRegenerating" @click="handleRegenerate">
          {{ isRegenerating ? 'Régénération…' : 'Régénérer uniquement' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup>
import type { DemoSite, DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'
import { getDemoSite, listDemoSiteTemplates, regenerateDemoSite, updateDemoSite } from '~/services/demoSiteService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route = useRoute()
const demoSiteId = Number(route.params.id)

const site = ref<DemoSite | null>(null)
const pending = ref(true)
const loadError = ref<string | null>(null)
const templates = ref<DemoSiteTemplate[]>([])
const isSaving = ref(false)
const isRegenerating = ref(false)
const saveMessage = ref<string | null>(null)
const saveSuccess = ref(false)

const defaultTheme: DemoSiteTheme = { primary: '#0284c7', secondary: '#0f172a', accent: '#f59e0b' }

const form = ref({
  business_name: '',
  template_id: 'plumber-signature',
  phone: '',
  email: '',
  city: '',
  description: '',
  theme: { ...defaultTheme },
})

const canSave = computed(() => {
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email.trim())
  return form.value.business_name.trim().length >= 2 && emailValid
})

function applySiteUpdate(updatedSite: DemoSite, message: string): void {
  site.value = updatedSite
  saveMessage.value = message
  saveSuccess.value = updatedSite.status !== 'failed'
}

async function handleSave(): Promise<void> {
  if (!site.value || !canSave.value) return
  isSaving.value = true
  saveMessage.value = null
  try {
    const updatedSite = await updateDemoSite(demoSiteId, {
      business_name: form.value.business_name.trim(),
      template_id: form.value.template_id,
      email: form.value.email.trim(),
      phone: form.value.phone.trim() || undefined,
      city: form.value.city.trim() || undefined,
      description: form.value.description.trim() || undefined,
      theme: form.value.theme,
    })
    applySiteUpdate(updatedSite, updatedSite.verification_message ?? 'Site mis à jour et régénéré.')
  } catch (error) {
    saveMessage.value = error instanceof Error ? error.message : 'Échec de la mise à jour'
    saveSuccess.value = false
  } finally {
    isSaving.value = false
  }
}

async function handleRegenerate(): Promise<void> {
  if (!site.value) return
  isRegenerating.value = true
  saveMessage.value = null
  try {
    const updatedSite = await regenerateDemoSite(demoSiteId)
    applySiteUpdate(updatedSite, updatedSite.verification_message ?? 'Site régénéré.')
  } catch (error) {
    saveMessage.value = error instanceof Error ? error.message : 'Échec de la régénération'
    saveSuccess.value = false
  } finally {
    isRegenerating.value = false
  }
}

onMounted(async () => {
  try {
    const [loadedSite, loadedTemplates] = await Promise.all([getDemoSite(demoSiteId), listDemoSiteTemplates()])
    site.value = loadedSite
    templates.value = loadedTemplates
    form.value = {
      business_name: loadedSite.business_name,
      template_id: loadedSite.template_id,
      phone: loadedSite.phone ?? '',
      email: loadedSite.email ?? '',
      city: loadedSite.city ?? '',
      description: loadedSite.description ?? '',
      theme: loadedSite.theme ? { ...loadedSite.theme } : { ...defaultTheme },
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger le site'
  } finally {
    pending.value = false
  }
})
</script>
