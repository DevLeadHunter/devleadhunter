<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-[calc(100dvh-var(--app-drawer-bottom))] w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl"
      >
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
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ isEditing ? 'Modifier la campagne' : 'Nouvelle campagne' }}
            </h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              {{
                isEditing
                  ? 'Nom et description — les modèles se règlent dans la configuration'
                  : 'Séquence de cold email : envoi initial A/B puis relances'
              }}
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <form id="campaign-form" class="flex-1 space-y-5 overflow-y-auto px-5 py-4" @submit.prevent="handleSubmit">
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

          <div v-if="!isEditing">
            <label class="text-muted mb-1.5 block text-xs font-medium">Canal d'envoi</label>
            <div
              class="flex w-full rounded-full border border-[var(--app-line)] bg-[var(--app-surface-2)] p-0.5 sm:inline-flex sm:w-auto"
              role="group"
              aria-label="Canal d'envoi"
            >
              <button
                type="button"
                class="flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full px-3 text-sm font-medium transition-colors sm:h-auto sm:flex-none sm:py-1.5 sm:text-xs"
                :class="
                  form.channel === 'email'
                    ? 'bg-[var(--app-ink)] text-[var(--app-bg)]'
                    : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
                "
                :aria-pressed="form.channel === 'email'"
                @click="form.channel = 'email'"
              >
                <UIcon name="i-lucide-mail" class="h-3.5 w-3.5" />
                Email
              </button>
              <button
                type="button"
                class="flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full px-3 text-sm font-medium transition-colors sm:h-auto sm:flex-none sm:py-1.5 sm:text-xs"
                :class="
                  form.channel === 'sms'
                    ? 'bg-[var(--app-ink)] text-[var(--app-bg)]'
                    : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
                "
                :aria-pressed="form.channel === 'sms'"
                @click="form.channel = 'sms'"
              >
                <UIcon name="i-lucide-message-square-text" class="h-3.5 w-3.5" />
                SMS
              </button>
            </div>
          </div>

          <div v-if="!isEditing && form.channel === 'sms'" class="space-y-3">
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">Modèle de message SMS</label>
              <UiSelectField
                :model-value="form.smsTemplateKey"
                :options="smsTemplateOptions"
                placeholder="Choisir un modèle…"
                @update:model-value="form.smsTemplateKey = $event"
              />
            </div>
            <p class="text-muted text-[11px] leading-relaxed">
              Le modèle choisi part vers chaque prospect mobile avec le lien de son site démo. Pas d'A/B : le message et
              la mention « STOP » sont rendus automatiquement (tu peux le changer ensuite sur la campagne). L'expéditeur
              se règle dans Paramètres
              <UIcon name="i-lucide-arrow-right" class="inline-block h-[1em] w-[1em] align-[-0.125em]" /> Relance SMS.
            </p>
          </div>

          <div v-if="!isEditing && form.channel === 'email'" class="space-y-3">
            <p class="text-muted text-[11px] font-medium tracking-wide uppercase">Modèles d'email</p>

            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">
                Variante A
                <span class="font-normal text-[var(--app-faint)]">— envoi initial</span>
              </label>
              <div v-if="isLoadingTemplates" class="flex h-9 items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                Chargement…
              </div>
              <UiTemplateSelect
                v-else
                :model-value="form.templateIdA"
                :templates="templates"
                allow-create
                @update:model-value="form.templateIdA = $event"
                @create="openCreateTemplate('a')"
                @preview="previewTemplate"
              />
            </div>

            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">
                Variante B
                <span class="font-normal text-[var(--app-faint)]">— test A/B, optionnel</span>
              </label>
              <div v-if="isLoadingTemplates" class="flex h-9 items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                Chargement…
              </div>
              <UiTemplateSelect
                v-else
                :model-value="form.templateIdB"
                :templates="templates"
                allow-create
                @update:model-value="form.templateIdB = $event"
                @create="openCreateTemplate('b')"
                @preview="previewTemplate"
              />
            </div>
          </div>
        </form>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="emit('close')">
            Annuler
          </button>
          <button type="submit" form="campaign-form" class="btn-primary flex-1" :disabled="isSaving">
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ submitLabel }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { CampaignForm, UiCampaignDrawerEmits, UiCampaignDrawerProps } from '~/types/UiCampaignDrawer'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { EmailTemplate } from '~/types'
import type { CampaignDetailResponse } from '~/services/campaignService'
import type { CampaignFormDrawerMode } from '~/types/DrawerStack'
import type { SelectFieldOption } from '~/types/SelectField'
import { useCampaignsStore } from '~/stores/campaigns'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'
import { CampaignService } from '~/services/campaignService'
import { EmailTemplatesService } from '~/services/emailTemplatesService'
import { SmsService, type SmsTemplate } from '~/services/smsService'

/** Drawer to create an email campaign, or rename an existing one. */
const props: UiCampaignDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String as PropType<CampaignFormDrawerMode>,
    default: 'create',
  },
  campaign: {
    type: Object as PropType<CampaignDetailResponse | null>,
    default: null,
  },
})

