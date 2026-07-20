<template>
  <Teleport to="body">
    <!-- Pas de backdrop : le drawer est non-modal pour laisser la navigation
         (sidebar, pages) cliquable pendant qu'il est ouvert. -->
    <!-- Slide-over panel -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[560px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
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
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon
              :name="mode === 'preview' ? 'i-lucide-eye' : 'i-lucide-layout-template'"
              class="h-5 w-5 text-[var(--app-ink-soft)]"
            />
          </div>

          <div class="min-w-0 flex-1">
            <h2 class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">{{ drawerTitle }}</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              {{ mode === 'preview' ? 'Rendu avec des données d’exemple' : 'Modèle pour vos emails de prospection' }}
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->

        <!-- PREVIEW MODE -->
        <div v-if="mode === 'preview'" class="flex-1 overflow-y-auto px-5 py-4">
          <div v-if="isPreviewLoading" class="flex items-center justify-center py-16">
            <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-faint)]" />
          </div>
          <!-- L'email s'affiche sur fond blanc, comme dans un client mail. -->
          <div v-else class="rounded-lg border border-[var(--app-line)] bg-white p-6">
            <div class="mb-4 border-b border-neutral-200 pb-4">
              <p class="text-xs text-neutral-500">Sujet :</p>
              <p class="text-sm font-medium text-neutral-900">{{ previewSubject }}</p>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -- Preview of user's own email template HTML -->
            <div class="prose max-w-none text-sm text-neutral-900" v-html="previewHtml"></div>
          </div>
        </div>

        <!-- CREATE / EDIT MODE -->
        <form
          v-else
          id="email-template-form"
          class="flex-1 space-y-4 overflow-y-auto px-5 py-4"
          @submit.prevent="handleSave"
        >
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Nom du modèle <span class="text-[var(--app-red)]">*</span>
            </label>
            <input
              v-model="form.name"
              type="text"
              required
              class="input-field"
              placeholder="Ex : Proposition de site web"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Sujet de l'email <span class="text-[var(--app-red)]">*</span>
            </label>
            <input
              ref="subjectRef"
              v-model="form.subject"
              type="text"
              required
              class="input-field"
              placeholder="Ex : Création de site web pour {entreprise}"
              @input="subjectInsertion.onInput"
              @keydown="subjectInsertion.onKeydown"
              @blur="subjectInsertion.onBlur"
            />
            <p class="text-muted mt-1.5 mb-1.5 text-xs">
              Cliquez une variable pour l'insérer, ou tapez «&nbsp;{&nbsp;».
            </p>
            <UiVariableChips @insert="subjectInsertion.insertToken" />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Corps de l'email (HTML) <span class="text-[var(--app-red)]">*</span>
            </label>
            <textarea
              ref="bodyRef"
              v-model="form.body_html"
              required
              rows="14"
              class="input-field font-mono text-xs"
              placeholder="Bonjour {salutation},&#10;&#10;Je me présente..."
              @input="bodyInsertion.onInput"
              @keydown="bodyInsertion.onKeydown"
              @blur="bodyInsertion.onBlur"
            ></textarea>
            <p class="text-muted mt-1.5 mb-1.5 text-xs">Insérez une variable à l'endroit du curseur :</p>
            <UiVariableChips @insert="bodyInsertion.insertToken" />
          </div>

          <!-- Signature -->
          <div class="rounded-lg border border-[var(--app-line)] px-3 py-2.5">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-sm font-medium text-[var(--app-ink)]">Inclure une signature</p>
                <p class="text-muted text-xs">Ajoutée automatiquement au bas de l'email envoyé.</p>
              </div>
              <UiSwitch
                id="template-include-signature"
                v-model="includeSignature"
                :disabled="signatures.length === 0"
              />
            </div>

            <!-- Selector (switch on + at least one signature) -->
            <div v-if="includeSignature && signatures.length" class="mt-3">
              <select v-model="form.signature_id" class="input-field">
                <option v-for="signature in signatures" :key="signature.id" :value="signature.id">
                  {{ signature.name }}{{ signature.is_default ? ' (par défaut)' : '' }}
                </option>
              </select>
            </div>

            <!-- Empty-state invite -->
            <div
              v-if="signatures.length === 0"
              class="mt-3 rounded-md border border-dashed border-[var(--app-line)] px-3 py-2.5 text-center"
            >
              <p class="text-muted text-xs">Vous n'avez pas encore de signature.</p>
              <button type="button" class="btn-secondary mt-2 h-8 min-h-8 text-xs" @click="openSignaturesDrawer">
                <UIcon name="i-lucide-plus" class="mr-1 h-3.5 w-3.5" />
                Créer une signature
              </button>
            </div>

            <!-- Always-available manage link -->
            <button
              v-else
              type="button"
              class="mt-2.5 text-xs font-medium text-[var(--app-ink-soft)] underline decoration-[var(--app-line)] underline-offset-2 hover:text-[var(--app-ink)]"
              @click="openSignaturesDrawer"
            >
              Gérer mes signatures
            </button>
          </div>

          <div
            v-if="mode === 'edit'"
            class="flex items-center justify-between rounded-lg border border-[var(--app-line)] px-3 py-2.5"
          >
            <div>
              <p class="text-sm font-medium text-[var(--app-ink)]">Modèle actif</p>
              <p class="text-muted text-xs">Les modèles inactifs restent enregistrés mais ne sont plus proposés.</p>
            </div>
            <UiCheckbox id="template-active" v-model="form.is_active" />
          </div>
        </form>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <template v-if="mode === 'preview'">
            <button type="button" class="btn-secondary flex-1" @click="emit('close')">Fermer</button>
            <button v-if="template" type="button" class="btn-primary flex-1" @click="emit('edit', template)">
              <UIcon name="i-lucide-square-pen" class="mr-1.5 h-4 w-4" />
              Modifier ce modèle
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="emit('close')">
              Annuler
            </button>
            <button
              type="submit"
              form="email-template-form"
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

    <!-- Inline `{`-autocomplete for the subject and body fields -->
    <UiVariableAutocomplete
      :open="subjectInsertion.open.value"
      :items="subjectInsertion.items.value"
      :active-index="subjectInsertion.activeIndex.value"
      :position="subjectInsertion.position.value"
      @select="subjectInsertion.selectVariable"
      @activate="(index: number) => (subjectInsertion.activeIndex.value = index)"
    />
    <UiVariableAutocomplete
      :open="bodyInsertion.open.value"
      :items="bodyInsertion.items.value"
      :active-index="bodyInsertion.activeIndex.value"
      :position="bodyInsertion.position.value"
      @select="bodyInsertion.selectVariable"
      @activate="(index: number) => (bodyInsertion.activeIndex.value = index)"
    />
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { EmailSignature, EmailTemplate } from '~/types'
import type { EmailTemplateDrawerMode } from '~/types/DrawerStack'
import { computed, ref, watch } from 'vue'
import { createEmailTemplate, previewEmailTemplate, updateEmailTemplate } from '~/services/emailTemplatesService'
import { getEmailSignatures } from '~/services/emailSignaturesService'
import { useVariableInsertion } from '~/composables/useVariableInsertion'
import { buildPreviewSampleVariables } from '~/utils/emailVariables'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

