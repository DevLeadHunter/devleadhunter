<template>
  <div class="mx-auto max-w-3xl">
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Website builder</h1>
      <p class="text-muted mt-1 text-sm">Generate a demo site hosted for 14 days on demo.dibodev.fr</p>
    </div>

    <div class="mb-8 flex items-center gap-2">
      <div v-for="step in steps" :key="step.id" class="flex flex-1 items-center gap-2">
        <div
          :class="[
            'flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold',
            currentStep >= step.id ? 'bg-blue-600 text-white' : 'text-muted bg-[#30363d]',
          ]"
        >
          {{ step.id }}
        </div>
        <span class="text-muted hidden text-xs sm:inline">{{ step.label }}</span>
        <div v-if="step.id < steps.length" class="hidden h-px flex-1 bg-[#30363d] sm:block" />
      </div>
    </div>

    <div v-if="currentStep === 1" class="space-y-4 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-6">
      <h2 class="text-base font-medium text-[#f9f9f9]">Business information</h2>
      <div>
        <label class="text-muted mb-1 block text-sm">Business name *</label>
        <input v-model="form.business_name" type="text" class="input-field w-full" placeholder="Plomberie Dupont" />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <div>
          <label class="text-muted mb-1 block text-sm">Phone</label>
          <input v-model="form.phone" type="text" class="input-field w-full" placeholder="01 23 45 67 89" />
        </div>
        <div>
          <label class="text-muted mb-1 block text-sm">City</label>
          <input v-model="form.city" type="text" class="input-field w-full" placeholder="Paris" />
        </div>
      </div>
      <div>
        <label class="text-muted mb-1 block text-sm">Client email *</label>
        <input v-model="form.email" type="email" required class="input-field w-full" placeholder="client@example.com" />
        <p class="text-muted mt-1 text-xs">Used for Storyblok CMS access (invitation sent to this address).</p>
      </div>
      <div>
        <label class="text-muted mb-1 block text-sm">Short description</label>
        <textarea
          v-model="form.description"
          rows="3"
          class="input-field w-full"
          placeholder="Emergency plumbing services, 24/7 availability…"
        />
      </div>
      <div class="flex justify-end">
        <button type="button" class="btn-primary" :disabled="!canGoToStep2" @click="currentStep = 2">Continue</button>
      </div>
    </div>

    <div v-else-if="currentStep === 2" class="space-y-4">
      <h2 class="text-base font-medium text-[#f9f9f9]">Choose a template</h2>
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
      <div class="flex justify-between">
        <button type="button" class="btn-secondary" @click="currentStep = 1">Back</button>
        <button type="button" class="btn-primary" @click="currentStep = 3">Continue</button>
      </div>
    </div>

    <div v-else-if="currentStep === 3" class="space-y-4 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-6">
      <h2 class="text-base font-medium text-[#f9f9f9]">Review & generate</h2>
      <dl class="space-y-2 text-sm">
        <div class="flex justify-between gap-4">
          <dt class="text-muted">Business</dt>
          <dd class="text-[#f9f9f9]">{{ form.business_name }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-muted">Template</dt>
          <dd class="text-[#f9f9f9]">{{ selectedTemplateName }}</dd>
        </div>
        <div v-if="form.city" class="flex justify-between gap-4">
          <dt class="text-muted">City</dt>
          <dd class="text-[#f9f9f9]">{{ form.city }}</dd>
        </div>
        <div v-if="form.email" class="flex justify-between gap-4">
          <dt class="text-muted">Client email</dt>
          <dd class="text-[#f9f9f9]">{{ form.email }}</dd>
        </div>
        <div v-if="form.phone" class="flex justify-between gap-4">
          <dt class="text-muted">Phone</dt>
          <dd class="text-[#f9f9f9]">{{ form.phone }}</dd>
        </div>
      </dl>
      <p class="text-muted text-xs">The demo site will be live for 14 days, then deleted automatically.</p>
      <div class="flex justify-between">
        <button type="button" class="btn-secondary" @click="currentStep = 2">Back</button>
        <button type="button" class="btn-primary" :disabled="isSubmitting" @click="handleGenerate">
          {{ isSubmitting ? 'Generating…' : 'Generate website' }}
        </button>
      </div>
    </div>

    <div
      v-else-if="currentStep === 4 && createdSite"
      :class="[
        'space-y-4 rounded-lg border p-6',
        isDemoLive ? 'border-green-500/30 bg-green-500/10' : '',
        isDemoUnavailable ? 'border-amber-500/30 bg-amber-500/10' : '',
        isDemoFailed ? 'border-red-500/30 bg-red-500/10' : '',
      ]"
    >
      <h2 class="text-base font-medium text-[#f9f9f9]">
        {{ resultTitle }}
      </h2>
      <p v-if="isDemoFailed" class="text-sm text-red-300">{{ createdSite.error_message }}</p>
      <p v-else-if="resultMessage" class="text-muted text-sm">{{ resultMessage }}</p>

      <div v-if="!isDemoFailed" class="space-y-3 text-sm">
        <div v-if="createdSite.demo_url && isDemoLive" class="flex flex-wrap items-center gap-2">
          <span class="text-muted">Live demo:</span>
          <span class="break-all text-[#f9f9f9]">{{ createdSite.demo_url }}</span>
          <button
            type="button"
            class="btn-secondary shrink-0 px-3 py-1.5 text-xs"
            @click="openDemoUrl(createdSite.demo_url)"
          >
            Open demo
          </button>
          <button type="button" class="btn-secondary shrink-0 px-3 py-1.5 text-xs" @click="copyDemoUrl">
            {{ copied ? 'Copied!' : 'Copy link' }}
          </button>
        </div>

        <div v-else-if="createdSite.demo_url" class="flex flex-wrap items-center gap-2">
          <span class="text-muted">Demo URL (not reachable yet):</span>
          <span class="break-all text-[#f9f9f9]">{{ createdSite.demo_url }}</span>
          <button
            type="button"
            class="btn-secondary shrink-0 px-3 py-1.5 text-xs"
            @click="openDemoUrl(createdSite.demo_url)"
          >
            Open demo
          </button>
          <button type="button" class="btn-secondary shrink-0 px-3 py-1.5 text-xs" @click="copyDemoUrl">
            {{ copied ? 'Copied!' : 'Copy link' }}
          </button>
        </div>

        <p class="text-muted">Expires: {{ formatDate(createdSite.expires_at) }}</p>
        <div v-if="createdSite.storyblok_editor_url" class="rounded border border-[#30363d] bg-[#1a1a1a] p-4">
          <p class="font-medium text-[#f9f9f9]">Storyblok CMS access</p>
          <p class="text-muted mt-2">
            Editor:
            <button
              type="button"
              class="break-all text-blue-400 underline"
              @click="openDemoUrl(createdSite.storyblok_editor_url!)"
            >
              {{ createdSite.storyblok_editor_url }}
            </button>
          </p>
          <p v-if="createdSite.storyblok_login_email" class="mt-1">
            Client email: <span class="text-[#f9f9f9]">{{ createdSite.storyblok_login_email }}</span>
          </p>
          <p v-if="createdSite.storyblok_invite_sent" class="text-muted mt-2">
            An invitation was sent to the client by email. They must accept it and set their Storyblok password.
          </p>
          <p v-else-if="createdSite.storyblok_login_password" class="mt-1">
            Mock password: <code class="text-[#f9f9f9]">{{ createdSite.storyblok_login_password }}</code>
          </p>
          <p v-else-if="createdSite.storyblok_login_email" class="mt-2 text-amber-300/90">
            Storyblok invitation could not be sent automatically. Invite the client manually from the editor.
          </p>
        </div>
      </div>
      <div class="flex flex-wrap gap-3">
        <button
          v-if="!isDemoFailed"
          type="button"
          class="btn-secondary"
          :disabled="isVerifying"
          @click="handleVerifyAgain"
        >
          {{ isVerifying ? 'Checking…' : 'Check again' }}
        </button>
        <NuxtLink to="/dashboard/demo-sites" class="btn-secondary">My demo sites</NuxtLink>
        <button type="button" class="btn-primary" @click="resetForm">Create another</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { DemoSite, DemoSiteTemplate } from '~/services/demoSiteService'
