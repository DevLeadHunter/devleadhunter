<template>
  <div class="ml-6 rounded-xl border border-dashed border-[var(--app-ink-soft)]/40 bg-[var(--app-surface)] px-3 py-2.5">
    <div class="mb-1.5 flex flex-wrap items-center gap-2">
      <span class="text-[11px] font-medium text-[var(--app-ink)]">Moi</span>
      <span v-if="isFailed" class="app-badge app-badge--danger text-[10px]">
        <UIcon name="i-lucide-triangle-alert" class="h-2.5 w-2.5" />
        Pas parti
      </span>
      <span v-else-if="isSending" class="app-badge app-badge--progress text-[10px]">
        <UIcon name="i-lucide-loader-circle" class="h-2.5 w-2.5 animate-spin" />
        Envoi en cours
      </span>
      <span v-else class="app-badge app-badge--progress text-[10px]">
        <UIcon name="i-lucide-clock" class="h-2.5 w-2.5" />
        Programmé {{ scheduledLabel }}
      </span>
    </div>

    <p v-if="isFailed && props.item.scheduled_error" class="mb-1.5 text-[11px] text-[var(--app-red)]">
      {{ props.item.scheduled_error }}
    </p>
    <div
      v-if="props.item.has_newer_reply && !isEditing"
      class="mb-2 flex items-start gap-1.5 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] px-2.5 py-1.5"
    >
      <UIcon name="i-lucide-message-circle-warning" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-ink)]" />
      <p class="text-[11px] text-[var(--app-ink)]">
        Le prospect a répondu depuis que vous avez programmé ce message. Relisez-le avant qu'il parte.
      </p>
    </div>

    <template v-if="isEditing">
      <textarea
        v-model="draftText"
        rows="4"
        class="input-field w-full text-sm"
        aria-label="Texte du message programmé"
      ></textarea>
      <label class="text-muted mt-2 mb-1 block text-[11px] font-medium" :for="timeInputId">Envoi le</label>
      <input
        :id="timeInputId"
        v-model="draftTimeValue"
        type="datetime-local"
        :min="minimumValue"
        class="input-field h-9 w-full text-sm"
      />
      <div class="mt-2 flex justify-end gap-2">
        <button type="button" class="btn-secondary h-8 text-xs" :disabled="isWorking" @click="stopEditing">
          Annuler
        </button>
        <button
          type="button"
          class="btn-primary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!canSaveDraft || isWorking"
          @click="saveDraft"
        >
          Enregistrer
        </button>
      </div>
    </template>

    <template v-else>
      <!-- eslint-disable vue/no-v-html -- Our own HTML, written in the app -->
      <div
        class="overflow-hidden rounded-md border border-[var(--app-line)]/50 bg-white p-2 text-xs text-neutral-900 [&_p+p]:mt-2"
        v-html="props.item.body_html ?? ''"
      />
      <!-- eslint-enable vue/no-v-html -->
      <p class="text-muted mt-1 text-[10px]">Votre signature sera ajoutée à l'envoi.</p>

      <div v-if="!isSending" class="mt-2 flex flex-wrap items-center gap-1">
        <button
          type="button"
          class="inline-flex min-h-7 cursor-pointer items-center gap-1 rounded-lg px-2 text-[11px] font-medium text-[var(--app-ink-soft)] transition-colors enabled:hover:bg-[var(--app-surface-2)] enabled:hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="isWorking"
          @click="startEditing"
        >
          <UIcon name="i-lucide-pencil" class="h-3 w-3" />
          Modifier
        </button>
        <button
          type="button"
          class="inline-flex min-h-7 cursor-pointer items-center gap-1 rounded-lg px-2 text-[11px] font-medium text-[var(--app-ink-soft)] transition-colors enabled:hover:bg-[var(--app-surface-2)] enabled:hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="isWorking"
          @click="sendNow"
        >
          <UIcon name="i-lucide-send" class="h-3 w-3" />
          Envoyer maintenant
        </button>
        <button
          type="button"
          :class="[
            'ml-auto inline-flex min-h-7 cursor-pointer items-center gap-1 rounded-lg px-2 text-[11px] font-medium text-[var(--app-ink-soft)] transition-colors enabled:hover:bg-[var(--app-surface-2)] enabled:hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50',
            isConfirmingCancel && 'text-[var(--app-red)] enabled:hover:text-[var(--app-red)]',
          ]"
          :disabled="isWorking"
          @click="cancel"
        >
          <UIcon name="i-lucide-x" class="h-3 w-3" />
          {{ isConfirmingCancel ? "Confirmer l'annulation" : 'Annuler' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { ConversationItem, EmailResendResult } from '~/types'
import type { UiScheduledReplyCardEmits, UiScheduledReplyCardProps } from '~/types/UiScheduledReplyCard'
import type { UseToastReturn } from '~/types/Composables'
import { EmailLogsService } from '~/services/emailLogsService'
import { formatScheduledMoment, parseApiDate, parseFutureDatetimeLocalValue, toDatetimeLocalValue } from '~/utils/date'
import { ReplyBodyFormat } from '~/utils/replyBodyFormat'
import { useToast } from '~/composables/useToast'

const props: UiScheduledReplyCardProps = defineProps({
  item: {
    type: Object as PropType<ConversationItem>,
    required: true,
  },
})

const emit: EmitFn<UiScheduledReplyCardEmits> = defineEmits<UiScheduledReplyCardEmits>()

const toast: UseToastReturn = useToast()
const timeInputId: string = useId()

const isEditing: Ref<boolean> = ref(false)
const isWorking: Ref<boolean> = ref(false)
const isConfirmingCancel: Ref<boolean> = ref(false)
const draftText: Ref<string> = ref('')
const draftTimeValue: Ref<string> = ref('')
const minimumValue: Ref<string> = ref('')

const isFailed: ComputedRef<boolean> = computed((): boolean => props.item.scheduled_status === 'failed')
const isSending: ComputedRef<boolean> = computed((): boolean => props.item.scheduled_status === 'sending')

const scheduledLabel: ComputedRef<string> = computed((): string =>
  props.item.scheduled_at ? formatScheduledMoment(parseApiDate(props.item.scheduled_at)) : '',
)

const draftMoment: ComputedRef<Date | null> = computed((): Date | null =>
  parseFutureDatetimeLocalValue(draftTimeValue.value),
)

const canSaveDraft: ComputedRef<boolean> = computed(
  (): boolean => draftText.value.trim().length > 0 && draftMoment.value !== null,
)

/** Open the inline editor prefilled with the planned text and time (a past time is left for the user to fix). */
function startEditing(): void {
  draftText.value = ReplyBodyFormat.toText(props.item.body_html ?? '')
  const planned: Date | null = props.item.scheduled_at ? parseApiDate(props.item.scheduled_at) : null
  draftTimeValue.value = planned && planned.getTime() > Date.now() ? toDatetimeLocalValue(planned) : ''
  minimumValue.value = toDatetimeLocalValue(new Date())
  isConfirmingCancel.value = false
  isEditing.value = true
}

/** Close the inline editor without saving. */
function stopEditing(): void {
  isEditing.value = false
}

/**
 * Run a scheduled-email action, then ask the thread to reload.
 * @param action - The API call.
 * @param successMessage - Toast shown on success.
 * @returns A promise resolved once done.
 */
async function runAction(action: () => Promise<unknown>, successMessage: string): Promise<void> {
  isWorking.value = true
  try {
    await action()
    toast.success(successMessage)
    isEditing.value = false
  } catch (error: unknown) {
    toast.error(error instanceof Error && error.message ? error.message : 'Action impossible')
  } finally {
    isWorking.value = false
    isConfirmingCancel.value = false
    // A failed send-now still changed the row (now « Pas parti »): the thread must show it.
    emit('changed')
  }
}

/** Save the edited text and time. */
async function saveDraft(): Promise<void> {
  const scheduledId: number | null | undefined = props.item.scheduled_id
  const moment: Date | null = draftMoment.value
  if (!scheduledId || !moment || !canSaveDraft.value) return
  await runAction(
    (): Promise<unknown> =>
      EmailLogsService.updateScheduled(scheduledId, {
        bodyHtml: ReplyBodyFormat.toHtml(draftText.value),
        scheduledAt: moment,
      }),
    `Envoi programmé ${formatScheduledMoment(moment)}`,
  )
}

/** Send the planned message right away. */
async function sendNow(): Promise<void> {
  const scheduledId: number | null | undefined = props.item.scheduled_id
  if (!scheduledId) return
  await runAction(async (): Promise<void> => {
    const result: EmailResendResult = await EmailLogsService.sendScheduledNow(scheduledId)
    if (!result.success) throw new Error(result.error || "Échec de l'envoi")
  }, 'Réponse envoyée')
}

/** Cancel the planned message; the first click asks for confirmation. */
async function cancel(): Promise<void> {
  const scheduledId: number | null | undefined = props.item.scheduled_id
  if (!scheduledId) return
  if (!isConfirmingCancel.value) {
    isConfirmingCancel.value = true
    return
  }
  await runAction((): Promise<void> => EmailLogsService.cancelScheduled(scheduledId), 'Envoi programmé annulé')
}
</script>
