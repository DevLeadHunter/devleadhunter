<template>
  <div class="mx-auto max-w-5xl">
    <div class="mb-8">
      <NuxtLink
        to="/dashboard/demo-sites"
        class="inline-flex items-center gap-2 text-sm text-[#8b949e] transition hover:text-[#f9f9f9]"
      >
        <i class="fa-solid fa-arrow-left text-xs"></i>
        Retour aux sites démo
      </NuxtLink>
      <h1 class="mt-4 text-2xl font-semibold text-[#f9f9f9]">Website builder</h1>
      <p class="mt-2 text-sm text-[#8b949e]">
        Créez un site vitrine professionnel pour votre prospect — publié sur demo.dibodev.fr pendant 14 jours.
      </p>
    </div>

    <DemoSitesWizardStepper :steps="steps" :current-step="currentStep" />

    <Transition name="wizard-step" mode="out-in">
      <!-- Étape 1 : Informations -->
      <div v-if="currentStep === 1" key="step-1" class="card space-y-6 p-6 md:p-8">
        <div>
          <h2 class="text-lg font-semibold text-[#f9f9f9]">Informations entreprise</h2>
          <p class="mt-1 text-sm text-[#8b949e]">
            Sélectionnez un prospect existant ou saisissez les informations manuellement.
          </p>
        </div>

        <div class="flex gap-2 rounded-xl border border-[#30363d] bg-[#0d1117] p-1">
          <button
            type="button"
            :class="[
              'flex-1 rounded-lg px-4 py-2.5 text-sm font-medium transition',
              inputMode === 'prospect' ? 'bg-[#1a1a1a] text-[#f9f9f9]' : 'text-[#8b949e] hover:text-[#f9f9f9]',
            ]"
            @click="inputMode = 'prospect'"
          >
            <i class="fa-solid fa-users mr-2"></i>
            Depuis un prospect
          </button>
          <button
            type="button"
            :class="[
              'flex-1 rounded-lg px-4 py-2.5 text-sm font-medium transition',
              inputMode === 'manual' ? 'bg-[#1a1a1a] text-[#f9f9f9]' : 'text-[#8b949e] hover:text-[#f9f9f9]',
            ]"
            @click="inputMode = 'manual'"
          >
            <i class="fa-solid fa-pen mr-2"></i>
            Saisie manuelle
          </button>
        </div>

        <div v-if="inputMode === 'prospect'" class="space-y-3">
          <label class="text-sm text-[#8b949e]">Choisir un prospect</label>
          <select v-model="selectedProspectId" class="input-field w-full" @change="applyProspect">
            <option :value="null">— Sélectionner —</option>
            <option v-for="p in prospects" :key="p.id" :value="p.id">
              {{ p.name }}{{ p.city ? ` · ${p.city}` : '' }}
            </option>
          </select>
          <p v-if="prospectsLoading" class="text-xs text-[#8b949e]">Chargement des prospects…</p>
          <p v-else-if="!prospects.length" class="text-xs text-amber-300/90">
            Aucun prospect enregistré.
            <NuxtLink to="/dashboard/my-prospects" class="underline">Ajouter un prospect</NuxtLink>
          </p>
        </div>

        <div class="grid gap-5 md:grid-cols-2">
          <div class="md:col-span-2">
            <label class="mb-1 block text-sm text-[#8b949e]">Nom de l'entreprise *</label>
            <input v-model="form.business_name" type="text" class="input-field w-full" placeholder="Plomberie Dupont" />
          </div>
          <div>
            <label class="mb-1 block text-sm text-[#8b949e]">Téléphone</label>
            <input v-model="form.phone" type="text" class="input-field w-full" placeholder="01 23 45 67 89" />
          </div>
          <div>
            <label class="mb-1 block text-sm text-[#8b949e]">Ville</label>
            <input v-model="form.city" type="text" class="input-field w-full" placeholder="Paris" />
          </div>
          <div class="md:col-span-2">
            <label class="mb-1 block text-sm text-[#8b949e]">Email client *</label>
            <input v-model="form.email" type="email" class="input-field w-full" placeholder="client@example.com" />
          </div>
          <div class="md:col-span-2">
            <label class="mb-1 block text-sm text-[#8b949e]">Description courte</label>
            <textarea
              v-model="form.description"
              rows="3"
              class="input-field w-full"
              placeholder="Dépannage plomberie 24h/24, installation sanitaire, recherche de fuite…"
            />
          </div>
        </div>

        <div class="flex justify-end">
          <button type="button" class="btn-primary" :disabled="!canGoToStep2" @click="goToStep(2)">
            Continuer
            <i class="fa-solid fa-arrow-right ml-2"></i>
          </button>
        </div>
      </div>

      <!-- Étape 2 : Template -->
      <div v-else-if="currentStep === 2" key="step-2" class="space-y-6">
        <div>
          <h2 class="text-lg font-semibold text-[#f9f9f9]">Choix du template</h2>
          <p class="mt-1 text-sm text-[#8b949e]">
            Sélectionnez un modèle et personnalisez les couleurs de la charte graphique.
          </p>
        </div>
        <DemoSitesTemplatePicker
          v-model="form.template_id"
          :templates="templates"
          :theme="form.theme"
          @update:theme="form.theme = $event"
        />
        <div class="flex justify-between">
          <button type="button" class="btn-secondary" @click="goToStep(1)">Retour</button>
          <button type="button" class="btn-primary" @click="loadPreviewAndContinue">
            Voir l'aperçu
            <i class="fa-solid fa-eye ml-2"></i>
          </button>
        </div>
      </div>

      <!-- Étape 3 : Aperçu -->
      <div v-else-if="currentStep === 3" key="step-3" class="space-y-6">
        <div>
          <h2 class="text-lg font-semibold text-[#f9f9f9]">Aperçu du site</h2>
          <p class="mt-1 text-sm text-[#8b949e]">
            Faites défiler l'aperçu et testez la navigation avant publication sur Storyblok et demo.dibodev.fr.
          </p>
        </div>

        <div v-if="previewLoading" class="card flex items-center justify-center py-24">
          <div class="loader-smooth"></div>
        </div>
        <DemoSitesDemoSitePreviewFrame
          v-else-if="previewContent"
          :content="previewContent"
          :business-name="form.business_name"
          :template-id="form.template_id"
        />

        <div class="card grid gap-4 p-6 md:grid-cols-2">
          <div v-for="item in recapItems" :key="item.label" class="flex justify-between gap-4 text-sm">
            <span class="text-[#8b949e]">{{ item.label }}</span>
            <span class="text-right font-medium text-[#f9f9f9]">{{ item.value }}</span>
          </div>
        </div>

        <div class="flex justify-between">
          <button type="button" class="btn-secondary" @click="goToStep(2)">Modifier le template</button>
          <button type="button" class="btn-primary" @click="goToStep(4)">
            Continuer vers la publication
            <i class="fa-solid fa-arrow-right ml-2"></i>
          </button>
        </div>
      </div>

      <!-- Étape 4 : Publication -->
      <div v-else-if="currentStep === 4" key="step-4" class="card space-y-6 p-6 md:p-8">
        <div>
          <h2 class="text-lg font-semibold text-[#f9f9f9]">Publication</h2>
          <p class="mt-1 text-sm text-[#8b949e]">Confirmez la génération — le site sera publié immédiatement.</p>
        </div>

        <label
          class="flex cursor-pointer items-start gap-4 rounded-xl border border-[#30363d] bg-[#0d1117] p-5 transition hover:border-[#484f58]"
        >
          <input v-model="form.invite_client_to_cms" type="checkbox" class="mt-1 h-4 w-4 rounded border-[#30363d]" />
          <span>
            <span class="font-medium text-[#f9f9f9]">Inviter le client au CMS Storyblok</span>
            <span class="mt-1 block text-xs text-[#8b949e]">
              Storyblok enverra un email d'invitation au client. Décochez pour inviter plus tard depuis la fiche du
              site.
            </span>
          </span>
        </label>

        <p class="text-xs text-[#8b949e]">
          <i class="fa-solid fa-clock mr-1"></i>
          Le site démo sera actif pendant 14 jours, puis supprimé automatiquement.
        </p>

        <div class="flex justify-between">
          <button type="button" class="btn-secondary" @click="goToStep(3)">Retour à l'aperçu</button>
          <button
            type="button"
            class="btn-primary inline-flex items-center gap-2"
            :disabled="isSubmitting"
            @click="handleGenerate"
          >
            <i v-if="isSubmitting" class="fa-solid fa-spinner fa-spin"></i>
            <i v-else class="fa-solid fa-rocket"></i>
            {{ isSubmitting ? 'Publication en cours…' : 'Publier le site' }}
          </button>
        </div>
      </div>

      <!-- Étape 5 : Terminé -->
      <div
        v-else-if="currentStep === 5 && createdSite"
        key="step-5"
        :class="[
          'card space-y-6 p-6 md:p-8',
          isDemoLive ? 'border-[#2BAD5F]/30' : '',
          isDemoFailed ? 'border-red-500/30' : '',
        ]"
      >
        <div class="text-center">
          <div
            :class="[
              'mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full text-2xl',
              isDemoLive
                ? 'bg-[#2BAD5F]/20 text-[#2BAD5F]'
                : isDemoFailed
                  ? 'bg-red-500/20 text-red-300'
                  : 'bg-amber-500/20 text-amber-300',
            ]"
          >
            <i :class="isDemoLive ? 'fa-solid fa-check' : isDemoFailed ? 'fa-solid fa-xmark' : 'fa-solid fa-clock'"></i>
          </div>
          <h2 class="text-xl font-semibold text-[#f9f9f9]">{{ resultTitle }}</h2>
          <p v-if="resultMessage" class="mt-2 text-sm text-[#8b949e]">{{ resultMessage }}</p>
        </div>

        <div v-if="!isDemoFailed && createdOpenUrl" class="rounded-xl border border-[#30363d] bg-[#0d1117] p-5">
          <p class="text-xs tracking-wide text-[#8b949e] uppercase">URL du site</p>
          <p class="mt-1 font-medium break-all text-[#f9f9f9]">{{ createdOpenUrl }}</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <button type="button" class="btn-primary h-9 px-4 text-xs" @click="openDemoUrl(createdOpenUrl)">
              Ouvrir
            </button>
            <button type="button" class="btn-secondary h-9 px-4 text-xs" @click="copyDemoUrl">
              {{ copied ? 'Copié !' : 'Copier le lien' }}
            </button>
            <NuxtLink
              :to="`/dashboard/demo-sites/${createdSite.id}`"
              class="btn-secondary inline-flex h-9 items-center px-4 text-xs"
              >Voir la fiche</NuxtLink
            >
          </div>
        </div>

        <div class="flex flex-wrap justify-center gap-3">
          <NuxtLink to="/dashboard/demo-sites" class="btn-secondary">Mes sites démo</NuxtLink>
          <button type="button" class="btn-primary" @click="resetForm">Créer un autre site</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import type { DemoSite, DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'
import type { Prospect } from '~/types'
import {
  createDemoSite,
  getDemoSiteOpenUrl,
  isDemoSiteReachable,
  listDemoSiteTemplates,
  previewDemoSite,
} from '~/services/demoSiteService'
import { listProspects } from '~/services/prospectsService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route = useRoute()
const { copy, copied } = useCopyToClipboard()
const { openExternalUrl } = useOpenExternalUrl()

const steps = [
  { id: 1, label: 'Informations' },
  { id: 2, label: 'Template' },
  { id: 3, label: 'Aperçu' },
  { id: 4, label: 'Publication' },
  { id: 5, label: 'Terminé' },
]

const currentStep = ref(1)
const inputMode = ref<'prospect' | 'manual'>('prospect')
const selectedProspectId = ref<number | null>(null)
const prospects = ref<Prospect[]>([])
const prospectsLoading = ref(true)
const templates = ref<DemoSiteTemplate[]>([])
const previewContent = ref<Record<string, unknown> | null>(null)
const previewLoading = ref(false)
const isSubmitting = ref(false)
const createdSite = ref<DemoSite | null>(null)

const defaultTheme: DemoSiteTheme = { primary: '#0284c7', secondary: '#0f172a', accent: '#f59e0b' }

const form = ref({
  business_name: '',
  template_id: 'plumber-signature',
  phone: '',
  email: '',
  city: '',
  description: '',
  invite_client_to_cms: false,
  theme: { ...defaultTheme },
  prospect_id: undefined as number | undefined,
})

const canGoToStep2 = computed(() => {
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email.trim())
  return form.value.business_name.trim().length >= 2 && emailValid
})