/** Local shape of the template form. */
interface EmailTemplateForm {
  name: string
  subject: string
  body_html: string
  is_active: boolean
  signature_id: number | null
}

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  mode: {
    type: String as PropType<EmailTemplateDrawerMode>,
    default: 'create',
  },
  template: {
    type: Object as PropType<EmailTemplate | null>,
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
  /** The template was created or updated. */
  saved: [template: EmailTemplate]
  /** Switch from preview to edit for the given template. */
  edit: [template: EmailTemplate]
}>()

const toast = useToast()

/** Persistent drawer stack (used to stack the signatures manager on top). */
const drawerStack = useDrawerStackStore()

/** Whether a save request is in flight. */
const isSaving: Ref<boolean> = ref<boolean>(false)

/** Whether the preview render is loading. */
const isPreviewLoading: Ref<boolean> = ref<boolean>(false)

/** Rendered preview subject. */
const previewSubject: Ref<string> = ref<string>('')

/** Rendered preview HTML body. */
const previewHtml: Ref<string> = ref<string>('')

/** The user's signatures (for the selector + invite). */
const signatures: Ref<EmailSignature[]> = ref<EmailSignature[]>([])

/** Whether the "include a signature" switch is on. */
const includeSignature: Ref<boolean> = ref<boolean>(false)

/** Template form state (create/edit modes). */
const form: Ref<EmailTemplateForm> = ref<EmailTemplateForm>({
  name: '',
  subject: '',
  body_html: '',
  is_active: true,
  signature_id: null,
})

/** Subject input element (for cursor-aware variable insertion). */
const subjectRef: Ref<HTMLInputElement | null> = ref<HTMLInputElement | null>(null)

/** Body textarea element. */
const bodyRef: Ref<HTMLTextAreaElement | null> = ref<HTMLTextAreaElement | null>(null)

/** Assisted insertion (chips + `{`-autocomplete) for the subject. */
const subjectInsertion = useVariableInsertion(
  subjectRef,
  (): string => form.value.subject,
  (value: string): void => {
    form.value.subject = value
  },
)