import { createDemoSite, listDemoSiteTemplates, verifyDemoSite } from '~/services/demoSiteService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const { copy, copied } = useCopyToClipboard()
const { openExternalUrl } = useOpenExternalUrl()
const isVerifying: Ref<boolean> = ref(false)

const steps = [
  { id: 1, label: 'Business info' },
  { id: 2, label: 'Template' },
  { id: 3, label: 'Review' },
  { id: 4, label: 'Done' },
]

const currentStep: Ref<number> = ref(1)
const isSubmitting: Ref<boolean> = ref(false)
const templates: Ref<DemoSiteTemplate[]> = ref([])
const createdSite: Ref<DemoSite | null> = ref(null)

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

const canGoToStep2: ComputedRef<boolean> = computed((): boolean => {
  const emailValid: boolean = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email.trim())
  return form.value.business_name.trim().length >= 2 && emailValid
})

const selectedTemplateName: ComputedRef<string> = computed((): string => {
  const match: DemoSiteTemplate | undefined = templates.value.find(
    (t: DemoSiteTemplate): boolean => t.id === form.value.template_id,
  )
  return match?.name ?? form.value.template_id
})

const isDemoLive: ComputedRef<boolean> = computed((): boolean => {
  return createdSite.value?.status === 'active' && Boolean(createdSite.value?.demo_url_live)
})

