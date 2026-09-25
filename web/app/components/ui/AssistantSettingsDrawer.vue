<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && assistant"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[520px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="assistant-settings-title"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            type="button"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            aria-label="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)]"
          >
            <UIcon name="i-lucide-pencil" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </div>
          <div class="min-w-0 flex-1">
            <h2
              id="assistant-settings-title"
              class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]"
            >
              Personnaliser {{ assistant.assistant_name }}
            </h2>
            <p class="text-muted mt-0.5 truncate text-sm">{{ assistant.business_name }}</p>
          </div>
          <button
            type="button"
            class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Fermer"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <form class="flex-1 space-y-5 overflow-y-auto px-5 py-4" @submit.prevent="save">
          <section class="flex flex-col gap-3">
            <h3 class="app-label !text-[0.6rem]">Identité</h3>
            <label class="flex flex-col gap-1">
              <span class="text-xs font-medium text-[var(--app-ink)]">Entreprise affichée</span>
              <input v-model="form.business_name" type="text" class="app-input" maxlength="255" required />
            </label>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs font-medium text-[var(--app-ink)]">Réceptionniste</span>
              <AssistantPersonaPicker v-model="form.assistant_name" :portrait-base-url="portraitBaseUrl" />
            </div>
            <label class="flex flex-col gap-1">
              <span class="text-xs font-medium text-[var(--app-ink)]">Prénom affiché</span>
              <input v-model="form.assistant_name" type="text" class="app-input" maxlength="64" placeholder="Sofia" />
              <span class="text-[11px] text-[var(--app-ink-soft)]">
                Un autre prénom garde le visage de l'un des six, selon son genre.
              </span>
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-xs font-medium text-[var(--app-ink)]">Ton</span>
              <input
                v-model="form.tone"
                type="text"
                class="app-input"
                maxlength="255"
                placeholder="professionnel et chaleureux"
              />
            </label>
            <div class="flex flex-col gap-1.5">
              <span class="text-xs font-medium text-[var(--app-ink)]">Langues proposées</span>
              <UiChipToggleGroup v-model="form.languages" :options="LANGUAGE_OPTIONS" label="Langues proposées" />
              <p v-if="form.languages.length === 0" class="text-xs text-[var(--app-red)]">
                Choisissez au moins une langue.
              </p>
            </div>
            <div class="flex items-center justify-between gap-3">
              <span class="text-xs font-medium text-[var(--app-ink)]">Couleur d'accent</span>
              <div class="flex items-center gap-2">
                <input
                  v-model="form.accent_color"
                  type="color"
                  class="h-8 w-10 cursor-pointer rounded border border-[var(--app-line)] bg-transparent"
                  aria-label="Choisir la couleur d'accent"
                />
                <input
                  v-model="form.accent_color"
                  type="text"
                  class="app-input w-28"
                  maxlength="32"
                  placeholder="#c8862f"
                  aria-label="Couleur d'accent en hexadécimal"
                />
              </div>
            </div>
          </section>

          <section class="flex flex-col gap-3 border-t border-[var(--app-line-soft)] pt-4">
            <div class="flex flex-col gap-0.5">
              <h3 class="app-label !text-[0.6rem]">Alertes au commerçant</h3>
              <p class="text-muted text-xs leading-relaxed">
                Une fois l'assistant vendu : chaque demande par email, et un SMS pour celles qui ne peuvent pas
                attendre. Rappel le lendemain si elle n'est pas traitée.
              </p>
            </div>
            <label class="flex flex-col gap-1">
              <span class="text-xs font-medium text-[var(--app-ink)]">Email du commerçant</span>
              <input
                v-model="form.email"
                type="email"
                inputmode="email"
                autocomplete="off"
                class="app-input"
                maxlength="255"
                placeholder="contact@entreprise.fr"
              />
              <span class="text-muted text-xs leading-relaxed">
                Reçoit les demandes, le rapport mensuel et le lien de l'espace client.
              </span>
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-xs font-medium text-[var(--app-ink)]">Mobile du commerçant</span>
              <input
                v-model="form.alert_phone"
                type="tel"
                inputmode="tel"
                autocomplete="off"
                class="app-input"
                maxlength="32"
                placeholder="06 12 34 56 78 ou +352 621 123 456"
              />
            </label>
            <UiSwitch id="assistant-alert-sms" v-model="form.alert_sms_enabled" label="SMS" />
            <template v-if="form.alert_sms_enabled">
              <p v-if="form.alert_phone.trim() === ''" class="text-muted text-xs leading-relaxed">
                Sans mobile, aucun SMS ne part : seul l'email de résumé est envoyé.
              </p>
              <div class="flex flex-col gap-1.5">
                <span class="text-xs font-medium text-[var(--app-ink)]">SMS immédiat pour</span>
                <UiChipToggleGroup
                  v-model="form.alert_sms_types"
                  :options="ALERT_TYPE_OPTIONS"
                  label="SMS immédiat pour"
                />
              </div>
              <div class="flex flex-col gap-1.5">
                <span class="text-xs font-medium text-[var(--app-ink)]">Ne pas déranger</span>
                <div class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <span>de</span>
                  <div class="w-24">
                    <UiSelectField v-model="form.alert_quiet_start_hour" :options="HOUR_OPTIONS" />
                  </div>
                  <span>à</span>
                  <div class="w-24">
                    <UiSelectField v-model="form.alert_quiet_end_hour" :options="HOUR_OPTIONS" />
                  </div>
                </div>
                <span class="text-muted text-xs leading-relaxed">Les SMS reçus dans la plage partent à sa fin.</span>
              </div>
            </template>
            <UiSwitch
              id="assistant-alert-email"
              v-model="form.alert_email_enabled"
              label="Email de résumé (toutes les demandes)"
            />
          </section>

          <section class="flex flex-col gap-1.5 border-t border-[var(--app-line-soft)] pt-4">
            <h3 class="app-label !text-[0.6rem]">Modèle</h3>
            <UiSwitch id="assistant-eu-only" v-model="form.eu_only" label="IA hébergée en Europe (Mistral)" />
            <p class="text-muted text-xs leading-relaxed">
              Les échanges de cet assistant ne partent jamais chez un autre fournisseur, même en cas de panne de Mistral
              (l'assistant propose alors de laisser ses coordonnées).
            </p>
          </section>
        </form>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="emit('close')">
            Annuler
          </button>
          <button
            type="button"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSaving || form.languages.length === 0"
            @click="save"
          >
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type {
  AiAssistantAlertSettings,
  AiAssistantEditForm,
  AiAssistantRequestType,
  AiAssistantSummary,
  AiAssistantUpdatePayload,
} from '~/types/AiAssistant'
import type { SelectFieldOption } from '~/types/SelectField'
import type { UseToastReturn } from '~/types/Composables'
import type { UiAssistantSettingsDrawerEmits, UiAssistantSettingsDrawerProps } from '~/types/UiAssistantSettingsDrawer'
import AssistantPersonaPicker from '~/components/ai-assistants/AssistantPersonaPicker.vue'
import { AiAssistantService } from '~/services/aiAssistantService'
import { useToast } from '~/composables/useToast'

/** Edit an assistant's identity, the alerts its business receives, and its model constraints. */
const props: UiAssistantSettingsDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  assistant: {
    type: Object as PropType<AiAssistantSummary | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiAssistantSettingsDrawerEmits> = defineEmits<UiAssistantSettingsDrawerEmits>()

const toast: UseToastReturn = useToast()

/** Starts of the API refusals worth showing as they are. */
const SAVE_REFUSALS: string[] = ["Numéro d'alerte", 'Adresse email', '« IA hébergée en Europe »']

/** Request types the owner can have texted at once, the ones that cannot wait first. */
const ALERT_TYPE_OPTIONS: SelectFieldOption<AiAssistantRequestType>[] = [
  { value: 'quote', label: 'Devis' },
  { value: 'appointment', label: 'Rendez-vous' },
  { value: 'urgent', label: 'Urgence' },
  { value: 'question', label: 'Question' },
  { value: 'other', label: 'Autre' },
]

/** Whole hours of the day, for the quiet window. */
const HOUR_OPTIONS: SelectFieldOption<number>[] = Array.from(
  { length: 24 },
  (_: unknown, hour: number): SelectFieldOption<number> => ({ value: hour, label: `${hour} h` }),
)

/** Languages a customer can offer, in the order they matter for the target markets. */
const LANGUAGE_OPTIONS: SelectFieldOption<string>[] = [
  { value: 'fr', label: 'Français' },
  { value: 'nl', label: 'Nederlands' },
  { value: 'de', label: 'Deutsch' },
  { value: 'en', label: 'English' },
  { value: 'lu', label: 'Lëtzebuergesch' },
  { value: 'it', label: 'Italiano' },
  { value: 'es', label: 'Español' },
]

const form: Ref<AiAssistantEditForm> = ref(emptyForm())
const isSaving: Ref<boolean> = ref(false)

/** The demo host serving the portraits, read off the assistant's demo link (empty when it is not a URL). */
const portraitBaseUrl: ComputedRef<string> = computed((): string => {
  try {
    return new URL(props.assistant?.demo_url ?? '').origin
  } catch {
    return ''
  }
})

/**
 * A blank form, before an assistant fills it.
 * @returns The form with every field at its neutral value.
 */
function emptyForm(): AiAssistantEditForm {
  return {
    assistant_name: '',
    business_name: '',
    tone: '',
    accent_color: '',
    languages: [],
    email: '',
    alert_phone: '',
    alert_sms_enabled: true,
    alert_email_enabled: true,
    alert_sms_types: [],
    alert_quiet_start_hour: 22,
    alert_quiet_end_hour: 8,
    eu_only: false,
  }
}

/**
 * The form as the assistant is now.
 * @param assistant - The assistant to edit.
 * @returns The prefilled form.
 */
function formOf(assistant: AiAssistantSummary): AiAssistantEditForm {
  return {
    assistant_name: assistant.assistant_name,
    business_name: assistant.business_name,
    tone: assistant.tone ?? '',
    accent_color: assistant.accent_color ?? '',
    languages: [...assistant.languages],
    email: assistant.email ?? '',
    alert_phone: assistant.alerts.phone ?? '',
    alert_sms_enabled: assistant.alerts.sms_enabled,
    alert_email_enabled: assistant.alerts.email_enabled,
    alert_sms_types: [...assistant.alerts.sms_types],
    alert_quiet_start_hour: assistant.alerts.quiet_start_hour,
    alert_quiet_end_hour: assistant.alerts.quiet_end_hour,
    eu_only: assistant.eu_only,
  }
}

/**
 * The alert settings the form changed, so an untouched setting keeps following the API default.
 * @param alerts - The assistant's current alert settings.
 * @param edited - The edited form.
 * @returns Only the alert fields that differ from the current settings.
 */
function changedAlertFields(alerts: AiAssistantAlertSettings, edited: AiAssistantEditForm): AiAssistantUpdatePayload {
  const changes: AiAssistantUpdatePayload = {}
  if (edited.alert_phone.trim() !== (alerts.phone ?? '')) changes.alert_phone = edited.alert_phone.trim()
  if (edited.alert_sms_enabled !== alerts.sms_enabled) changes.alert_sms_enabled = edited.alert_sms_enabled
  if (edited.alert_email_enabled !== alerts.email_enabled) changes.alert_email_enabled = edited.alert_email_enabled
  const sameTypes: boolean =
    edited.alert_sms_types.length === alerts.sms_types.length &&
    edited.alert_sms_types.every((type: AiAssistantRequestType): boolean => alerts.sms_types.includes(type))
  if (!sameTypes) changes.alert_sms_types = edited.alert_sms_types
  if (edited.alert_quiet_start_hour !== alerts.quiet_start_hour) {
    changes.alert_quiet_start_hour = edited.alert_quiet_start_hour
  }
  if (edited.alert_quiet_end_hour !== alerts.quiet_end_hour) changes.alert_quiet_end_hour = edited.alert_quiet_end_hour
  return changes
}

/**
 * Whether a reply still belongs to the drawer on screen: not closed, not switched to another assistant meanwhile.
 * @param assistantId - The assistant the request was made for.
 * @returns True when the reply may act on the drawer.
 */
function isShowing(assistantId: number): boolean {
  return props.open && props.assistant?.id === assistantId
}

/**
 * Persist the customization; the host refreshes the pages showing the assistant and leaves the drawer.
 * @returns A promise resolved once saved or refused.
 */
async function save(): Promise<void> {
  const target: AiAssistantSummary | null = props.assistant
  if (!target || isSaving.value) return
  if (form.value.languages.length === 0) {
    toast.error('Choisissez au moins une langue.')
    return
  }
  isSaving.value = true
  try {
    const payload: AiAssistantUpdatePayload = {
      assistant_name: form.value.assistant_name,
      business_name: form.value.business_name,
      tone: form.value.tone,
      accent_color: form.value.accent_color,
      languages: form.value.languages,
      ...(form.value.email.trim() !== (target.email ?? '') ? { email: form.value.email.trim() } : {}),
      ...changedAlertFields(target.alerts, form.value),
      ...(form.value.eu_only !== target.eu_only ? { eu_only: form.value.eu_only } : {}),
    }
    const updated: AiAssistantSummary = await AiAssistantService.update(target.id, payload)
    if (!isShowing(target.id)) return
    toast.success('Assistant personnalisé.')
    emit('saved', updated)
  } catch (error: unknown) {
    // The API explains what it refused (alert number, email, Europe-hosted AI without Mistral); anything else stays generic.
    const detail: string = error instanceof Error ? error.message : ''
    const explained: boolean = SAVE_REFUSALS.some((prefix: string): boolean => detail.startsWith(prefix))
    toast.error(explained ? detail : 'Enregistrement impossible pour le moment.')
  } finally {
    isSaving.value = false
  }
}

watch(
  (): AiAssistantSummary | null => (props.open ? props.assistant : null),
  (assistant: AiAssistantSummary | null): void => {
    form.value = assistant ? formOf(assistant) : emptyForm()
    isSaving.value = false
  },
  { immediate: true },
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
