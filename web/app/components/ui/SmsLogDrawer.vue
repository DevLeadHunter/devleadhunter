<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && sms"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
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
            <h2 class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ sms.recipient_name || sms.to_e164 }}
            </h2>
            <p class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">{{ sms.to_e164 }}</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <div class="flex items-center gap-2">
            <span :class="['app-badge', SMS_STATUS_BADGE_CLASS[sms.status] ?? '']">
              {{ SMS_STATUS_LABELS[sms.status] ?? sms.status }}
            </span>
            <span v-if="sms.status_detail" class="text-xs text-[var(--app-ink-soft)]">{{ sms.status_detail }}</span>
          </div>

          <div
            v-if="sms.status === 'failed'"
            class="rounded-lg border border-[var(--app-red)]/30 bg-[var(--app-red-soft)] p-3 text-xs text-[var(--app-ink)]"
          >
            <p class="font-semibold text-[var(--app-red)]">SMS non délivré</p>
            <p class="mt-1 [overflow-wrap:anywhere] break-words">{{ sms.status_detail || sms.error || '—' }}</p>
          </div>

          <div>
            <p class="app-label mb-1.5 !text-[0.6rem]">Message</p>
            <div
              class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3 text-sm [overflow-wrap:anywhere] break-words whitespace-pre-wrap text-[var(--app-ink)]"
            >
              {{ sms.body }}
            </div>
          </div>

          <dl class="divide-y divide-[var(--app-line-soft)] text-sm">
            <div class="flex items-center justify-between gap-3 py-2">
              <dt class="text-[var(--app-ink-soft)]">Expéditeur</dt>
              <dd class="font-medium text-[var(--app-ink)]">{{ sms.sender }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3 py-2">
              <dt class="text-[var(--app-ink-soft)]">Segments</dt>
              <dd class="text-[var(--app-ink)] tabular-nums">{{ sms.segments }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3 py-2">
              <dt class="text-[var(--app-ink-soft)]">Coût</dt>
              <dd class="text-[var(--app-ink)] tabular-nums">{{ formatEuros(sms.price_cents) }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3 py-2">
              <dt class="text-[var(--app-ink-soft)]">Envoyé le</dt>
              <dd class="text-[var(--app-ink)]">{{ formatDateTime(sms.created_at) }}</dd>
            </div>
            <div v-if="sms.delivered_at" class="flex items-center justify-between gap-3 py-2">
              <dt class="text-[var(--app-ink-soft)]">Délivré le</dt>
              <dd class="text-[var(--app-ink)]">{{ formatDateTime(sms.delivered_at) }}</dd>
            </div>
            <div class="flex items-center justify-between gap-3 py-2">
              <dt class="text-[var(--app-ink-soft)]">Référence</dt>
              <dd class="font-label text-xs text-[var(--app-ink-soft)]">dlh-{{ sms.id }}</dd>
            </div>
          </dl>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <button class="btn-secondary w-full" @click="emit('resend', sms)">
            <UIcon name="i-lucide-send" class="mr-1.5 h-4 w-4" />
            Renvoyer un SMS
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UiSmsLogDrawerEmits, UiSmsLogDrawerProps } from '~/types/UiSmsLogDrawer'
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { SmsMessage } from '~/services/smsService'
import { computed } from 'vue'
import { SMS_STATUS_BADGE_CLASS, SMS_STATUS_LABELS } from '~/constants/smsStatus'
import { formatEuros } from '~/utils/currency'
import { parseApiDate } from '~/utils/date'

const props: UiSmsLogDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  message: {
    type: Object as PropType<SmsMessage | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiSmsLogDrawerEmits> = defineEmits<UiSmsLogDrawerEmits>()

/** The SMS to display (null while the drawer is closed or empty). */
const sms: ComputedRef<SmsMessage | null> = computed((): SmsMessage | null => props.message ?? null)

/**
 * Format an ISO timestamp to a full French date-time.
 * @param iso - The ISO timestamp.
 * @returns The formatted date-time.
 */
function formatDateTime(iso: string): string {
  return parseApiDate(iso).toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
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