const emit: EmitFn<UiCampaignDrawerEmits> = defineEmits<UiCampaignDrawerEmits>()

const campaignsStore: ReturnType<typeof useCampaignsStore> = useCampaignsStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const toast: UseToastReturn = useToast()

/** Whether the create or update request is in flight. */
const isSaving: Ref<boolean> = ref(false)

const isEditing: ComputedRef<boolean> = computed((): boolean => props.mode === 'edit')

const submitLabel: ComputedRef<string> = computed((): string => {
  if (isSaving.value) return isEditing.value ? 'Enregistrement…' : 'Création…'
  return isEditing.value ? 'Enregistrer' : 'Créer la campagne'
})

/** Whether the template list is being fetched. */
const isLoadingTemplates: Ref<boolean> = ref(false)

/** Available email templates for the select fields. */
const templates: Ref<EmailTemplate[]> = ref([])

/** First-contact SMS library templates, for the SMS-channel picker. */
const smsTemplates: Ref<SmsTemplate[]> = ref([])

/** Options for the SMS template picker. */
const smsTemplateOptions: ComputedRef<SelectFieldOption<string>[]> = computed((): SelectFieldOption<string>[] =>
  smsTemplates.value.map(
    (template: SmsTemplate): SelectFieldOption<string> => ({
      value: template.key,
      label: template.name,
    }),
  ),
)

/** Which template slot triggered the last "Créer un modèle" click. */
const pendingTemplateSlot: Ref<'a' | 'b' | null> = ref(null)

/** Campaign form state. */
const form: Ref<CampaignForm> = ref({
  name: '',
  description: '',
  channel: 'email',
  templateIdA: 0,
  templateIdB: 0,
  smsTemplateKey: '',
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
    templates.value = await EmailTemplatesService.getEmailTemplates()
  } catch {
    // Non-critical — the selects will remain empty.
  } finally {
    isLoadingTemplates.value = false
  }
}

/**
 * Load the first-contact SMS library templates and preselect the default when none is chosen.
 * @returns A promise resolved once the SMS templates are loaded.
 */
async function loadSmsTemplates(): Promise<void> {
  smsTemplates.value = await SmsService.listTemplates('first_contact').catch((): SmsTemplate[] => [])
  if (!form.value.smsTemplateKey) {
    const preselected: SmsTemplate | undefined =
      smsTemplates.value.find((template: SmsTemplate): boolean => template.is_default) ?? smsTemplates.value[0]
    if (preselected) form.value.smsTemplateKey = preselected.key
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
 * Stack the read-only preview of a template, so its body is visible before picking it.
 * @param templateId - Identifier of the template to preview.
 */
function previewTemplate(templateId: number): void {
  const template: EmailTemplate | undefined = templates.value.find(
    (candidate: EmailTemplate): boolean => candidate.id === templateId,
  )
  if (template) drawerStack.push({ kind: 'email-template', mode: 'preview', template })
}

/**
 * Create or rename the campaign, then hand back to the host.
 * @returns A promise resolved once the campaign is saved.
 */
async function handleSubmit(): Promise<void> {
  isSaving.value = true
  try {
    if (isEditing.value && props.campaign) {
      await CampaignService.update(props.campaign.id, {
        name: form.value.name.trim(),
        description: form.value.description.trim() || undefined,
      })
      toast.success('Campagne mise à jour')
      emit('saved')
      return
    }
    const isSms: boolean = form.value.channel === 'sms'
    await campaignsStore.createCampaign({
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      channel: form.value.channel,
      prospect_ids: [],
      // SMS campaigns carry no email template — they render a first-contact SMS library template.
      template_id: isSms ? undefined : form.value.templateIdA || undefined,
      ab_template_id_b: isSms ? undefined : form.value.templateIdB || undefined,
      sms_template_key: isSms ? form.value.smsTemplateKey || undefined : undefined,
    })
    toast.success(isSms ? 'Campagne SMS créée' : 'Campagne créée avec succès')
    emit('close')
  } catch {
    toast.error(isEditing.value ? 'Erreur lors de la mise à jour' : 'Erreur lors de la création de la campagne')
  } finally {
    isSaving.value = false
  }
}

// Only on a fresh open: returning from a nested drawer must not reset the form.
watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (!open) {
      stackLengthWhenHidden = drawerStack.stack.length
      return
    }
    if (stackLengthWhenHidden !== 0) return
    form.value = {
      name: props.campaign?.name ?? '',
      description: props.campaign?.description ?? '',
      channel: props.campaign?.channel ?? 'email',
      templateIdA: 0,
      templateIdB: 0,
      smsTemplateKey: props.campaign?.sms_template_key ?? '',
    }
    pendingTemplateSlot.value = null
    if (!isEditing.value) {
      void loadTemplates()
      void loadSmsTemplates()
    }
  },
)

// Auto-selects the new template in whichever slot opened the nested drawer.
watch(
  (): number => drawerStack.emailTemplatesRefreshCounter,
  async (): Promise<void> => {
    if (!props.open) return
    const prevIds: Set<number> = new Set<number>(templates.value.map((t: EmailTemplate): number => t.id))
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