/** Assisted insertion for the body. */
const bodyInsertion = useVariableInsertion(
  bodyRef,
  (): string => form.value.body_html,
  (value: string): void => {
    form.value.body_html = value
  },
)

/** Key of the entity the form was last initialised for (mode + template id). */
const lastInitKey: Ref<string> = ref<string>('')

/** Drawer title matching the current mode. */
const drawerTitle: ComputedRef<string> = computed((): string => {
  if (props.mode === 'preview') return props.template?.name ?? 'Aperçu du modèle'
  if (props.mode === 'edit') return 'Modifier le modèle'
  return 'Nouveau modèle'
})

/**
 * Best default signature id: the flagged default, else the first one.
 * @returns The id to preselect, or null when the user has no signature.
 */
function defaultSignatureId(): number | null {
  const preferred: EmailSignature | undefined =
    signatures.value.find((s: EmailSignature): boolean => s.is_default) ?? signatures.value[0]
  return preferred?.id ?? null
}

/**
 * Load the user's signatures and keep the selection coherent.
 * @returns A promise that resolves once loaded.
 */
async function loadSignatures(): Promise<void> {
  try {
    signatures.value = await getEmailSignatures()
  } catch {
    // Non-blocking: the signature section simply shows the empty state.
    signatures.value = []
  }
  // No signature available → the switch can't be on.
  if (signatures.value.length === 0) {
    includeSignature.value = false
    form.value.signature_id = null
    return
  }
  // Switch on but no valid selection → fall back to the default signature.
  const isSelectionValid: boolean = signatures.value.some(
    (s: EmailSignature): boolean => s.id === form.value.signature_id,
  )
  if (includeSignature.value && !isSelectionValid) {
    form.value.signature_id = defaultSignatureId()
  }
}

/** Stack the signatures manager on top of this drawer. */
function openSignaturesDrawer(): void {
  drawerStack.push({ kind: 'email-signatures' })
}

/**
 * Create or update the template, then notify the host.
 * @returns A promise that resolves once the template is persisted.
 */
async function handleSave(): Promise<void> {
  isSaving.value = true
  const signatureId: number | null = includeSignature.value ? form.value.signature_id : null
  try {
    if (props.mode === 'edit' && props.template) {
      const updated: EmailTemplate = await updateEmailTemplate(props.template.id, {
        name: form.value.name,
        subject: form.value.subject,
        body_html: form.value.body_html,
        is_active: form.value.is_active,
        signature_id: signatureId,
      })
      toast.success('Modèle mis à jour')
      emit('saved', updated)
    } else {
      const created: EmailTemplate = await createEmailTemplate({
        name: form.value.name,
        subject: form.value.subject,
        body_html: form.value.body_html,
        signature_id: signatureId,
      })
      toast.success('Modèle créé')
      emit('saved', created)
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enregistrement du modèle")
  } finally {
    isSaving.value = false
  }
}

/**
 * Render the preview of the current template with sample data.
 * @returns A promise that resolves once the preview is loaded.
 */
async function loadPreview(): Promise<void> {
  if (!props.template) return
  isPreviewLoading.value = true
  try {
    const preview: { subject: string; body_html: string } = await previewEmailTemplate(
      props.template.id,
      buildPreviewSampleVariables(),
    )
    previewSubject.value = preview.subject
    previewHtml.value = preview.body_html
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors du chargement de l'aperçu")
  } finally {
    isPreviewLoading.value = false
  }
}

// Turning the switch on with no valid selection → preselect the default.
watch(includeSignature, (on: boolean): void => {
  if (on && form.value.signature_id == null) {
    form.value.signature_id = defaultSignatureId()
  }
})

watch(
  (): [boolean, EmailTemplateDrawerMode, number | undefined] => [props.open, props.mode, props.template?.id],
  ([open, mode]: [boolean, EmailTemplateDrawerMode, number | undefined]): void => {
    if (!open) return
    if (mode === 'preview') {
      previewSubject.value = ''
      previewHtml.value = ''
      void loadPreview()
      return
    }
    // Refresh signatures every time the editor is shown (e.g. after managing them).
    void loadSignatures()
    // Only (re)initialise the form when the target template changes — returning
    // from the stacked signatures drawer must NOT wipe unsaved edits.
    const key: string = `${mode}:${props.template?.id ?? 'new'}`
    if (key === lastInitKey.value) return
    lastInitKey.value = key
    includeSignature.value = props.template?.signature_id != null
    form.value = {
      name: props.template?.name ?? '',
      subject: props.template?.subject ?? '',
      body_html: props.template?.body_html ?? '',
      is_active: props.template?.is_active ?? true,
      signature_id: props.template?.signature_id ?? null,
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