const isDemoUnavailable: ComputedRef<boolean> = computed((): boolean => {
  return createdSite.value?.status === 'unavailable'
})

const isDemoFailed: ComputedRef<boolean> = computed((): boolean => {
  return createdSite.value?.status === 'failed'
})

const resultTitle: ComputedRef<string> = computed((): string => {
  if (isDemoFailed.value) {
    return 'Demo site generation failed'
  }
  if (isDemoLive.value) {
    return 'Demo site ready'
  }
  if (isDemoUnavailable.value) {
    return 'Demo site saved — link not live yet'
  }
  return 'Demo site status'
})

const resultMessage: ComputedRef<string> = computed((): string => {
  return createdSite.value?.verification_message ?? createdSite.value?.error_message ?? ''
})

/**
 * Open a demo URL in the system browser (desktop) or a new tab (web).
 */
async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

/**
 * Copy the live demo URL to the clipboard.
 */
async function copyDemoUrl(): Promise<void> {
  if (!createdSite.value?.demo_url) {
    return
  }
  await copy(createdSite.value.demo_url)
}

/**
 * Re-run backend verification for the generated demo site.
 */
async function handleVerifyAgain(): Promise<void> {
  if (!createdSite.value) {
    return
  }
  isVerifying.value = true
  try {
    createdSite.value = await verifyDemoSite(createdSite.value.id)
  } catch (error) {
    console.error(error)
    alert(error instanceof Error ? error.message : 'Verification failed')
  } finally {
    isVerifying.value = false
  }
}

/**
 * Format an ISO datetime for display.
 */
function formatDate(value: string): string {
  return new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

/**
 * Submit the stepper form and provision the demo site.
 */
async function handleGenerate(): Promise<void> {
  isSubmitting.value = true
  try {
    createdSite.value = await createDemoSite({
      business_name: form.value.business_name.trim(),
      template_id: form.value.template_id,
      email: form.value.email.trim(),
      phone: form.value.phone.trim() || undefined,
      city: form.value.city.trim() || undefined,
      description: form.value.description.trim() || undefined,
    })
    currentStep.value = 4
  } catch (error) {
    console.error(error)
    alert(error instanceof Error ? error.message : 'Failed to generate demo site')
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Reset the stepper to create another demo site.
 */
function resetForm(): void {
  currentStep.value = 1
  createdSite.value = null
  form.value = {
    business_name: '',
    template_id: 'plumber-simple',
    phone: '',
    email: '',
    city: '',
    description: '',
  }
}

onMounted(async (): Promise<void> => {
  templates.value = await listDemoSiteTemplates()
})
</script>
