<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="props.open && props.campaignId !== null"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="campaign-reply-title"
      >
        <UiDrawerHeader
          title="Ajouter une réponse"
          subtitle="Reçue par téléphone ou dans une autre boîte"
          icon="i-lucide-message-square-plus"
          :show-back="props.showBack"
          title-id="campaign-reply-title"
          @back="emit('back')"
          @close="emit('close')"
        />

        <form
          id="campaign-reply-form"
          class="flex flex-1 flex-col gap-5 overflow-y-auto px-5 py-5"
          @submit.prevent="save"
        >
          <div class="flex flex-col gap-1.5">
            <span class="app-label">Prospect</span>
            <UiSelectField
              v-model="prospectId"
              :options="props.prospects"
              placeholder="Choisir le prospect…"
              aria-label="Prospect"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <span class="app-label">Sa réponse</span>
            <UiSegmentedControl v-model="verdict" :options="VERDICT_OPTIONS" label="Sa réponse" class="self-start" />
          </div>

          <label class="flex flex-col gap-1.5">
            <span class="app-label">Reçue le</span>
            <input v-model="receivedAt" type="datetime-local" :max="latestAllowedMoment" class="app-input" />
          </label>

          <label class="flex flex-col gap-1.5">
            <span class="app-label">Ce qu'il a écrit ou dit</span>
            <textarea
              v-model="message"
              class="app-input min-h-28 resize-y py-2"
              maxlength="5000"
              placeholder="Collez sa réponse, ou résumez l'appel."
            ></textarea>
          </label>

          <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
            La réponse compte dans les résultats de la campagne et arrête les relances encore prévues pour ce prospect.
          </p>
        </form>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <p v-if="errorMessage" class="mb-3 text-xs text-[var(--app-red)]" role="alert">{{ errorMessage }}</p>
          <div class="flex flex-col gap-2 sm:flex-row">
            <button type="button" class="app-btn-secondary w-full sm:flex-1" @click="emit('close')">Annuler</button>
            <button
              type="submit"
              form="campaign-reply-form"
              class="app-btn-primary w-full sm:flex-1"
              :disabled="isSaving || prospectId === 0"
            >
              <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              {{ isSaving ? 'Ajout…' : 'Ajouter la réponse' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType, Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type { CampaignResultsReplyVerdict } from '~/types/CampaignResults'
import type { SelectFieldOption } from '~/types/SelectField'
import type { UiCampaignReplyDrawerEmits, UiCampaignReplyDrawerProps } from '~/types/UiCampaignReplyDrawer'
import { ref, watch } from 'vue'
import { useToast } from '~/composables/useToast'
import { CampaignService } from '~/services/campaignService'
import { toDatetimeLocalValue } from '~/utils/date'

const props: UiCampaignReplyDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  campaignId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  prospects: {
    type: Array as PropType<SelectFieldOption<number>[]>,
    required: true,
  },
})

const emit: EmitFn<UiCampaignReplyDrawerEmits> = defineEmits<UiCampaignReplyDrawerEmits>()

const toast: UseToastReturn = useToast()

const VERDICT_OPTIONS: SelectFieldOption<CampaignResultsReplyVerdict>[] = [
  { value: 'interested', label: 'Intéressé' },
  { value: 'refused', label: 'Refus' },
  { value: 'other', label: 'Autre' },
]

const prospectId: Ref<number> = ref(0)
const verdict: Ref<CampaignResultsReplyVerdict> = ref('interested')
const receivedAt: Ref<string> = ref('')
const message: Ref<string> = ref('')
const latestAllowedMoment: Ref<string> = ref('')
const isSaving: Ref<boolean> = ref(false)
const errorMessage: Ref<string> = ref('')

/**
 * Record the reply on the campaign, then let the results reload.
 * @returns A promise resolved once the reply is saved or refused.
 */
async function save(): Promise<void> {
  if (props.campaignId === null || prospectId.value === 0 || isSaving.value) return
  const receivedMoment: Date | null = receivedAt.value ? new Date(receivedAt.value) : null
  if (receivedMoment && receivedMoment.getTime() > Date.now()) {
    errorMessage.value = 'La date de la réponse ne peut pas être dans le futur.'
    return
  }
  isSaving.value = true
  errorMessage.value = ''
  try {
    await CampaignService.addManualReply(props.campaignId, {
      prospect_id: prospectId.value,
      verdict: verdict.value,
      received_at: receivedMoment ? receivedMoment.toISOString() : null,
      message: message.value.trim(),
    })
    toast.success('Réponse ajoutée')
    emit('saved')
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : "La réponse n'a pas pu être ajoutée."
  } finally {
    isSaving.value = false
  }
}

watch(
  (): [boolean, number | null] => [props.open, props.campaignId],
  ([isOpen]: [boolean, number | null]): void => {
    if (!isOpen) return
    const nowValue: string = toDatetimeLocalValue(new Date())
    prospectId.value = 0
    verdict.value = 'interested'
    receivedAt.value = nowValue
    latestAllowedMoment.value = nowValue
    message.value = ''
    errorMessage.value = ''
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
