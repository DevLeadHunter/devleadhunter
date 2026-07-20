<template>
  <Teleport to="body">
    <!-- Pas de backdrop : le drawer est non-modal pour laisser la navigation
         (sidebar, pages) cliquable pendant qu'il est ouvert. -->
    <!-- Slide-over panel -->
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

          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-accent-soft)]"
          >
            <UIcon name="i-lucide-send" class="h-5 w-5 text-[var(--app-accent-ink)]" />
          </div>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Envoyer un email</h2>
            <p v-if="form.recipient_email" class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              À {{ form.recipient_name || form.recipient_email }}
            </p>
            <p v-else class="mt-0.5 text-[11px] text-[var(--app-ink-soft)]">Envoi manuel via votre compte Resend</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <form id="send-email-form" class="flex-1 space-y-4 overflow-y-auto px-5 py-4" @submit.prevent="handleSend">
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Email destinataire <span class="text-[var(--app-red)]">*</span>
            </label>
            <input
              v-model="form.recipient_email"
              type="email"
              required
              class="input-field"
              placeholder="prospect@exemple.fr"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Nom destinataire</label>
            <input v-model="form.recipient_name" type="text" class="input-field" placeholder="Jean Dupont" />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Sujet <span class="text-[var(--app-red)]">*</span>
            </label>
            <input v-model="form.subject" type="text" required class="input-field" placeholder="Votre site démo" />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Message <span class="text-[var(--app-red)]">*</span>
            </label>
            <textarea
              v-model="form.body"
              required
              rows="12"
              class="input-field resize-none"
              placeholder="Bonjour,&#10;&#10;J'ai créé un site vitrine pour votre entreprise…"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Signature</label>
            <select v-model="signatureId" class="input-field">
              <option :value="null">Aucune signature</option>
              <option v-for="signature in signatures" :key="signature.id" :value="signature.id">
                {{ signature.name }}{{ signature.is_default ? ' (par défaut)' : '' }}
              </option>
            </select>
            <button
              type="button"
              class="mt-1.5 text-xs font-medium text-[var(--app-ink-soft)] underline decoration-[var(--app-line)] underline-offset-2 hover:text-[var(--app-ink)]"
              @click="openSignaturesDrawer"
            >
              Gérer mes signatures
            </button>
          </div>
        </form>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSending" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="send-email-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSending"
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
import type { PropType, Ref } from 'vue'
import type { EmailSignature, Prospect } from '~/types'
import type { SendEmailPrefill } from '~/types/DrawerStack'
import { ref, watch } from 'vue'
import { api } from '~/services/api'
import { getEmailSignatures } from '~/services/emailSignaturesService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

/** Local shape of the manual send form. */
interface SendEmailForm {
  recipient_email: string
  recipient_name: string
  subject: string
  body: string
}

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospect: {
    type: Object as PropType<Prospect | null>,
    default: null,
  },
  prefill: {
    type: Object as PropType<SendEmailPrefill | null>,
    default: null,
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
  /** The email was successfully dispatched. */
  sent: []
}>()

const toast = useToast()

/** Persistent drawer stack (to stack the signatures manager on top). */
const drawerStack = useDrawerStackStore()

/** Whether the quick-send request is in flight. */
const isSending: Ref<boolean> = ref<boolean>(false)

/** The user's signatures (for the optional selector). */
const signatures: Ref<EmailSignature[]> = ref<EmailSignature[]>([])

/** Selected signature id (null = none). */
const signatureId: Ref<number | null> = ref<number | null>(null)

/** Key of the recipient the form was last initialised for. */
const lastInitKey: Ref<string> = ref<string>('')

/** Manual send form state. */
const form: Ref<SendEmailForm> = ref<SendEmailForm>({
  recipient_email: '',
  recipient_name: '',
  subject: '',
  body: '',
})

/**
 * Load the user's signatures and default the selection to the default one.
 * @returns A promise that resolves once loaded.
 */
async function loadSignatures(): Promise<void> {
  try {
    signatures.value = await getEmailSignatures()
  } catch {
    signatures.value = []
  }
  const stillValid: boolean = signatures.value.some((s: EmailSignature): boolean => s.id === signatureId.value)
  if (!stillValid) {
    const preferred: EmailSignature | undefined =
      signatures.value.find((s: EmailSignature): boolean => s.is_default) ?? signatures.value[0]
    signatureId.value = preferred?.id ?? null
  }
}

/** Stack the signatures manager on top of this drawer. */
function openSignaturesDrawer(): void {
  drawerStack.push({ kind: 'email-signatures' })
}

/**
 * Send the email through the quick-send endpoint (uses the user's Resend
 * configuration), then notify the host so the stack can navigate back.
 * @returns A promise that resolves once the email has been dispatched.
 */
async function handleSend(): Promise<void> {
  isSending.value = true
  try {
    await api.post('/api/v1/emails/quick-send', {
      recipient_email: form.value.recipient_email,
      recipient_name: form.value.recipient_name || undefined,
      subject: form.value.subject,
      body_html: `<p>${form.value.body.replace(/\n/g, '<br>')}</p>`,
      signature_id: signatureId.value ?? undefined,
    })
    toast.success('Email envoyé avec succès')
    emit('sent')
  } catch {
    toast.error("Erreur lors de l'envoi — vérifiez votre configuration Resend dans les Paramètres")
  } finally {
    isSending.value = false
  }
}

watch(
  (): [boolean, number | undefined, SendEmailPrefill | null] => [props.open, props.prospect?.id, props.prefill],
  ([open]: [boolean, number | undefined, SendEmailPrefill | null]): void => {
    if (!open) return
    // Refresh signatures every time the composer is shown (e.g. after managing them).
    void loadSignatures()
    // Only (re)initialise the form when the recipient changes — returning from
    // the stacked signatures drawer must NOT wipe a message being written.
    const key: string = props.prefill
      ? `prefill:${props.prefill.recipient_email}|${props.prefill.subject}`
      : `prospect:${props.prospect?.id ?? 'blank'}`
    if (key === lastInitKey.value) return
    lastInitKey.value = key
    if (props.prefill) {
      form.value = { ...props.prefill }
      return
    }
    form.value = {
      recipient_email: props.prospect?.email ?? '',
      recipient_name: props.prospect?.name ?? '',
      subject: '',
      body: '',
    }
  },
  { immediate: true },
)
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
