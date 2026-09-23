<template>
  <div class="flex min-h-full flex-col gap-6">
    <div>
      <p class="app-label flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Module IA
      </p>
      <h1 class="app-page-title mt-2">Assistants IA</h1>
      <p class="text-muted mt-1 max-w-2xl text-sm leading-relaxed">
        Les réceptionnistes IA générés pour vos prospects : lien de démo à envoyer, script à coller sur leur site, et
        les contacts captés 24h/24.
      </p>
    </div>

    <div v-if="isLoading" class="flex h-40 items-center justify-center">
      <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <template v-else>
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Mes assistants</h2>
          <span class="text-muted text-xs tabular-nums">{{ assistants.length }}</span>
        </div>

        <div v-if="assistants.length === 0" class="app-card flex flex-col items-center gap-3 px-6 py-10 text-center">
          <UIcon name="i-lucide-bot" class="h-8 w-8 text-[var(--app-faint)]" />
          <p class="text-muted max-w-sm text-sm leading-relaxed">
            Aucun assistant généré. Ouvrez un prospect et cliquez « Générer un assistant IA » pour créer sa démo.
          </p>
        </div>

        <div v-else class="grid gap-3 @2xl:grid-cols-2">
          <article v-for="assistant in assistants" :key="assistant.id" class="app-card flex flex-col gap-3 p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ assistant.business_name }}</p>
                <p class="text-muted truncate text-xs">{{ assistant.assistant_name }}</p>
              </div>
              <span
                class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase"
                :class="
                  assistant.status === 'active'
                    ? 'border-[var(--app-green)] text-[var(--app-green)]'
                    : 'border-[var(--app-line)] text-[var(--app-ink-soft)]'
                "
              >
                {{ assistant.status === 'active' ? 'Actif' : assistant.status }}
              </span>
            </div>

            <div class="flex flex-wrap gap-1">
              <span
                v-for="language in assistant.languages"
                :key="language"
                class="rounded border border-[var(--app-line)] px-1.5 py-0.5 text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase"
              >
                {{ language }}
              </span>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <a
                :href="demoUrlWithInternal(assistant.demo_url)"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-secondary h-8 text-xs"
              >
                <UIcon name="i-lucide-external-link" class="mr-1.5 h-3.5 w-3.5" />
                Voir la démo
              </a>
              <button type="button" class="btn-secondary h-8 text-xs" @click="copySnippet(assistant)">
                <UIcon name="i-lucide-code" class="mr-1.5 h-3.5 w-3.5" />
                Copier le script
              </button>
              <button type="button" class="btn-secondary h-8 text-xs" @click="openEdit(assistant)">
                <UIcon name="i-lucide-pencil" class="mr-1.5 h-3.5 w-3.5" />
                Personnaliser
              </button>
              <button
                v-if="confirmingId !== assistant.id"
                type="button"
                class="text-muted ml-auto flex h-8 cursor-pointer items-center gap-1 rounded-lg px-2 text-xs transition-colors hover:text-[var(--app-red)]"
                @click="confirmingId = assistant.id"
              >
                <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                Supprimer
              </button>
              <button
                v-else
                type="button"
                class="ml-auto flex h-8 cursor-pointer items-center gap-1 rounded-lg bg-[var(--app-red)] px-2.5 text-xs font-medium text-white"
                @click="removeAssistant(assistant)"
              >
                <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
                Confirmer
              </button>
            </div>

            <code
              class="block truncate rounded-md bg-[var(--app-surface-2)] px-2 py-1.5 text-[11px] text-[var(--app-ink-soft)]"
            >
              {{ assistant.embed_snippet }}
            </code>
          </article>
        </div>
      </section>

      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Contacts captés</h2>
          <span class="text-muted text-xs tabular-nums">{{ leads.length }}</span>
        </div>

        <div v-if="leads.length === 0" class="app-card px-6 py-8 text-center">
          <p class="text-muted text-sm leading-relaxed">
            Aucun contact capté pour le moment. Chaque visiteur qui laisse ses coordonnées dans un assistant apparaît
            ici.
          </p>
        </div>

        <ul v-else class="app-card divide-y divide-[var(--app-line-soft)] overflow-hidden">
          <li
            v-for="lead in leads"
            :key="lead.id"
            class="flex flex-col gap-1 px-4 py-3 @xl:flex-row @xl:items-center @xl:gap-4"
          >
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-[var(--app-ink)]">{{ lead.name }}</p>
              <p class="text-muted truncate text-xs">{{ lead.contact }}</p>
            </div>
            <p v-if="lead.need" class="text-muted min-w-0 flex-1 truncate text-xs @xl:text-sm">« {{ lead.need }} »</p>
            <div class="flex shrink-0 items-center gap-3 text-xs">
              <span class="text-[var(--app-ink-soft)]">{{ lead.business_name }}</span>
              <span class="text-[var(--app-faint)] tabular-nums">{{ formatDate(lead.created_at) }}</span>
            </div>
          </li>
        </ul>
      </section>
    </template>

    <div
      v-if="editing"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)] p-4"
      @click.self="closeEdit"
    >
      <div class="app-card max-h-[90vh] w-full max-w-md overflow-y-auto p-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-[var(--app-ink)]">Personnaliser l'assistant</h3>
          <button
            type="button"
            class="text-muted cursor-pointer transition-colors hover:text-[var(--app-ink)]"
            aria-label="Fermer"
            @click="closeEdit"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex flex-col gap-3">
          <label class="flex flex-col gap-1">
            <span class="app-label !text-[0.6rem]">Entreprise affichée</span>
            <input v-model="editForm.business_name" type="text" class="app-input" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="app-label !text-[0.6rem]">Nom de l'assistant</span>
            <input v-model="editForm.assistant_name" type="text" class="app-input" placeholder="Sofia" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="app-label !text-[0.6rem]">Ton</span>
            <input v-model="editForm.tone" type="text" class="app-input" placeholder="professionnel et chaleureux" />
          </label>

          <div class="flex flex-col gap-1.5">
            <span class="app-label !text-[0.6rem]">Langues</span>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="language in LANGUAGE_OPTIONS"
                :key="language.code"
                type="button"
                class="cursor-pointer rounded-full border px-2.5 py-1 text-xs transition-colors"
                :class="
                  editForm.languages.includes(language.code)
                    ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
                    : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
                "
                @click="toggleLanguage(language.code)"
              >
                {{ language.label }}
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between gap-3">
            <span class="app-label !text-[0.6rem]">Couleur d'accent</span>
            <div class="flex items-center gap-2">
              <input
                v-model="editForm.accent_color"
                type="color"
                class="h-8 w-10 cursor-pointer rounded border border-[var(--app-line)] bg-transparent"
                aria-label="Choisir la couleur d'accent"
              />
              <input v-model="editForm.accent_color" type="text" class="app-input w-28" placeholder="#c8862f" />
            </div>
          </div>
        </div>

        <div class="mt-5 flex gap-2">
          <button type="button" class="btn-secondary flex-1" @click="closeEdit">Annuler</button>
          <button type="button" class="btn-primary flex-1" :disabled="isSaving" @click="saveEdit">
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { onMounted, ref } from 'vue'
import { AiAssistantService } from '~/services/aiAssistantService'
import type {
  AiAssistantEditForm,
  AiAssistantLead,
  AiAssistantLeadsResponse,
  AiAssistantListResponse,
  AiAssistantSummary,
  AiAssistantUpdatePayload,
} from '~/types/AiAssistant'
import type { UseToastReturn } from '~/types/Composables'
import { useToast } from '~/composables/useToast'
import { parseApiDate } from '~/utils/date'

