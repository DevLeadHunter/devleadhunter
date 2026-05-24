<template>
  <div class="mx-auto max-w-3xl">
    <div class="mb-8">
      <NuxtLink to="/dashboard/demo-sites" class="text-sm text-blue-400 underline">← Back to demo sites</NuxtLink>
      <h1 class="mt-3 text-xl font-semibold text-[#f9f9f9]">Edit demo site</h1>
      <p v-if="site" class="text-muted mt-1 text-sm">{{ site.business_name }} · {{ site.slug }}</p>
    </div>

    <div v-if="pending" class="text-muted text-sm">Loading…</div>
    <div v-else-if="loadError" class="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
      {{ loadError }}
    </div>
    <form v-else-if="site" class="space-y-6" @submit.prevent="handleSave">
      <div class="space-y-4 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-6">
        <h2 class="text-base font-medium text-[#f9f9f9]">Business information</h2>
        <div>
          <label class="text-muted mb-1 block text-sm">Business name *</label>
          <input v-model="form.business_name" type="text" class="input-field w-full" required />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label class="text-muted mb-1 block text-sm">Phone</label>
            <input v-model="form.phone" type="text" class="input-field w-full" />
          </div>
          <div>
            <label class="text-muted mb-1 block text-sm">City</label>
            <input v-model="form.city" type="text" class="input-field w-full" />
          </div>
        </div>
        <div>
          <label class="text-muted mb-1 block text-sm">Client email *</label>
          <input v-model="form.email" type="email" required class="input-field w-full" />
          <p class="text-muted mt-1 text-xs">Used for Storyblok CMS access.</p>
        </div>
        <div>
          <label class="text-muted mb-1 block text-sm">Short description</label>
          <textarea v-model="form.description" rows="3" class="input-field w-full" />
        </div>
      </div>

      <div class="space-y-4 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-6">
        <h2 class="text-base font-medium text-[#f9f9f9]">Template</h2>
        <div class="grid gap-4">
          <button
            v-for="template in templates"
            :key="template.id"
            type="button"
            :class="[
              'rounded-lg border p-4 text-left transition',
              form.template_id === template.id
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-[#30363d] bg-[#1a1a1a] hover:border-[#484f58]',
            ]"
            @click="form.template_id = template.id"
          >
            <p class="font-medium text-[#f9f9f9]">{{ template.name }}</p>
            <p class="text-muted mt-1 text-sm">{{ template.description }}</p>
          </button>
        </div>
      </div>

      <div
        v-if="saveMessage"
        :class="[
          'rounded-lg border p-4 text-sm',
          saveSuccess
            ? 'border-green-500/30 bg-green-500/10 text-green-200'
            : 'border-red-500/30 bg-red-500/10 text-red-300',
        ]"
      >
        {{ saveMessage }}
      </div>

      <div class="flex flex-wrap gap-3">
        <button type="submit" class="btn-primary" :disabled="isSaving || !canSave">
          {{ isSaving ? 'Saving…' : 'Save & regenerate' }}
        </button>
        <button type="button" class="btn-secondary" :disabled="isRegenerating" @click="handleRegenerate">
          {{ isRegenerating ? 'Regenerating…' : 'Regenerate only' }}
        </button>
        <button
          v-if="site.demo_url && site.demo_url_live"
          type="button"
          class="btn-secondary"
          @click="openDemoUrl(site.demo_url!)"
        >
          Open demo
        </button>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { DemoSite, DemoSiteTemplate } from '~/services/demoSiteService'
import { getDemoSite, listDemoSiteTemplates, regenerateDemoSite, updateDemoSite } from '~/services/demoSiteService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const route = useRoute()
const demoSiteId: number = Number(route.params.id)

const { openExternalUrl } = useOpenExternalUrl()

const site: Ref<DemoSite | null> = ref(null)
const pending: Ref<boolean> = ref(true)
const loadError: Ref<string | null> = ref(null)
const templates: Ref<DemoSiteTemplate[]> = ref([])
const isSaving: Ref<boolean> = ref(false)
const isRegenerating: Ref<boolean> = ref(false)
const saveMessage: Ref<string | null> = ref(null)
const saveSuccess: Ref<boolean> = ref(false)

const form: Ref<{
  business_name: string
  template_id: string
  phone: string
  email: string
  city: string
  description: string
}> = ref({
  business_name: '',
  template_id: 'plumber-simple',
  phone: '',
  email: '',
  city: '',
  description: '',
})

const canSave: ComputedRef<boolean> = computed((): boolean => {
  const emailValid: boolean = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email.trim())
  return form.value.business_name.trim().length >= 2 && emailValid
})

/**
 * Open a demo URL in the system browser (desktop) or a new tab (web).
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Apply API response to local state and show a status message.
 */
function applySiteUpdate(updatedSite: DemoSite, message: string): void {
  site.value = updatedSite
  saveMessage.value = message
  saveSuccess.value = updatedSite.status !== 'failed'
}

/**
 * Save form changes and regenerate the demo site content.
 */
async function handleSave(): Promise<void> {
  if (!site.value || !canSave.value) {
    return
  }
  isSaving.value = true
  saveMessage.value = null
  try {
    const updatedSite: DemoSite = await updateDemoSite(demoSiteId, {
      business_name: form.value.business_name.trim(),
      template_id: form.value.template_id,
      email: form.value.email.trim(),
      phone: form.value.phone.trim() || undefined,
      city: form.value.city.trim() || undefined,
      description: form.value.description.trim() || undefined,
    })
    applySiteUpdate(updatedSite, updatedSite.verification_message ?? 'Demo site updated and regenerated.')
  } catch (error) {
    console.error(error)
    saveMessage.value = error instanceof Error ? error.message : 'Failed to update demo site'
    saveSuccess.value = false
  } finally {
    isSaving.value = false
  }
}

/**
 * Regenerate content from current stored fields without saving form edits.
 */
async function handleRegenerate(): Promise<void> {
  if (!site.value) {
    return
  }
  isRegenerating.value = true
  saveMessage.value = null
  try {
    const updatedSite: DemoSite = await regenerateDemoSite(demoSiteId)
    applySiteUpdate(updatedSite, updatedSite.verification_message ?? 'Demo site regenerated.')
  } catch (error) {
    console.error(error)
    saveMessage.value = error instanceof Error ? error.message : 'Failed to regenerate demo site'
    saveSuccess.value = false
  } finally {
    isRegenerating.value = false
  }
}

onMounted(async (): Promise<void> => {
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
    }
  } catch (error) {
    console.error(error)
    loadError.value = error instanceof Error ? error.message : 'Failed to load demo site'
  } finally {
    pending.value = false
  }
})
</script>
