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

          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-accent-soft)]"
          >
            <UIcon name="i-lucide-message-square-text" class="h-5 w-5 text-[var(--app-accent-ink)]" />
          </div>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Envoyer un SMS</h2>
            <p v-if="form.to" class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              À {{ form.recipient_name || form.to }}
            </p>
            <p v-else class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">Mobile français (06/07)</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <form id="send-sms-form" class="flex-1 space-y-4 overflow-y-auto px-5 py-4" @submit.prevent="handleSend">
          <div
            v-if="!providerReady"
            class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3 text-xs text-[var(--app-ink-soft)]"
          >
            Le canal SMS n'est pas encore activé côté serveur (clé smsmode manquante). L'envoi échouera tant qu'elle
            n'est pas configurée.
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Numéro mobile <span class="text-[var(--app-red)]">*</span>
            </label>
            <input
              v-model="form.to"
              type="tel"
              required
              class="input-field"
              placeholder="06 12 34 56 78"
              autocomplete="tel"
            />
            <p class="text-muted mt-1 text-[11px]">{{ acceptedMobileNumberLabel }}</p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Nom du destinataire</label>
            <input v-model="form.recipient_name" type="text" class="input-field" placeholder="Jean Dupont" />
          </div>

          <div v-if="props.prospect">
            <label class="text-muted mb-1.5 block text-xs font-medium">Modèle</label>
            <UiSelectField
              v-model="selectedTemplateKey"
              :options="templateOptions"
              placeholder="Choisir un modèle…"
              :disabled="isLoadingTemplate"
            />
            <p class="text-muted mt-1 text-[11px]">
              Rempli pour ce prospect avec le lien de sa démo, à retoucher avant l'envoi si besoin.
            </p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Message <span class="text-[var(--app-red)]">*</span>
            </label>
            <textarea
              v-model="form.text"
              required
              rows="6"
              class="input-field resize-none"
              placeholder="Bonjour, je vous ai envoyé un aperçu de site web…"
            />
            <div v-if="segmentCount" class="mt-1.5 flex items-center justify-between text-[11px]">
              <span class="text-muted">
                {{ segmentCount.characters }} caractère{{ segmentCount.characters > 1 ? 's' : '' }} ·
                {{ segmentCount.segments }} SMS
                <span v-if="segmentCount.is_unicode" class="text-[var(--app-red)]">
                  · accents/emoji : capacité réduite
                </span>
              </span>
            </div>
            <p v-if="isTooLong" class="mt-1 text-[11px] font-medium text-[var(--app-red)]">
              {{ smsTooLongWarning }}
            </p>
            <p class="text-muted mt-1 text-[11px]">La mention de désinscription est ajoutée à l'envoi.</p>
          </div>
        </form>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSending" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="send-sms-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSending || isTooLong"
          >
            <UIcon v-if="isSending" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isSending ? 'Envoi…' : 'Envoyer' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { SendSmsForm, UiSendSmsDrawerEmits, UiSendSmsDrawerProps } from '~/types/UiSendSmsDrawer'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { Prospect } from '~/types'
import type { SendSmsPrefill } from '~/types/DrawerStack'
import type { SelectFieldOption } from '~/types/SelectField'
import type { SmsConfig, SmsSendResult, SmsTemplate, SmsTemplatePreview } from '~/services/smsService'
import type { SmsSegmentCount } from '~/types/SmsSegmentCount'
import type { ProspectCountryOption } from '~/utils/prospectCountries'
import { computed, ref, watch } from 'vue'
import { SmsService } from '~/services/smsService'
import { useToast } from '~/composables/useToast'
import { ProspectCountries } from '~/utils/prospectCountries'

