<template>
  <section class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-reply" class="h-4 w-4 text-[var(--app-accent)]" />
        <h3 class="text-sm font-semibold text-[var(--app-ink)]">Relance SMS</h3>
      </div>
      <UiSwitch
        id="campaign-sms-follow-up"
        :model-value="isEnabled"
        label="Envoyer une relance"
        @update:model-value="toggleFollowUp"
      />
    </div>

    <p v-if="!isEnabled" class="text-muted text-sm">Sans relance, chaque prospect reçoit un seul SMS.</p>

    <template v-else>
      <div class="flex flex-wrap items-center gap-2 text-sm text-[var(--app-ink)]">
        <span>J+</span>
        <input
          v-model.number="delayDays"
          type="number"
          min="1"
          max="365"
          class="input-field h-9 w-16 text-center"
          aria-label="Jours d'envoi avant la relance"
        />
        <span>jours d'envoi après le premier SMS, à l'heure du prospect</span>
      </div>

      <div class="mt-3">
        <label class="text-muted mb-1.5 block text-xs font-medium">Modèle de la relance</label>
        <UiSelectField
          :model-value="templateKey"
          :options="templateOptions"
          placeholder="Choisir un modèle…"
          aria-label="Modèle de la relance"
          @update:model-value="templateKey = $event"
        />
      </div>

      <p class="text-muted mt-3 mb-1.5 text-xs font-medium">Aperçu de la relance</p>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] p-3">
        <p class="text-sm leading-relaxed whitespace-pre-line text-[var(--app-ink)]">{{ previewText }}</p>
      </div>
      <p class="text-muted mt-1.5 text-[11px]">
        <span v-if="previewSegments">{{ previewSegments }} SMS · </span>La mention de désinscription est ajoutée à
        l'envoi.
      </p>
      <p v-if="isVideoFollowUp" class="text-muted mt-1 text-[11px] leading-relaxed">
        <UIcon name="i-lucide-video-off" class="mr-0.5 inline-block h-3 w-3 align-[-2px]" />
        Prospect sans vidéo prête : sa relance n'est pas envoyée.
      </p>

      <div
        class="mt-3 flex items-start gap-2 rounded-lg border border-[var(--app-green)]/20 bg-[var(--app-green-soft)] px-3 py-2"
      >
        <UIcon name="i-lucide-circle-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-green)]" />
        <p class="text-xs text-[var(--app-ink)]">
          <span class="font-medium">Arrêt automatique à la réponse.</span>
          Ajoutez la réponse SMS du prospect, depuis sa fiche ou l'onglet Résultats : sa relance est annulée.
        </p>
      </div>
    </template>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, ModelRef, PropType, Ref } from 'vue'
import type { SmsTemplate, SmsTemplateModule, SmsTemplatePreview } from '~/services/smsService'
import type { CampaignSmsFollowUpCardProps } from '~/types/CampaignSmsFollowUpCard'
import type { UseAuthReturn } from '~/types/Composables'
import type { SelectFieldOption } from '~/types/SelectField'
import { computed, ref, watch } from 'vue'
import { SmsService } from '~/services/smsService'
import { SmsVariables } from '~/utils/smsVariables'

const isEnabled: ModelRef<boolean> = defineModel<boolean>('isEnabled', { required: true })

const delayDays: ModelRef<number> = defineModel<number>('delayDays', { required: true })

const templateKey: ModelRef<string> = defineModel<string>('templateKey', { required: true })

const props: CampaignSmsFollowUpCardProps = defineProps({
  templates: {
    type: Array as PropType<SmsTemplate[]>,
    required: true,
  },
  campaignModule: {
    type: String as PropType<SmsTemplateModule>,
    required: true,
  },
  previewProspectId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  defaultDelayDays: {
    type: Number,
    required: true,
  },
})

const { user }: UseAuthReturn = useAuth()

const LOYALTY_CARD_LINK_VARIABLE: string = 'lien_carte'
const VIDEO_LINK_VARIABLE: string = 'lien_video'

const renderedPreview: Ref<SmsTemplatePreview | null> = ref(null)

const followUpTemplates: ComputedRef<SmsTemplate[]> = computed((): SmsTemplate[] =>
  props.templates.filter(
    (template: SmsTemplate): boolean =>
      template.module === props.campaignModule &&
      !template.recalls_an_email &&
      !template.variables.includes(LOYALTY_CARD_LINK_VARIABLE),
  ),
)

const templateOptions: ComputedRef<SelectFieldOption<string>[]> = computed((): SelectFieldOption<string>[] =>
  followUpTemplates.value.map(
    (template: SmsTemplate): SelectFieldOption<string> => ({ value: template.key, label: template.name }),
  ),
)

const selectedTemplate: ComputedRef<SmsTemplate | null> = computed(
  (): SmsTemplate | null =>
    followUpTemplates.value.find((template: SmsTemplate): boolean => template.key === templateKey.value) ?? null,
)

const isVideoFollowUp: ComputedRef<boolean> = computed(
  (): boolean => selectedTemplate.value?.variables.includes(VIDEO_LINK_VARIABLE) ?? false,
)

const previewText: ComputedRef<string> = computed((): string => {
  if (renderedPreview.value?.key === templateKey.value) return renderedPreview.value.body
  return SmsVariables.renderWithSampleValues(
    selectedTemplate.value?.body ?? '',
    SmsVariables.firstNameOf(user.value?.name),
  )
})

const previewSegments: ComputedRef<number | null> = computed((): number | null =>
  renderedPreview.value?.key === templateKey.value ? renderedPreview.value.segments : null,
)

/**
 * Turn the relance on with the user's usual delay and the first fitting template, or off.
 * @param shouldSend - Whether the campaign sends a relance.
 */
function toggleFollowUp(shouldSend: boolean): void {
  isEnabled.value = shouldSend
  if (!shouldSend) return
  if (!delayDays.value) delayDays.value = props.defaultDelayDays
  if (!selectedTemplate.value) templateKey.value = followUpTemplates.value[0]?.key ?? ''
}

/**
 * Render the chosen relance for the campaign's first prospect; the sample rendering stands in when that fails.
 * @returns A promise resolved once the preview is set.
 */
async function renderPreview(): Promise<void> {
  renderedPreview.value = null
  if (!isEnabled.value || !templateKey.value || props.previewProspectId === null) return
  renderedPreview.value = await SmsService.previewTemplate(templateKey.value, props.previewProspectId).catch(
    (): null => null,
  )
}

watch(
  [isEnabled, templateKey, (): number | null => props.previewProspectId],
  (): void => {
    renderPreview()
  },
  { immediate: true },
)
</script>