/**
 * Management page for the AI assistant module: the generated assistants (demo link + embed
 * snippet) and the leads their visitors left. Generation itself happens from a prospect.
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

useSeoMeta({ title: 'Assistants IA — DevLeadHunter' })

const toast: UseToastReturn = useToast()

const assistants: Ref<AiAssistantSummary[]> = ref([])
const leads: Ref<AiAssistantLead[]> = ref([])
const isLoading: Ref<boolean> = ref(true)
const confirmingId: Ref<number | null> = ref(null)

/** The assistant being customized (null = the modal is closed). */
const editing: Ref<AiAssistantSummary | null> = ref(null)
const editForm: Ref<AiAssistantEditForm> = ref({
  assistant_name: '',
  business_name: '',
  tone: '',
  accent_color: '',
  languages: [],
})
const isSaving: Ref<boolean> = ref(false)

/** Languages a customer can offer, in the order they matter for the target markets. */
const LANGUAGE_OPTIONS: { code: string; label: string }[] = [
  { code: 'fr', label: 'Français' },
  { code: 'nl', label: 'Nederlands' },
  { code: 'de', label: 'Deutsch' },
  { code: 'en', label: 'English' },
  { code: 'lu', label: 'Lëtzebuergesch' },
  { code: 'it', label: 'Italiano' },
  { code: 'es', label: 'Español' },
]