const props: UiSendSmsDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospect: {
    type: Object as PropType<Prospect | null>,
    default: null,
  },
  prefill: {
    type: Object as PropType<SendSmsPrefill | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiSendSmsDrawerEmits> = defineEmits<UiSendSmsDrawerEmits>()

const toast: UseToastReturn = useToast()

const SEGMENT_COUNT_DELAY_MILLISECONDS: number = 300

let segmentCountTimer: ReturnType<typeof setTimeout> | undefined
let segmentCountRequestNumber: number = 0

/** Whether the manual send request is in flight. */
const isSending: Ref<boolean> = ref(false)

/** Whether the platform smsmode key is configured (drives the warning banner). */
const providerReady: Ref<boolean> = ref(true)

/** Key of the recipient the form was last initialised for. */
const lastInitKey: Ref<string> = ref('')

/** Manual send form state. */
const form: Ref<SendSmsForm> = ref({
  to: '',
  recipient_name: '',
  text: '',
})

/** Library templates offered for a linked prospect, as select options. */
const templateOptions: Ref<SelectFieldOption<string>[]> = ref([])

/** Key of the library template the message was filled from (empty = free text). */
const selectedTemplateKey: Ref<string> = ref('')

/** Whether a template is being rendered for the prospect. */
const isLoadingTemplate: Ref<boolean> = ref(false)

const segmentCount: Ref<SmsSegmentCount | null> = ref(null)

/** A message that would bill (and send) more SMS than allowed is blocked. */
const isTooLong: ComputedRef<boolean> = computed(
  (): boolean => segmentCount.value !== null && segmentCount.value.segments > segmentCount.value.maximum_segments,
)

const smsTooLongWarning: ComputedRef<string> = computed((): string =>
  segmentCount.value
    ? `Message trop long : il partirait en ${segmentCount.value.segments} SMS. ` +
      `Raccourcissez-le pour tenir en ${segmentCount.value.maximum_segments}.`
    : '',
)

const acceptedMobileNumberLabel: ComputedRef<string> = computed((): string => {
  const country: ProspectCountryOption = ProspectCountries.option(props.prospect?.country)
  return country.code === 'FR'
    ? 'Uniquement les mobiles français commençant par 06 ou 07.'
    : `Mobile du prospect (${country.label}), au format national ou international.`
})

/**
 * Load the SMS config to know whether the server key is ready.
 * @returns A promise that resolves once loaded.
 */
async function loadConfig(): Promise<void> {
  try {
    const config: SmsConfig = await SmsService.getConfig()
    providerReady.value = config.provider_ready
  } catch {
    providerReady.value = true
  }
}

/**
 * Load the library templates offered for a linked prospect, labelled by touch.
 * @returns A promise that resolves once the options are set.
 */
async function loadTemplates(): Promise<void> {
  if (!props.prospect) return
  try {
    const templates: SmsTemplate[] = await SmsService.listTemplates()
    templateOptions.value = templates.map(
      (template: SmsTemplate): SelectFieldOption<string> => ({
        value: template.key,
        label: `${template.category === 'first_contact' ? 'Premier contact' : 'Relance'} · ${template.name}`,
      }),
    )
  } catch {
    templateOptions.value = []
  }
}

/**
 * Fill the message with a template rendered for the linked prospect (editable afterwards).
 * @param key - The chosen template key.
 * @returns A promise that resolves once the message is filled.
 */
async function applyTemplate(key: string): Promise<void> {
  if (!key || !props.prospect) return
  isLoadingTemplate.value = true
  try {
    const preview: SmsTemplatePreview = await SmsService.previewTemplate(key, props.prospect.id)
    form.value.text = preview.body
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de préparer ce modèle pour ce prospect')
    selectedTemplateKey.value = ''
  } finally {
    isLoadingTemplate.value = false
  }
}

/**
 * Ask the API how many segments the typed message bills, the opt-out mention of its recipient's country included.
 * @param text - The message as typed.
 * @returns A promise that resolves once the count of the latest request is stored.
 */
async function refreshSegmentCount(text: string): Promise<void> {
  segmentCountRequestNumber += 1
  const requestNumber: number = segmentCountRequestNumber
  if (!text.trim()) {
    segmentCount.value = null
    return
  }
  try {
    const count: SmsSegmentCount = await SmsService.countSegments({ text, prospect_id: props.prospect?.id ?? null })
    if (requestNumber === segmentCountRequestNumber) segmentCount.value = count
  } catch {
    if (requestNumber === segmentCountRequestNumber) segmentCount.value = null
  }
}

/**
 * Recount the segments once the user pauses typing.
 * @param text - The message as typed.
 */
function scheduleSegmentCount(text: string): void {
  clearTimeout(segmentCountTimer)
  segmentCountTimer = setTimeout((): void => {
    refreshSegmentCount(text)
  }, SEGMENT_COUNT_DELAY_MILLISECONDS)
}

/**
 * Send the SMS through the manual endpoint, then notify the host so the stack can navigate back.
 * @returns A promise that resolves once the SMS has been dispatched.
 */
async function handleSend(): Promise<void> {
  if (isTooLong.value) {
    toast.error(smsTooLongWarning.value)
    return
  }
  isSending.value = true
  try {
    const result: SmsSendResult = await SmsService.sendManual({
      to: form.value.to,
      text: form.value.text,
      prospect_id: props.prospect?.id ?? null,
      recipient_name: form.value.recipient_name || null,
    })
    if (result.sent) {
      toast.success('SMS envoyé')
      emit('sent')
    } else {
      toast.error(result.reason ?? "Échec de l'envoi du SMS")
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'envoi du SMS")
  } finally {
    isSending.value = false
  }
}

watch(
  (): [boolean, number | undefined, SendSmsPrefill | null] => [props.open, props.prospect?.id, props.prefill ?? null],
  ([open]: [boolean, number | undefined, SendSmsPrefill | null]): void => {
    if (!open) return
    void loadConfig()
    // Only when the recipient changes: returning from a stacked drawer must not wipe the draft.
    const key: string = props.prefill
      ? `prefill:${props.prefill.to}|${props.prefill.text}`
      : `prospect:${props.prospect?.id ?? 'blank'}`
    if (key === lastInitKey.value) return
    lastInitKey.value = key
    selectedTemplateKey.value = ''
    templateOptions.value = []
    if (props.prefill) {
      form.value = { ...props.prefill }
      return
    }
    form.value = {
      to: props.prospect?.phone ?? '',
      recipient_name: props.prospect?.name ?? '',
      text: '',
    }
    loadTemplates()
  },
  { immediate: true },
)

watch(selectedTemplateKey, applyTemplate)

watch((): string => form.value.text, scheduleSegmentCount)
</script>

<style scoped>
/* Panel slide from right */
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
