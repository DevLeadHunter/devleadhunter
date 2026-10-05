<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && log"
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

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Renvoyer l'e-mail</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">{{ log.subject }}</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-5">
          <label
            for="resend-email"
            class="mb-1.5 block text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase"
          >
            Adresse e-mail
          </label>
          <input
            id="resend-email"
            v-model="resendEmail"
            type="email"
            class="input-field w-full"
            placeholder="adresse@exemple.fr"
            @keydown.enter="submitResend"
          />
          <p class="text-muted mt-2 text-[11px]">
            Réenvoie le même e-mail (sujet et contenu). Une adresse différente est enregistrée sur le prospect.
          </p>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <button class="btn-primary w-full" :disabled="resending || !resendEmail.trim()" @click="submitResend">
            <UIcon v-if="resending" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            <template v-else>
              <UIcon name="i-lucide-send" class="mr-1.5 h-4 w-4" />
              Renvoyer
            </template>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType, Ref } from 'vue'
import type { EmailLog, EmailResendResult, Prospect } from '~/types'
import type { EmailResendDrawerProps } from '~/types/EmailResendDrawer'
import type { UiEmailResendDrawerEmits } from '~/types/UiEmailResendDrawer'
import type { UseToastReturn } from '~/types/Composables'
import { EmailLogsService } from '~/services/emailLogsService'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

/** Sub-drawer that re-sends a failed email, letting the operator correct the address first. */
const props: EmailResendDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  log: {
    type: Object as PropType<EmailLog | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiEmailResendDrawerEmits> = defineEmits<UiEmailResendDrawerEmits>()

const toast: UseToastReturn = useToast()
const resendEmail: Ref<string> = ref('')
const resending: Ref<boolean> = ref(false)

/**
 * Re-send the log's email to the address in the field, then refresh the list on success.
 * @returns Promise resolved once the send attempt completes.
 */
async function submitResend(): Promise<void> {
  if (!props.log || resending.value) return
  const email: string = resendEmail.value.trim()
  if (!email) return
  resending.value = true
  try {
    const result: EmailResendResult = await EmailLogsService.resendEmailLog(props.log.id, email)
    if (result.success) {
      toast.success('E-mail renvoyé')
      emit('resent')
    } else {
      toast.error(result.error ?? "Échec du renvoi de l'e-mail")
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec du renvoi de l'e-mail")
  } finally {
    resending.value = false
  }
}

watch(
  (): [boolean, number | undefined] => [props.open, props.log?.id],
  async ([isOpen]: [boolean, number | undefined]): Promise<void> => {
    const log: EmailLog | null = props.log
    if (!isOpen || !log) return
    resendEmail.value = log.recipient_email
    if (!log.prospect_id) return
    try {
      const prospect: Prospect = await ProspectsService.getProspect(Number(log.prospect_id))
      resendEmail.value = prospect.email ?? log.recipient_email
    } catch {
      resendEmail.value = log.recipient_email
    }
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
