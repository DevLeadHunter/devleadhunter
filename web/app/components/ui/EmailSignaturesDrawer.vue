<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[560px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- Header -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="view === 'editor' || showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            :title="view === 'editor' ? 'Revenir à la liste' : 'Revenir au volet précédent'"
            @click="handleBack"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-signature" class="h-5 w-5 text-[var(--app-ink-soft)]" />
          </div>

          <div class="min-w-0 flex-1">
            <h2 class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">{{ drawerTitle }}</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              Signatures réutilisables sur vos modèles et emails
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-5 py-4">
          <!-- LIST VIEW -->
          <template v-if="view === 'list'">
            <div v-if="isLoading" class="flex items-center justify-center py-16">
              <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-faint)]" />
            </div>

            <div v-else-if="signatures.length === 0" class="card px-6 py-12 text-center">
              <UIcon name="i-lucide-signature" class="mx-auto h-8 w-8 text-[var(--app-faint)]" />
              <h3 class="mt-4 text-sm font-semibold text-[var(--app-ink)]">Aucune signature</h3>
              <p class="text-muted mx-auto mt-1 max-w-xs text-xs leading-relaxed">
                Créez une signature à ajouter au bas de vos emails (importez celle de Gmail en la collant).
              </p>
            </div>

            <div v-else class="space-y-2.5">
              <div v-for="signature in signatures" :key="signature.id" class="card p-3.5">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex min-w-0 items-center gap-2">
                    <h3 class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ signature.name }}</h3>
                    <span v-if="signature.is_default" class="app-badge">Par défaut</span>
                  </div>
                  <div class="flex shrink-0 items-center gap-1.5">
                    <button
                      v-if="!signature.is_default"
                      class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
                      title="Définir par défaut"
                      @click="setAsDefault(signature)"
                    >
                      <UIcon name="i-lucide-star" class="h-3.5 w-3.5" />
                    </button>
                    <button
                      class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
                      title="Modifier"
                      @click="openEditor(signature)"
                    >
                      <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
                    </button>
                    <button
                      class="btn-danger flex h-8 min-h-8 items-center justify-center px-2.5 text-xs"
                      title="Supprimer"
                      @click="confirmDelete(signature)"
                    >
                      <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <!-- eslint-disable vue/no-v-html -- Preview of the user's own signature HTML -->
                <div
                  class="mt-2.5 max-h-24 overflow-hidden rounded-md border border-[var(--app-line)] bg-white p-2.5 text-xs text-neutral-900"
                  v-html="signature.content_html"
                ></div>
                <!-- eslint-enable vue/no-v-html -->
              </div>
            </div>
          </template>

          <!-- EDITOR VIEW -->
          <form v-else id="signature-form" class="space-y-4" @submit.prevent="handleSave">
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">
                Nom de la signature <span class="text-[var(--app-red)]">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                required
                class="input-field"
                placeholder="Ex : Signature Dibodev"
              />
            </div>

            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">Contenu de la signature</label>
              <UiRichSignatureEditor v-model="form.content_html" />
            </div>

            <div class="flex items-center justify-between rounded-lg border border-[var(--app-line)] px-3 py-2.5">
              <div>
                <p class="text-sm font-medium text-[var(--app-ink)]">Signature par défaut</p>
                <p class="text-muted text-xs">Pré-sélectionnée sur vos nouveaux modèles.</p>
              </div>
              <UiSwitch id="signature-default" v-model="form.is_default" />
            </div>
          </form>
        </div>

        <!-- Footer -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <template v-if="view === 'list'">
            <button type="button" class="btn-secondary flex-1" @click="emit('close')">Fermer</button>
            <button type="button" class="btn-primary flex-1" @click="openEditor(null)">
              <UIcon name="i-lucide-plus" class="mr-1.5 h-4 w-4" />
              Nouvelle signature
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="view = 'list'">
              Annuler
            </button>
            <button
              type="submit"
              form="signature-form"
              class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isSaving"
            >
              <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
              {{ isSaving ? 'Enregistrement…' : 'Enregistrer' }}
            </button>
          </template>
        </div>
      </div>
    </Transition>

    <UiConfirmModal
      ref="confirmModal"
      title="Supprimer la signature"
      :message="`Supprimer la signature « ${signatureToDelete?.name} » ? Elle sera retirée des modèles qui l'utilisent.`"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDelete"
    />
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { EmailSignature } from '~/types'
import { computed, ref, watch } from 'vue'
import {
  getEmailSignatures,
  createEmailSignature,
  updateEmailSignature,
  deleteEmailSignature,
} from '~/services/emailSignaturesService'
import { useToast } from '~/composables/useToast'

