<template>
  <div class="mx-auto max-w-4xl">
    <!-- Header -->
    <div class="mb-6">
      <NuxtLink
        to="/dashboard/demo-sites"
        class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Sites démo
      </NuxtLink>
      <p class="app-label mt-4 flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Website builder
      </p>
      <h1 class="app-page-title mt-2">Créer un site vitrine</h1>
      <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
        Un vrai site professionnel pour votre prospect — publié sur demo.dibodev.fr pendant 14 jours.
      </p>
    </div>

    <DemoSitesWizardStepper :steps="steps" :current-step="currentStep" @navigate="handleStepNavigate" />

    <!-- Étape 1 : Informations -->
    <div v-if="currentStep === 1" key="step-1" class="wizard-step app-card space-y-6 p-6 md:p-7">
      <div>
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Informations entreprise</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Sélectionnez un prospect existant ou saisissez les informations manuellement.
        </p>
      </div>

      <!-- Source segmented control -->
      <div class="flex gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] p-1">
        <button type="button" :class="segmentClass(inputMode === 'prospect')" @click="inputMode = 'prospect'">
          <UIcon name="i-lucide-users" class="h-3.5 w-3.5" />
          Depuis un prospect
        </button>
        <button type="button" :class="segmentClass(inputMode === 'manual')" @click="inputMode = 'manual'">
          <UIcon name="i-lucide-pen-line" class="h-3.5 w-3.5" />
          Saisie manuelle
        </button>
      </div>

      <div v-if="inputMode === 'prospect'" class="space-y-2">
        <label class="app-label block">Choisir un prospect</label>
        <select v-model="selectedProspectId" class="app-input w-full" @change="applyProspect">
          <option :value="null">— Sélectionner —</option>
          <option v-for="p in prospects" :key="p.id" :value="p.id">
            {{ p.name }}{{ p.city ? ` · ${p.city}` : '' }}
          </option>
        </select>
        <p v-if="prospectsLoading" class="text-xs text-[var(--app-ink-soft)]">Chargement des prospects…</p>
        <p v-else-if="!prospects.length" class="text-xs text-[var(--app-accent-ink)]">
          Aucun prospect enregistré.
          <NuxtLink to="/dashboard/my-prospects" class="underline underline-offset-2">Ajouter un prospect</NuxtLink>
        </p>
        <p v-else-if="form.prospect_id" class="inline-flex items-center gap-1.5 text-xs text-[var(--app-green)]">
          <UIcon name="i-lucide-circle-check" class="h-3.5 w-3.5" />
          Champs pré-remplis — le site sera relié à ce prospect
        </p>
      </div>

      <div class="grid gap-5 md:grid-cols-2">
        <div class="md:col-span-2">
          <label class="app-label mb-1.5 block">Nom de l'entreprise *</label>
          <input v-model="form.business_name" type="text" class="app-input w-full" placeholder="Plomberie Dupont" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Téléphone</label>
          <input v-model="form.phone" type="text" class="app-input w-full" placeholder="01 23 45 67 89" />
        </div>
        <div>
          <label class="app-label mb-1.5 block">Ville</label>
          <input v-model="form.city" type="text" class="app-input w-full" placeholder="Paris" />
        </div>
        <div class="md:col-span-2">
          <label class="app-label mb-1.5 block">Email client *</label>
          <input v-model="form.email" type="email" class="app-input w-full" placeholder="client@example.com" />
        </div>
        <div class="md:col-span-2">
          <label class="app-label mb-1.5 block">Description courte</label>
          <textarea
            v-model="form.description"
            rows="3"
            class="app-input h-auto w-full py-2"
            placeholder="Dépannage plomberie 24h/24, installation sanitaire, recherche de fuite…"
          />
        </div>
      </div>

      <div class="flex items-center justify-between gap-4 border-t border-[var(--app-line-soft)] pt-5">
        <p v-if="!canGoToStep2" class="text-xs text-[var(--app-ink-soft)]">
          Le nom et un email valide sont requis pour continuer.
        </p>
        <span v-else></span>
        <button type="button" class="app-btn-primary" :disabled="!canGoToStep2" @click="goToStep(2)">
          Continuer
          <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <!-- Étape 2 : Template -->
    <div v-else-if="currentStep === 2" key="step-2" class="wizard-step space-y-6">
      <div>
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Choix de la template</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Sélectionnez un modèle et personnalisez les couleurs de la charte graphique.
        </p>
      </div>
      <DemoSitesTemplatePicker
        v-model="form.template_id"
        :templates="templates"
        :theme="form.theme"
        @update:theme="form.theme = $event"
      />
      <div class="flex justify-between border-t border-[var(--app-line-soft)] pt-5">
        <button type="button" class="app-btn-secondary" @click="goToStep(1)">
          <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
          Retour
        </button>
        <button type="button" class="app-btn-primary" @click="loadPreviewAndContinue">
          Voir l'aperçu
          <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <!-- Étape 3 : Aperçu -->
    <div v-else-if="currentStep === 3" key="step-3" class="wizard-step space-y-6">
      <div>
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Aperçu du site</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Faites défiler l'aperçu et testez la navigation avant publication.
        </p>
      </div>

      <div v-if="previewLoading" class="app-card flex flex-col items-center justify-center gap-4 py-24">
        <div class="loader-ring"></div>
        <p class="font-label text-xs tracking-wide text-[var(--app-ink-soft)] uppercase">Génération de l'aperçu…</p>
      </div>
      <DemoSitesDemoSitePreviewFrame
        v-else-if="previewContent"
        :content="previewContent"
        :business-name="form.business_name"
        :template-id="form.template_id"
      />

      <!-- Récapitulatif -->
      <div class="app-card p-5 md:p-6">
        <p class="app-label mb-4">Récapitulatif</p>
        <dl class="grid gap-x-8 gap-y-3 sm:grid-cols-2">
          <div v-for="item in recapItems" :key="item.label" class="flex items-baseline justify-between gap-4">
            <dt class="text-xs text-[var(--app-ink-soft)]">{{ item.label }}</dt>
            <dd class="text-right text-sm font-medium text-[var(--app-ink)]">{{ item.value }}</dd>
          </div>
        </dl>
      </div>

      <div class="flex justify-between border-t border-[var(--app-line-soft)] pt-5">
        <button type="button" class="app-btn-secondary" @click="goToStep(2)">
          <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
          Modifier la template
        </button>
        <button type="button" class="app-btn-primary" @click="goToStep(4)">
          Continuer vers la publication
          <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>

    <!-- Étape 4 : Publication -->
    <div v-else-if="currentStep === 4" key="step-4" class="wizard-step app-card space-y-6 p-6 md:p-7">
      <div>
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Publication</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Confirmez la génération — le site sera publié immédiatement.
        </p>
      </div>

      <label
        class="flex cursor-pointer items-start gap-3.5 rounded-xl border p-4 transition-colors"
        :class="
          form.invite_client_to_cms
            ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]/60'
            : 'border-[var(--app-line)] bg-[var(--app-bg)] hover:border-[var(--app-ink-soft)]'
        "
      >
        <input v-model="form.invite_client_to_cms" type="checkbox" class="mt-0.5 h-4 w-4 accent-(--app-accent)" />
        <span>
          <span class="text-sm font-medium text-[var(--app-ink)]">Inviter le client au CMS Storyblok</span>
          <span class="mt-1 block text-xs leading-relaxed text-[var(--app-ink-soft)]">
            Storyblok enverra un email d'invitation au client. Décochez pour inviter plus tard depuis la fiche du site.
          </span>
        </span>
      </label>

      <p class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Le site démo sera actif pendant 14 jours, puis supprimé automatiquement.
      </p>

      <div class="flex justify-between border-t border-[var(--app-line-soft)] pt-5">
        <button type="button" class="app-btn-secondary" @click="goToStep(3)">
          <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
          Retour à l'aperçu
        </button>
        <button type="button" class="app-btn-primary" :disabled="isSubmitting" @click="handleGenerate">
          <UIcon
            :name="isSubmitting ? 'i-lucide-loader-circle' : 'i-lucide-rocket'"
            :class="['h-3.5 w-3.5', isSubmitting && 'animate-spin']"
          />
          {{ isSubmitting ? 'Publication en cours…' : 'Publier le site' }}
        </button>
      </div>
    </div>

    <!-- Étape 5 : Terminé -->
    <div v-else-if="currentStep === 5 && createdSite" key="step-5" class="wizard-step space-y-5">
      <!-- Échec -->
      <div v-if="isDemoFailed" class="app-card border-[var(--app-red)]/40 p-6 text-center md:p-8">
        <span
          class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[var(--app-red-soft)] text-[var(--app-red)]"
        >
          <UIcon name="i-lucide-x" class="h-6 w-6" />
        </span>
        <h2 class="mt-4 text-lg font-semibold text-[var(--app-ink)]">{{ resultTitle }}</h2>
        <p v-if="resultMessage" class="mx-auto mt-2 max-w-md text-sm text-[var(--app-ink-soft)]">
          {{ resultMessage }}
        </p>
        <div class="mt-6 flex flex-wrap justify-center gap-2">
          <button type="button" class="app-btn-primary" @click="goToStep(4)">Réessayer la publication</button>
          <NuxtLink to="/dashboard/demo-sites" class="app-btn-secondary">Mes sites démo</NuxtLink>
        </div>
      </div>

      <template v-else>
        <!-- Succès / en attente -->
        <div class="app-card p-6 text-center md:p-8">
          <span
            class="mx-auto flex h-14 w-14 items-center justify-center rounded-full"
            :class="
              isDemoLive
                ? 'bg-[var(--app-green-soft)] text-[var(--app-green)]'
                : 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
            "
          >
            <UIcon :name="isDemoLive ? 'i-lucide-check' : 'i-lucide-clock'" class="h-6 w-6" />
          </span>
          <h2 class="mt-4 text-lg font-semibold text-[var(--app-ink)]">{{ resultTitle }}</h2>
          <p v-if="resultMessage" class="mx-auto mt-2 max-w-md text-sm text-[var(--app-ink-soft)]">
            {{ resultMessage }}
          </p>

          <!-- URL -->
          <div
            v-if="createdOpenUrl"
            class="mx-auto mt-6 max-w-lg rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-4 text-left"
          >
            <p class="app-label">URL du site</p>
            <p class="font-label mt-1.5 text-sm break-all text-[var(--app-ink)]">{{ createdOpenUrl }}</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                class="app-btn-secondary h-8 min-h-8 px-3 text-xs"
                @click="openDemoUrl(createdOpenUrl)"
              >
                <UIcon name="i-lucide-external-link" class="h-3 w-3" />
                Ouvrir
              </button>
              <button type="button" class="app-btn-secondary h-8 min-h-8 px-3 text-xs" @click="copyDemoUrl">
                <UIcon :name="copied ? 'i-lucide-check' : 'i-lucide-copy'" class="h-3 w-3" />
                {{ copied ? 'Copié !' : 'Copier le lien' }}
              </button>
              <NuxtLink
                :to="`/dashboard/demo-sites/${createdSite.id}`"
                class="app-btn-secondary h-8 min-h-8 px-3 text-xs"
              >
                <UIcon name="i-lucide-file-text" class="h-3 w-3" />
                Voir la fiche
              </NuxtLink>
            </div>
          </div>
        </div>

        <!-- Et maintenant ? — chaîner vers le démarchage -->
        <div class="app-card p-5 md:p-6">
          <p class="app-label flex items-center gap-2">
            <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
            Et maintenant ?
          </p>
          <p class="mt-2 text-sm leading-relaxed text-[var(--app-ink-soft)]">
            Le site est en ligne — il ne vend rien tant que le prospect ne l'a pas vu. Lancez le démarchage.
          </p>
          <div class="mt-4 flex flex-wrap gap-2">
            <NuxtLink v-if="campaignChainUrl" :to="campaignChainUrl" class="app-btn-primary">
              <UIcon name="i-lucide-megaphone" class="h-3.5 w-3.5" />
              Ajouter à une campagne
            </NuxtLink>
            <button type="button" class="app-btn-secondary" @click="resetForm">
              <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
              Créer un autre site
            </button>
            <NuxtLink to="/dashboard/demo-sites" class="app-btn-secondary">Mes sites démo</NuxtLink>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
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
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const route = useRoute()
const toast = useToast()
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

