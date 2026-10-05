<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 bottom-[var(--app-drawer-bottom)] z-50 flex w-full max-w-[560px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] pointer-coarse:size-11"
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
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] pointer-coarse:size-11"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <UiDrawerBrowseNav
          v-if="mode === 'preview'"
          :position-label="browsePositionLabel"
          :can-previous="canBrowsePrevious"
          :can-next="canBrowseNext"
          @previous="emit('browsePrevious')"
          @next="emit('browseNext')"
        />

        <div v-if="mode === 'preview'" class="flex-1 overflow-x-hidden overflow-y-auto px-5 py-4">
          <div v-if="isPreviewLoading" class="flex items-center justify-center py-16">
            <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-faint)]" />
          </div>

          <UiEmailPreviewPane v-else :subject="previewSubject" :body-html="previewHtml" />
        </div>

        <form
          v-else
          id="email-template-form"
          class="flex-1 space-y-8 overflow-y-auto px-5 py-6"
          @submit.prevent="handleSave"
        >
          <div class="space-y-5">
            <div>
              <label class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
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
              <label class="mb-2 block text-sm font-medium text-[var(--app-ink)]">Étape de la séquence</label>
              <UiSelectField v-model="form.category" :options="categoryOptions" />
              <p class="text-muted mt-1.5 text-xs">
                Classe le modèle dans l'onglet correspondant — un premier email et une relance ne s'écrivent pas pareil.
              </p>
            </div>

            <div>
              <label class="mb-2 block text-sm font-medium text-[var(--app-ink)]">Habillage</label>
              <UiSelectField v-model="form.layout" :options="layoutOptions" />
              <p class="text-muted mt-1.5 text-xs">{{ selectedLayoutDescription }}</p>
            </div>

            <div
              v-if="mode === 'create' && isSuperAdminUser"
              class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)] px-4 py-3"
            >
              <label class="flex cursor-pointer items-start gap-3">
                <input v-model="shareWithAll" type="checkbox" class="mt-0.5" />
                <span>
                  <span class="block text-sm font-medium text-[var(--app-ink)]"
                    >Partager avec tous les utilisateurs</span
                  >
                  <span class="text-muted mt-0.5 block text-xs leading-relaxed">
                    Ajoute ce modèle à la bibliothèque commune. Les autres pourront le personnaliser sans modifier votre
                    version.
                  </span>
                </span>
              </label>
            </div>

            <div>
              <label class="mb-2 block text-sm font-medium text-[var(--app-ink)]">
                Objet <span class="text-[var(--app-red)]">*</span>
              </label>
              <input
                ref="subjectRef"
                v-model="form.subject"
                type="text"
                required
                class="input-field"
                placeholder="Ex : Création de site web pour {entreprise}"
                @focus="activeField = 'subject'"
                @input="subjectInsertion.onInput"
                @keydown="subjectInsertion.onKeydown"
                @blur="subjectInsertion.onBlur"
              />
            </div>

            <div>
              <div class="mb-2 flex items-center justify-between gap-2">
                <label class="block text-sm font-medium text-[var(--app-ink)]">
                  Message <span class="text-[var(--app-red)]">*</span>
                </label>
                <div class="flex gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] p-0.5">
                  <button
                    type="button"
                    :class="composerTabClass(!isComposerPreview)"
                    @click="isComposerPreview = false"
                  >
                    <UIcon name="i-lucide-pencil" class="h-3 w-3" />
                    Écrire
                  </button>
                  <button type="button" :class="composerTabClass(isComposerPreview)" @click="showComposerPreview">
                    <UIcon name="i-lucide-eye" class="h-3 w-3" />
                    Aperçu
                  </button>
                </div>
              </div>

              <template v-if="isComposerPreview">
                <div v-if="isPreviewLoading" class="flex items-center justify-center py-16">
                  <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-faint)]" />
                </div>
                <UiEmailPreviewPane v-else :subject="previewSubject" :body-html="previewHtml" />
              </template>

              <div v-show="!isComposerPreview">
                <div class="mb-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface-2)]/50 p-3.5">
                  <div class="mb-3 flex items-center justify-between gap-2">
                    <p class="text-xs font-medium text-[var(--app-ink)]">Variables personnalisées</p>
                    <span
                      class="inline-flex items-center gap-1 rounded-md border border-[var(--app-line)] bg-[var(--app-surface)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--app-ink-soft)]"
                      title="Le clic insère dans ce champ"
                    >
                      <UIcon name="i-lucide-corner-down-right" class="h-3 w-3" />
                      {{ activeFieldLabel }}
                    </span>
                  </div>
                  <UiVariableChips @insert="insertIntoActiveField" />
                  <p class="mt-3 text-[11px] leading-snug text-[var(--app-ink-soft)]">
                    Clic
                    <UIcon name="i-lucide-arrow-right" class="inline-block h-[1em] w-[1em] align-[-0.125em]" /> insère
                    au curseur dans le champ actif. Ou tapez «&nbsp;{&nbsp;» dans l'objet ou le message.
                  </p>
                </div>

                <textarea
                  ref="bodyRef"
                  v-model="form.body_html"
                  required
                  rows="12"
                  class="input-field font-mono text-xs leading-relaxed"
                  placeholder="Bonjour {salutation},&#10;&#10;Je me présente..."
                  @focus="activeField = 'body'"
                  @input="bodyInsertion.onInput"
                  @keydown="bodyInsertion.onKeydown"
                  @blur="bodyInsertion.onBlur"
                ></textarea>
                <p class="mt-1.5 text-xs text-[var(--app-ink-soft)]">Le message accepte du HTML.</p>
              </div>
            </div>
          </div>

          <section class="space-y-3">
            <p class="app-label">Signature</p>
            <div class="rounded-xl border border-[var(--app-line)] p-3.5">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-medium text-[var(--app-ink)]">Inclure une signature</p>
                  <p class="text-muted text-xs">Ajoutée au bas de l'email envoyé.</p>
                </div>
                <UiSwitch
                  id="template-include-signature"
                  v-model="includeSignature"
                  :disabled="signatures.length === 0"
                />
              </div>

              <div v-if="includeSignature && signatures.length" class="mt-3.5">
                <UiSelectField v-model="selectedSignatureId" :options="signatureOptions" />
              </div>

              <div v-if="signatures.length === 0" class="mt-3.5">
                <p class="text-muted mb-2.5 text-xs">Aucune signature configurée.</p>
                <button type="button" class="btn-primary" @click="openSignaturesDrawer">
                  <UIcon name="i-lucide-plus" class="h-4 w-4" />
                  Créer une signature
                </button>
              </div>

              <button
                v-else
                type="button"
                class="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                @click="openSignaturesDrawer"
              >
                <UIcon name="i-lucide-settings-2" class="h-3.5 w-3.5" />
                Gérer mes signatures
              </button>
            </div>
          </section>

          <section v-if="mode === 'edit'" class="space-y-3">
            <p class="app-label">Statut</p>
            <div class="flex items-center justify-between rounded-xl border border-[var(--app-line)] p-3.5">
              <div>
                <p class="text-sm font-medium text-[var(--app-ink)]">Modèle actif</p>
                <p class="text-muted text-xs">Les modèles inactifs restent enregistrés mais ne sont plus proposés.</p>
              </div>
              <UiSwitch id="template-active" v-model="form.is_active" />
            </div>
          </section>
        </form>

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
import type { UseToastReturn } from '~/types/Composables'
import type {
  EmailTemplateForm,
  UiEmailTemplateDrawerEmits,
  UiEmailTemplateDrawerProps,
} from '~/types/UiEmailTemplateDrawer'
import type { ComputedRef, EmitFn, PropType, Ref, WritableComputedRef } from 'vue'
import type {
  EmailSignature,
  EmailTemplate,
  EmailTemplateCategory,
  EmailTemplateLayout,
  EmailTemplatePreview,
} from '~/types'
import type { EmailTemplateDrawerMode } from '~/types/DrawerStack'
import type { SelectFieldOption } from '~/types/SelectField'
import { computed, ref, watch } from 'vue'
import { EmailTemplatesService } from '~/services/emailTemplatesService'
import { EmailSignaturesService } from '~/services/emailSignaturesService'
import { useVariableInsertion } from '~/composables/useVariableInsertion'
import { EmailVariables } from '~/utils/emailVariables'
import {
  DEFAULT_EMAIL_TEMPLATE_LAYOUT,
  EMAIL_TEMPLATE_CATEGORIES,
  EMAIL_TEMPLATE_CATEGORY_LABELS,
  EMAIL_TEMPLATE_LAYOUTS,
  EMAIL_TEMPLATE_LAYOUT_DESCRIPTIONS,
  EMAIL_TEMPLATE_LAYOUT_LABELS,
} from '~/utils/emailTemplate'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'
import { useUserStore } from '~/stores/user'
import { isSuperAdmin } from '~/utils/userRoles'

/** Drawer to create or edit an email template. */
const props: UiEmailTemplateDrawerProps = defineProps({
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
  browsePositionLabel: {
    type: String,
    default: '',
  },
  canBrowsePrevious: {
    type: Boolean,
    default: false,
  },
  canBrowseNext: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiEmailTemplateDrawerEmits> = defineEmits<UiEmailTemplateDrawerEmits>()

const toast: UseToastReturn = useToast()

/** Persistent drawer stack (used to stack the signatures manager on top). */
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const userStore: ReturnType<typeof useUserStore> = useUserStore()

const isSuperAdminUser: ComputedRef<boolean> = computed((): boolean => isSuperAdmin(userStore.user?.role))
const shareWithAll: Ref<boolean> = ref(false)

/** Whether a save request is in flight. */
const isSaving: Ref<boolean> = ref(false)

/** Whether the preview render is loading. */
const isPreviewLoading: Ref<boolean> = ref(false)

/** Whether the composer shows the rendered draft instead of the HTML editor. */
const isComposerPreview: Ref<boolean> = ref(false)

/** Rendered preview subject. */
const previewSubject: Ref<string> = ref('')

/** Rendered preview HTML body. */
const previewHtml: Ref<string> = ref('')

/** The user's signatures (for the selector + invite). */
const signatures: Ref<EmailSignature[]> = ref([])

/** Whether the "include a signature" switch is on. */
const includeSignature: Ref<boolean> = ref(false)

/** Template form state (create/edit modes). */
const form: Ref<EmailTemplateForm> = ref({
  name: '',
  subject: '',
  body_html: '',
  is_active: true,
  signature_id: null,
  category: 'first_email',
  layout: DEFAULT_EMAIL_TEMPLATE_LAYOUT,
})

const signatureOptions: ComputedRef<SelectFieldOption<number>[]> = computed((): SelectFieldOption<number>[] =>
  signatures.value.map(
    (signature: EmailSignature): SelectFieldOption<number> => ({
      value: signature.id,
      label: `${signature.name}${signature.is_default ? ' (par défaut)' : ''}`,
    }),
  ),
)

/** Signature bound to the selector — the form keeps `null` for « none », the selector never shows it. */
const selectedSignatureId: WritableComputedRef<number> = computed({
  get: (): number => form.value.signature_id ?? 0,
  set: (value: number): void => {
    form.value.signature_id = value
  },
})

/** Sequence-step options offered by the category selector. */
const categoryOptions: SelectFieldOption[] = EMAIL_TEMPLATE_CATEGORIES.map(
  (category: EmailTemplateCategory): SelectFieldOption => ({
    value: category,
    label: EMAIL_TEMPLATE_CATEGORY_LABELS[category],
  }),
)

const layoutOptions: SelectFieldOption[] = EMAIL_TEMPLATE_LAYOUTS.map(
  (layout: EmailTemplateLayout): SelectFieldOption => ({
    value: layout,
    label: EMAIL_TEMPLATE_LAYOUT_LABELS[layout],
  }),
)

const selectedLayoutDescription: ComputedRef<string> = computed(
  (): string => EMAIL_TEMPLATE_LAYOUT_DESCRIPTIONS[form.value.layout],
)

/** Subject input element (for cursor-aware variable insertion). */
const subjectRef: Ref<HTMLInputElement | null> = ref(null)

/** Body textarea element. */
const bodyRef: Ref<HTMLTextAreaElement | null> = ref(null)

/** Assisted insertion (chips + `{`-autocomplete) for the subject. */
const subjectInsertion: VariableInsertion = useVariableInsertion(
  subjectRef,
  (): string => form.value.subject,
  (value: string): void => {
    form.value.subject = value
  },
)

/** Assisted insertion for the body. */
const bodyInsertion: VariableInsertion = useVariableInsertion(
  bodyRef,
  (): string => form.value.body_html,
  (value: string): void => {
    form.value.body_html = value
  },
)

/** Field the single variable palette targets (last focused; defaults to body). */
const activeField: Ref<'subject' | 'body'> = ref('body')

/** Key of the entity the form was last initialised for (mode + template id). */
const lastInitKey: Ref<string> = ref('')

/** Drawer title matching the current mode. */
const drawerTitle: ComputedRef<string> = computed((): string => {
  if (props.mode === 'preview') return props.template?.name ?? 'Aperçu du modèle'
  if (props.mode === 'edit') return 'Modifier le modèle'
  return 'Nouveau modèle'
})

/** Human label of the field the palette currently targets. */
const activeFieldLabel: ComputedRef<string> = computed((): string =>
  activeField.value === 'subject' ? 'Objet' : 'Message',
)

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
    signatures.value = await EmailSignaturesService.getEmailSignatures()
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
 * Insert a variable token into whichever field is currently focused.
 * @param token - The placeholder to insert (e.g. `{prenom}`).
 */
function insertIntoActiveField(token: string): void {
  if (activeField.value === 'subject') subjectInsertion.insertToken(token)
  else bodyInsertion.insertToken(token)
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
      const updated: EmailTemplate = await EmailTemplatesService.updateEmailTemplate(props.template.id, {
        name: form.value.name,
        subject: form.value.subject,
        body_html: form.value.body_html,
        is_active: form.value.is_active,
        signature_id: signatureId,
        category: form.value.category,
        layout: form.value.layout,
      })
      toast.success('Modèle mis à jour')
      emit('saved', updated)
    } else {
      const created: EmailTemplate = await EmailTemplatesService.createEmailTemplate({
        name: form.value.name,
        subject: form.value.subject,
        body_html: form.value.body_html,
        signature_id: signatureId,
        category: form.value.category,
        layout: form.value.layout,
        share_with_all: shareWithAll.value,
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
 * Classes of an Écrire/Aperçu tab.
 * @param active - Whether the tab is the current one.
 * @returns Tailwind classes.
 */
function composerTabClass(active: boolean): string {
  const base: string =
    'flex cursor-pointer items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors'
  return active
    ? `${base} bg-[var(--app-btn-bg)] text-[var(--app-btn-text)]`
    : `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Switch the composer to its preview tab: the draft currently typed, rendered as it would leave.
 * @returns A promise that resolves once the preview is rendered.
 */
async function showComposerPreview(): Promise<void> {
  isComposerPreview.value = true
  isPreviewLoading.value = true
  try {
    const preview: EmailTemplatePreview = await EmailTemplatesService.previewEmailTemplateDraft({
      subject: form.value.subject,
      body_html: form.value.body_html,
      signature_id: includeSignature.value ? form.value.signature_id : null,
      layout: form.value.layout,
      variables: EmailVariables.buildPreviewSampleVariables(),
    })
    previewSubject.value = preview.subject
    previewHtml.value = preview.body_html
  } catch (err: unknown) {
    isComposerPreview.value = false
    toast.error(err instanceof Error ? err.message : "Erreur lors du chargement de l'aperçu")
  } finally {
    isPreviewLoading.value = false
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
    const preview: EmailTemplatePreview = await EmailTemplatesService.previewEmailTemplate(
      props.template.id,
      EmailVariables.buildPreviewSampleVariables(),
    )
    previewSubject.value = preview.subject
    previewHtml.value = preview.body_html
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors du chargement de l'aperçu")
  } finally {
    isPreviewLoading.value = false
  }
}

watch(
  (): [EmailTemplateLayout, boolean, number | null] => [
    form.value.layout,
    includeSignature.value,
    form.value.signature_id,
  ],
  (): void => {
    if (isComposerPreview.value) void showComposerPreview()
  },
)

// Turning the switch on with no valid selection → preselect the default.
watch(includeSignature, (on: boolean): void => {
  if (on && form.value.signature_id == null) {
    form.value.signature_id = defaultSignatureId()
  }
})

watch(
  (): [boolean, EmailTemplateDrawerMode, number | undefined] => [
    props.open,
    props.mode ?? 'create',
    props.template?.id,
  ],
  ([open, mode]: [boolean, EmailTemplateDrawerMode, number | undefined]): void => {
    if (!open) return
    isComposerPreview.value = false
    if (mode === 'preview') {
      previewSubject.value = ''
      previewHtml.value = ''
      void loadPreview()
      return
    }
    // Refresh signatures every time the editor is shown (e.g. after managing them).
    void loadSignatures()
    // Only when the target changes: returning from the signatures drawer must not wipe edits.
    const key: string = `${mode}:${props.template?.id ?? 'new'}`
    if (key === lastInitKey.value) return
    lastInitKey.value = key
    shareWithAll.value = false
    includeSignature.value = props.template ? props.template.signature_id != null : true
    form.value = {
      name: props.template?.name ?? '',
      subject: props.template?.subject ?? '',
      body_html: props.template?.body_html ?? '',
      is_active: props.template?.is_active ?? true,
      signature_id: props.template?.signature_id ?? null,
      category: props.template?.category ?? 'first_email',
      layout: props.template?.layout ?? DEFAULT_EMAIL_TEMPLATE_LAYOUT,
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