/**
 * Append the internal marker so opening a demo from the dashboard never pollutes its analytics.
 * @param demoUrl - The assistant's public demo URL.
 * @returns The URL carrying `?internal=1`.
 */
function demoUrlWithInternal(demoUrl: string): string {
  return demoUrl.includes('?') ? `${demoUrl}&internal=1` : `${demoUrl}?internal=1`
}

/**
 * Format an API timestamp as a short local date.
 * @param iso - The API date string (UTC, naive).
 * @returns The localised « jour mois » label.
 */
function formatDate(iso: string): string {
  return parseApiDate(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

/**
 * Copy an assistant's embed snippet to the clipboard.
 * @param assistant - The assistant whose snippet to copy.
 * @returns A promise resolved once the copy is attempted.
 */
async function copySnippet(assistant: AiAssistantSummary): Promise<void> {
  try {
    await navigator.clipboard.writeText(assistant.embed_snippet)
    toast.success('Script copié — à coller avant </body> du site du client.')
  } catch {
    toast.error('Copie impossible depuis ce navigateur.')
  }
}

/**
 * Soft-delete an assistant after the inline confirmation.
 * @param assistant - The assistant to remove.
 * @returns A promise resolved once removed and the list refreshed.
 */
async function removeAssistant(assistant: AiAssistantSummary): Promise<void> {
  confirmingId.value = null
  try {
    await AiAssistantService.remove(assistant.id)
    assistants.value = assistants.value.filter((item: AiAssistantSummary): boolean => item.id !== assistant.id)
    toast.success('Assistant supprimé.')
  } catch {
    toast.error("Suppression impossible pour l'instant.")
  }
}

/**
 * Open the customization modal, prefilled from the assistant.
 * @param assistant - The assistant to edit.
 */
function openEdit(assistant: AiAssistantSummary): void {
  editing.value = assistant
  editForm.value = {
    assistant_name: assistant.assistant_name,
    business_name: assistant.business_name,
    tone: assistant.tone ?? '',
    accent_color: assistant.accent_color ?? '',
    languages: [...assistant.languages],
  }
}

/** Close the customization modal without saving. */
function closeEdit(): void {
  editing.value = null
}

/**
 * Toggle a language in the edit form.
 * @param code - The language code to toggle.
 */
function toggleLanguage(code: string): void {
  const languages: string[] = editForm.value.languages
  editForm.value.languages = languages.includes(code)
    ? languages.filter((item: string): boolean => item !== code)
    : [...languages, code]
}

/**
 * Persist the customization and refresh the edited card.
 * @returns A promise resolved once saved.
 */
async function saveEdit(): Promise<void> {
  const target: AiAssistantSummary | null = editing.value
  if (!target || isSaving.value) return
  isSaving.value = true
  try {
    const payload: AiAssistantUpdatePayload = {
      assistant_name: editForm.value.assistant_name,
      business_name: editForm.value.business_name,
      tone: editForm.value.tone,
      accent_color: editForm.value.accent_color,
      languages: editForm.value.languages,
    }
    const updated: AiAssistantSummary = await AiAssistantService.update(target.id, payload)
    assistants.value = assistants.value.map(
      (item: AiAssistantSummary): AiAssistantSummary => (item.id === updated.id ? updated : item),
    )
    editing.value = null
    toast.success('Assistant personnalisé.')
  } catch {
    toast.error('Enregistrement impossible pour le moment.')
  } finally {
    isSaving.value = false
  }
}

/**
 * Load the assistants and their captured leads.
 * @returns A promise resolved once both are loaded.
 */
async function loadData(): Promise<void> {
  isLoading.value = true
  try {
    const [assistantList, leadList]: [AiAssistantListResponse, AiAssistantLeadsResponse] = await Promise.all([
      AiAssistantService.list(),
      AiAssistantService.listLeads(),
    ])
    assistants.value = assistantList.assistants
    leads.value = leadList.leads
  } catch {
    toast.error('Chargement des assistants impossible.')
  } finally {
    isLoading.value = false
  }
}

onMounted((): void => {
  void loadData()
})
</script>
