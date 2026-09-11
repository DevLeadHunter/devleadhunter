<template>
  <div class="space-y-3">
    <div v-if="isLoading" class="flex justify-center py-4">
      <UIcon name="i-lucide-loader-circle" class="text-muted h-5 w-5 animate-spin" />
    </div>

    <p v-else-if="items.length === 0" class="text-sm text-[var(--app-faint)]">Aucun échange SMS pour le moment.</p>

    <ul v-else class="space-y-2">
      <li v-for="item in items" :key="`${item.kind}-${item.id}`" class="flex flex-col">
        <div
          :class="[
            'group max-w-[85%] rounded-xl px-3 py-2',
            item.kind === 'sent'
              ? 'self-end rounded-br-sm bg-[var(--app-ink)] text-[var(--app-surface)]'
              : 'self-start rounded-bl-sm border border-[var(--app-line)] bg-[var(--app-surface-2)] text-[var(--app-ink)]',
          ]"
        >
          <p class="text-sm [overflow-wrap:anywhere] break-words whitespace-pre-wrap">{{ item.body }}</p>
        </div>
        <div
          :class="[
            'mt-0.5 flex items-center gap-1.5 text-[10px] text-[var(--app-ink-soft)]',
            item.kind === 'sent' ? 'self-end' : 'self-start',
          ]"
        >
          <span>{{ formatCompactDateTime(item.at) }}</span>
          <span v-if="item.kind === 'sent' && item.status">
            · {{ SMS_STATUS_LABELS[item.status] ?? item.status }}
          </span>
          <span v-else-if="item.kind === 'received'">· reçu de {{ item.number }}</span>
          <button
            v-if="item.kind === 'received'"
            type="button"
            class="flex h-4 w-4 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)]"
            title="Supprimer cette réponse consignée (erreur de saisie)"
            @click="removeReply(item.id)"
          >
            <UIcon name="i-lucide-trash-2" class="h-3 w-3" />
          </button>
        </div>
      </li>
    </ul>

    <!-- Manual consignment: the sender is one-way, replies land on the operator's phone. -->
    <button v-if="!isFormOpen" type="button" class="btn-secondary h-8 w-full text-xs" @click="openForm">
      <UIcon name="i-lucide-message-square-reply" class="mr-1.5 h-3.5 w-3.5" />
      Consigner une réponse
    </button>

    <form
      v-else
      class="space-y-2 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3"
      @submit.prevent="submit"
    >
      <div>
        <label class="text-muted mb-1 block text-[10px] font-medium" :for="`sms-reply-number-${prospectId}`">
          Numéro du prospect
        </label>
        <input
          :id="`sms-reply-number-${prospectId}`"
          v-model="fromNumber"
          type="tel"
          class="input-field h-8 w-full text-sm"
          placeholder="06 12 34 56 78"
        />
        <p class="text-muted mt-1 text-[10px]">
          Pré-rempli, modifiable si le prospect a écrit depuis un autre numéro (il sera ajouté à sa fiche).
        </p>
      </div>
      <div>
        <label class="text-muted mb-1 block text-[10px] font-medium" :for="`sms-reply-body-${prospectId}`">
          Message reçu
        </label>
        <textarea
          :id="`sms-reply-body-${prospectId}`"
          v-model="body"
          rows="3"
          class="input-field w-full resize-none text-sm"
          placeholder="Le message tel que le prospect l'a envoyé…"
        ></textarea>
      </div>
      <div>
        <label class="text-muted mb-1 block text-[10px] font-medium" :for="`sms-reply-at-${prospectId}`">
          Reçu le
        </label>
        <input
          :id="`sms-reply-at-${prospectId}`"
          v-model="receivedAtLocal"
          type="datetime-local"
          class="input-field h-8 w-full text-sm"
        />
      </div>
      <div class="flex gap-2 pt-0.5">
        <button type="button" class="btn-secondary h-8 flex-1 text-xs" :disabled="isSubmitting" @click="closeForm">
          Annuler
        </button>
        <button type="submit" class="btn-primary h-8 flex-1 text-xs" :disabled="isSubmitting || !canSubmit">
          <UIcon v-if="isSubmitting" name="i-lucide-loader-circle" class="mr-1 h-3.5 w-3.5 animate-spin" />
          Consigner
        </button>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { SmsThread, SmsThreadItem } from '~/services/smsService'
