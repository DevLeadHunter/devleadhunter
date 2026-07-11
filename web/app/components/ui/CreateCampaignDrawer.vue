<template>
  <Teleport to="body">
    <!-- Pas de backdrop : drawer non-modal (navigation possible pendant qu'il
         est ouvert), fermeture par X / Échap. -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-megaphone" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Nouvelle campagne</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              Séquence de cold email : envoi initial A/B puis relances
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <form
          id="create-campaign-form"
          class="flex-1 space-y-5 overflow-y-auto px-5 py-4"
          @submit.prevent="handleCreate"
        >
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="campaign-name">Nom de la campagne</label>
            <input
              id="campaign-name"
              v-model="form.name"
              type="text"
              required
              minlength="2"
              placeholder="Ex : Plombiers Lyon — juillet"
              class="input-field"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="campaign-description">
              Description (optionnel)
            </label>
            <textarea
              id="campaign-description"
              v-model="form.description"
              rows="3"
              placeholder="Objectif, cible, notes…"
              class="input-field h-auto min-h-20 py-2"
            ></textarea>
          </div>

          <!-- ── Modèles d'email ─────────────────────────────────── -->
          <div class="space-y-3">
            <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Modèles d'email</p>

            <!-- Variante A -->
            <div>
              <div class="mb-1.5 flex items-center justify-between">
                <label class="text-muted text-xs font-medium">
                  Variante A
                  <span class="font-normal text-[var(--app-faint)]">— envoi initial</span>
                </label>
                <button
                  type="button"
                  class="flex items-center gap-1 text-[11px] text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                  @click="openCreateTemplate('a')"
                >
                  <UIcon name="i-lucide-plus" class="h-3 w-3" />
                  Créer un modèle
                </button>
              </div>
              <div v-if="isLoadingTemplates" class="flex h-9 items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                Chargement…
              </div>
              <UiTemplateSelect
                v-else
                :model-value="form.templateIdA"
                :templates="templates"
                @update:model-value="form.templateIdA = $event"
              />
            </div>

            <!-- Variante B -->
            <div>
              <div class="mb-1.5 flex items-center justify-between">
                <label class="text-muted text-xs font-medium">
                  Variante B
                  <span class="font-normal text-[var(--app-faint)]">— test A/B, optionnel</span>
                </label>
                <button
                  type="button"
                  class="flex items-center gap-1 text-[11px] text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                  @click="openCreateTemplate('b')"
                >
                  <UIcon name="i-lucide-plus" class="h-3 w-3" />
                  Créer un modèle
                </button>
              </div>
              <div v-if="isLoadingTemplates" class="flex h-9 items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                Chargement…
              </div>
              <UiTemplateSelect
                v-else
                :model-value="form.templateIdB"
                :templates="templates"
                @update:model-value="form.templateIdB = $event"
              />
            </div>
          </div>
        </form>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isCreating" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="create-campaign-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isCreating"
          >
            <UIcon v-if="isCreating" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isCreating ? 'Création…' : 'Créer la campagne' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import type { EmailTemplate } from '~/types'
import { useCampaignsStore } from '~/stores/campaigns'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'
import { getEmailTemplates } from '~/services/emailTemplatesService'

/** Local shape of the campaign creation form. */
interface CreateCampaignForm {
  name: string
  description: string
  /** Template ID for variant A (0 = none selected). */
  templateIdA: number
  /** Template ID for variant B / A/B test (0 = none). */
  templateIdB: number
}

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

const campaignsStore = useCampaignsStore()
const drawerStack = useDrawerStackStore()
const toast = useToast()

/** Whether the create request is in flight. */
const isCreating: Ref<boolean> = ref<boolean>(false)

/** Whether the template list is being fetched. */
const isLoadingTemplates: Ref<boolean> = ref<boolean>(false)

/** Available email templates for the select fields. */
const templates: Ref<EmailTemplate[]> = ref<EmailTemplate[]>([])

/** Which template slot triggered the last "Créer un modèle" click. */
const pendingTemplateSlot: Ref<'a' | 'b' | null> = ref<'a' | 'b' | null>(null)

/** Campaign creation form state. */
const form: Ref<CreateCampaignForm> = ref<CreateCampaignForm>({
  name: '',
  description: '',
  templateIdA: 0,
  templateIdB: 0,
})

/**
 * Stack length captured when `open` last transitioned to false.
 * Used to distinguish a fresh open (stack was empty) from a return after a
 * nested drawer was closed (stack was ≥ 2).
 */
let stackLengthWhenHidden: number = 0

/**
 * Load the email template list from the API.
 * @returns A promise that resolves once the list is loaded.
 */
async function loadTemplates(): Promise<void> {
  isLoadingTemplates.value = true
  try {
    templates.value = await getEmailTemplates()
  } catch {
    // Non-critical — the selects will remain empty.
  } finally {
    isLoadingTemplates.value = false
  }
}

/**
 * Push the email template creation drawer on the stack, remembering which
 * slot (A or B) should receive the newly-created template.
 * @param slot - Which template slot triggered this action.
 */
function openCreateTemplate(slot: 'a' | 'b'): void {
  pendingTemplateSlot.value = slot
  drawerStack.push({ kind: 'email-template', mode: 'create', template: null })
}

/**
 * Create the campaign then close the drawer (the store prepends it to the list).
 * @returns A promise resolved once the campaign is created.
 */
async function handleCreate(): Promise<void> {
  isCreating.value = true
  try {
    await campaignsStore.createCampaign({
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      prospect_ids: [],
      template_id: form.value.templateIdA || undefined,
      ab_template_id_b: form.value.templateIdB || undefined,
    })
    toast.success('Campagne créée avec succès')
    emit('close')
  } catch {
    toast.error('Erreur lors de la création de la campagne')
  } finally {
    isCreating.value = false
  }
}

// Reset and reload only on fresh open (stack was empty before we were pushed),
// NOT when returning from a nested drawer like the email-template creator.
watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (!open) {
      stackLengthWhenHidden = drawerStack.stack.length
      return
    }
    if (stackLengthWhenHidden === 0) {
      form.value = { name: '', description: '', templateIdA: 0, templateIdB: 0 }
      pendingTemplateSlot.value = null
      void loadTemplates()
    }
  },
)

// When a template is saved from the nested email-template drawer, refresh the
// list and auto-select the new template in whichever slot triggered the action.
watch(
  (): number => drawerStack.emailTemplatesRefreshCounter,
  async (): Promise<void> => {
    if (!props.open) return
    const prevIds = new Set<number>(templates.value.map((t: EmailTemplate): number => t.id))
    await loadTemplates()
    if (pendingTemplateSlot.value !== null) {
      const newTemplate: EmailTemplate | undefined = templates.value.find(
        (t: EmailTemplate): boolean => !prevIds.has(t.id),
      )
      if (newTemplate) {
        if (pendingTemplateSlot.value === 'a') {
          form.value.templateIdA = newTemplate.id
        } else {
          form.value.templateIdB = newTemplate.id
        }
      }
      pendingTemplateSlot.value = null
    }
  },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