/** Internal view of the drawer (list of signatures vs single-signature editor). */
type SignaturesDrawerView = 'list' | 'editor'

/** Local shape of the signature editor form. */
interface SignatureForm {
  name: string
  content_html: string
  is_default: boolean
}

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
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
}>()

const toast = useToast()

/** Current internal view. */
const view: Ref<SignaturesDrawerView> = ref<SignaturesDrawerView>('list')

/** Loaded signatures. */
const signatures: Ref<EmailSignature[]> = ref<EmailSignature[]>([])

/** Whether the list is loading. */
const isLoading: Ref<boolean> = ref<boolean>(false)

/** Whether a save request is in flight. */
const isSaving: Ref<boolean> = ref<boolean>(false)

/** Signature currently edited (null when creating a new one). */
const editingSignature: Ref<EmailSignature | null> = ref<EmailSignature | null>(null)

/** Editor form state. */
const form: Ref<SignatureForm> = ref<SignatureForm>({ name: '', content_html: '', is_default: false })

/** Signature pending deletion. */
const signatureToDelete: Ref<EmailSignature | null> = ref<EmailSignature | null>(null)

/** Confirm modal handle. */
const confirmModal: Ref<{ open: () => void; close: () => void } | null> = ref<{
  open: () => void
  close: () => void
} | null>(null)

/** Drawer title matching the current view. */
const drawerTitle: ComputedRef<string> = computed((): string => {
  if (view.value === 'list') return 'Mes signatures'
  return editingSignature.value ? 'Modifier la signature' : 'Nouvelle signature'
})

/**
 * Load every signature of the current user.
 * @returns A promise that resolves once loaded.
 */
async function loadSignatures(): Promise<void> {
  isLoading.value = true
  try {
    signatures.value = await getEmailSignatures()
  } catch {
    // Non-blocking: fall back to the empty state rather than a scary toast.
    signatures.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * Open the editor for a signature (or a blank one).
 * @param signature - Signature to edit, or null to create.
 */
function openEditor(signature: EmailSignature | null): void {
  editingSignature.value = signature
  form.value = {
    name: signature?.name ?? '',
    content_html: signature?.content_html ?? '',
    is_default: signature?.is_default ?? signatures.value.length === 0,
  }
  view.value = 'editor'
}

/**
 * Header back button — returns to the list from the editor, else pops the stack.
 */
function handleBack(): void {
  if (view.value === 'editor') {
    view.value = 'list'
    return
  }
  emit('back')
}

/**
 * Create or update the edited signature.
 * @returns A promise that resolves once persisted.
 */
async function handleSave(): Promise<void> {
  isSaving.value = true
  try {
    if (editingSignature.value) {
      await updateEmailSignature(editingSignature.value.id, {
        name: form.value.name,
        content_html: form.value.content_html,
        is_default: form.value.is_default,
      })
      toast.success('Signature mise à jour')
    } else {
      await createEmailSignature({
        name: form.value.name,
        content_html: form.value.content_html,
        is_default: form.value.is_default,
      })
      toast.success('Signature créée')
    }
    await loadSignatures()
    view.value = 'list'
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enregistrement")
  } finally {
    isSaving.value = false
  }
}

/**
 * Mark a signature as the default one.
 * @param signature - Signature to promote.
 */
async function setAsDefault(signature: EmailSignature): Promise<void> {
  try {
    await updateEmailSignature(signature.id, { is_default: true })
    await loadSignatures()
    toast.success(`« ${signature.name} » définie par défaut`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  }
}

/**
 * Ask for confirmation before deleting a signature.
 * @param signature - Signature to delete.
 */
function confirmDelete(signature: EmailSignature): void {
  signatureToDelete.value = signature
  confirmModal.value?.open()
}

/**
 * Delete the pending signature after confirmation.
 * @returns A promise that resolves once removed.
 */
async function handleDelete(): Promise<void> {
  const signature: EmailSignature | null = signatureToDelete.value
  if (!signature) return
  try {
    await deleteEmailSignature(signature.id)
    await loadSignatures()
    toast.success(`Signature « ${signature.name} » supprimée`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    signatureToDelete.value = null
  }
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (!open) return
    view.value = 'list'
    void loadSignatures()
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