/** Deep-link to the campaigns page with the prospect pre-selected (null without a linked prospect). */
const campaignChainUrl: ComputedRef<string | null> = computed((): string | null => {
  return form.value.prospect_id ? `/dashboard/campaigns?addProspect=${form.value.prospect_id}` : null
})

/**
 * Classes of a source segmented-control button.
 * @param active - Whether the segment is selected.
 * @returns Tailwind classes for the segment.
 */
function segmentClass(active: boolean): string {
  const base =
    'flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors'
  if (active) {
    return `${base} bg-[var(--app-btn-bg)] text-[var(--app-btn-text)]`
  }
  return `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

function goToStep(step: number): void {
  currentStep.value = step
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

/**
 * Stepper node clicked — allow going back to a previous step
 * (never forward, never once the site is created).
 * @param stepId - Target step id.
 */
function handleStepNavigate(stepId: number): void {
  if (stepId < currentStep.value && currentStep.value < 5) {
    goToStep(stepId)
  }
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
    toast.error(error instanceof Error ? error.message : "Impossible de générer l'aperçu")
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
    toast.error(error instanceof Error ? error.message : 'Échec de la publication')
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
/* Entrée d'étape en animation CSS pure : aucune machinerie JS <Transition>
   (rAF gelé en onglet inactif, reduced-motion…) ne peut figer le wizard. */
.wizard-step {
  animation: wizard-step-in 0.3s ease;
}

@keyframes wizard-step-in {
  from {
    opacity: 0;
    transform: translateX(18px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.loader-ring {
  width: 48px;
  height: 48px;
  border: 3px solid var(--app-line);
  border-left-color: var(--app-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wizard-step {
    animation: none;
  }
}
</style>