const selectedTemplateName = computed(() => {
  return templates.value.find((t) => t.id === form.value.template_id)?.name ?? form.value.template_id
})

const recapItems = computed(() => [
  { label: 'Entreprise', value: form.value.business_name },
  { label: 'Template', value: selectedTemplateName.value },
  { label: 'Ville', value: form.value.city || '—' },
  { label: 'Email', value: form.value.email },
])

const isDemoLive = computed(() => (createdSite.value ? isDemoSiteReachable(createdSite.value) : false))
const createdOpenUrl = computed(() => (createdSite.value ? getDemoSiteOpenUrl(createdSite.value) : null))
const isDemoFailed = computed(() => createdSite.value?.status === 'failed')
const resultTitle = computed(() => {
  if (isDemoFailed.value) return 'Échec de la publication'
  if (isDemoLive.value) return 'Site publié avec succès !'
  return 'Site enregistré — lien pas encore actif'
})
const resultMessage = computed(() => createdSite.value?.verification_message ?? createdSite.value?.error_message ?? '')

function goToStep(step: number): void {
  currentStep.value = step
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function applyProspect(): void {
  const prospect = prospects.value.find((p) => p.id === selectedProspectId.value)
  if (!prospect) return
  form.value.business_name = prospect.name
  form.value.phone = prospect.phone ?? ''
  form.value.email = prospect.email ?? ''
  form.value.city = prospect.city ?? ''
  form.value.prospect_id = prospect.id
  if (prospect.category) {
    form.value.description = `${prospect.category} — services professionnels${prospect.city ? ` à ${prospect.city}` : ''}.`
  }
}

async function loadPreviewAndContinue(): Promise<void> {
  previewLoading.value = true
  goToStep(3)
  try {
    const result = await previewDemoSite({
      business_name: form.value.business_name.trim(),
      template_id: form.value.template_id,
      email: form.value.email.trim(),
      phone: form.value.phone.trim() || undefined,
      city: form.value.city.trim() || undefined,
      description: form.value.description.trim() || undefined,
      theme: form.value.theme,
    })
    previewContent.value = result.content_json
  } catch (error) {
    console.error(error)
    alert(error instanceof Error ? error.message : "Impossible de générer l'aperçu")
    goToStep(2)
  } finally {
    previewLoading.value = false
  }
}

async function handleGenerate(): Promise<void> {
  isSubmitting.value = true
  try {
    createdSite.value = await createDemoSite({
      business_name: form.value.business_name.trim(),
      template_id: form.value.template_id,
      email: form.value.email.trim(),
      invite_client_to_cms: form.value.invite_client_to_cms,
      phone: form.value.phone.trim() || undefined,
      city: form.value.city.trim() || undefined,
      description: form.value.description.trim() || undefined,
      theme: form.value.theme,
      prospect_id: form.value.prospect_id,
    })
    goToStep(5)
  } catch (error) {
    console.error(error)
    alert(error instanceof Error ? error.message : 'Échec de la publication')
  } finally {
    isSubmitting.value = false
  }
}

async function openDemoUrl(url: string): Promise<void> {
  await openExternalUrl(url)
}

async function copyDemoUrl(): Promise<void> {
  if (createdOpenUrl.value) await copy(createdOpenUrl.value)
}

function resetForm(): void {
  currentStep.value = 1
  createdSite.value = null
  previewContent.value = null
  selectedProspectId.value = null
  form.value = {
    business_name: '',
    template_id: 'plumber-signature',
    phone: '',
    email: '',
    city: '',
    description: '',
    invite_client_to_cms: false,
    theme: { ...defaultTheme },
    prospect_id: undefined,
  }
}

onMounted(async () => {
  const [loadedTemplates, loadedProspects] = await Promise.all([
    listDemoSiteTemplates(),
    listProspects().catch(() => [] as Prospect[]),
  ])
  templates.value = loadedTemplates
  prospects.value = loadedProspects
  prospectsLoading.value = false

  if (loadedTemplates[0]?.default_theme) {
    form.value.theme = { ...loadedTemplates[0].default_theme }
  }

  const prospectIdParam = route.query.prospectId
  if (prospectIdParam) {
    selectedProspectId.value = Number(prospectIdParam)
    inputMode.value = 'prospect'
    applyProspect()
  }
})
</script>

<style scoped>
.wizard-step-enter-active,
.wizard-step-leave-active {
  transition: all 0.35s ease;
}
.wizard-step-enter-from {
  opacity: 0;
  transform: translateX(24px);
}
.wizard-step-leave-to {
  opacity: 0;
  transform: translateX(-24px);
}

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