import type { UiSmsConversationProps } from '~/types/UiSmsConversation'
import type { UseToastReturn } from '~/types/Composables'
import { SmsService } from '~/services/smsService'
import { SMS_STATUS_LABELS } from '~/constants/smsStatus'
import { formatCompactDateTime } from '~/utils/date'
import { useToast } from '~/composables/useToast'

const props: UiSmsConversationProps = defineProps({
  prospectId: {
    type: Number,
    required: true,
  },
  /** Number prefilled in the consignment form — the prospect's primary, or the SMS recipient. */
  defaultNumber: {
    type: String,
    default: '',
  },
})

const toast: UseToastReturn = useToast()

const items: Ref<SmsThreadItem[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const isFormOpen: Ref<boolean> = ref(false)
const isSubmitting: Ref<boolean> = ref(false)
const fromNumber: Ref<string> = ref('')
const body: Ref<string> = ref('')
const receivedAtLocal: Ref<string> = ref('')

/** Whether the consignment form holds enough to submit. */
const canSubmit: ComputedRef<boolean> = computed(
  (): boolean => fromNumber.value.trim().length > 0 && body.value.trim().length > 0,
)

/**
 * Format a date as the value of a datetime-local input (local time, minute precision).
 * @param date - The date to format.
 * @returns The `YYYY-MM-DDTHH:mm` local string.
 */
function toDatetimeLocalValue(date: Date): string {
  const pad: (n: number) => string = (n: number): string => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** Fetch the prospect's thread (sent SMS + consigned replies, oldest first). */
async function loadThread(): Promise<void> {
  isLoading.value = true
  try {
    const thread: SmsThread = await SmsService.getThread(props.prospectId)
    items.value = thread.items
  } catch {
    items.value = []
  } finally {
    isLoading.value = false
  }
}

/** Open the consignment form with the default number and the current time. */
function openForm(): void {
  fromNumber.value = props.defaultNumber
  body.value = ''
  receivedAtLocal.value = toDatetimeLocalValue(new Date())
  isFormOpen.value = true
}

/** Close the consignment form, discarding the draft. */
function closeForm(): void {
  isFormOpen.value = false
}

/**
 * Persist the consigned reply, then reload the thread.
 * @returns A promise resolved once consigned.
 */
async function submit(): Promise<void> {
  if (!canSubmit.value) return
  isSubmitting.value = true
  try {
    // The API stores naive-UTC datetimes: convert the local input before sending.
    const receivedAtUtc: string | null = receivedAtLocal.value
      ? new Date(receivedAtLocal.value).toISOString().slice(0, 19)
      : null
    await SmsService.createReply({
      prospect_id: props.prospectId,
      from_number: fromNumber.value.trim(),
      body: body.value.trim(),
      received_at: receivedAtUtc,
    })
    toast.success('Réponse consignée — relances en attente coupées')
    isFormOpen.value = false
    await loadThread()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Impossible de consigner la réponse')
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Delete one consigned reply (typo repair), then reload the thread.
 * @param replyId - The reply to delete.
 * @returns A promise resolved once deleted.
 */
async function removeReply(replyId: number): Promise<void> {
  try {
    await SmsService.deleteReply(replyId)
    await loadThread()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Suppression impossible')
  }
}

watch(
  (): number => props.prospectId,
  (): void => {
    isFormOpen.value = false
    void loadThread()
  },
)

onMounted((): void => {
  void loadThread()
})
</script>
