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
              v-model="form.subject"
              type="text"
              required
              class="input-field"
              placeholder="Ex : Création de site web pour {company_name}"
            />
            <p class="text-muted mt-1 text-xs">Utilisez {variable} pour les valeurs dynamiques</p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">
              Corps de l'email (HTML) <span class="text-[var(--app-red)]">*</span>
            </label>
            <textarea
              v-model="form.body_html"
              required
              rows="16"
              class="input-field font-mono text-xs"
              placeholder="Bonjour {name},&#10;&#10;Je me présente..."
            ></textarea>
            <p class="text-muted mt-1 text-xs">Variables disponibles : {name}, {company_name}, {email}, etc.</p>
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
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { EmailTemplate } from '~/types'
import type { EmailTemplateDrawerMode } from '~/types/DrawerStack'
import { computed, ref, watch } from 'vue'
import { createEmailTemplate, previewEmailTemplate, updateEmailTemplate } from '~/services/emailTemplatesService'
import { useToast } from '~/composables/useToast'

/** Sample variables used to render a realistic preview. */
const PREVIEW_SAMPLE_VARIABLES: Record<string, string> = {
  name: 'Jean Dupont',
  company_name: 'Restaurant Le Gourmet',
  email: 'contact@legourmet.fr',
  phone: '01 23 45 67 89',
}

/** Local shape of the template form. */
interface EmailTemplateForm {
  name: string
  subject: string
  body_html: string
  is_active: boolean
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

/** Whether a save request is in flight. */
const isSaving: Ref<boolean> = ref<boolean>(false)

/** Whether the preview render is loading. */
const isPreviewLoading: Ref<boolean> = ref<boolean>(false)

/** Rendered preview subject. */
const previewSubject: Ref<string> = ref<string>('')

/** Rendered preview HTML body. */
const previewHtml: Ref<string> = ref<string>('')

/** Template form state (create/edit modes). */
const form: Ref<EmailTemplateForm> = ref<EmailTemplateForm>({
  name: '',
  subject: '',
  body_html: '',
  is_active: true,
})

/** Drawer title matching the current mode. */
const drawerTitle: ComputedRef<string> = computed((): string => {
  if (props.mode === 'preview') return props.template?.name ?? 'Aperçu du modèle'
  if (props.mode === 'edit') return 'Modifier le modèle'
  return 'Nouveau modèle'
})

/**
 * Create or update the template, then notify the host.
 * @returns A promise that resolves once the template is persisted.
 */
async function handleSave(): Promise<void> {
  isSaving.value = true
  try {
    if (props.mode === 'edit' && props.template) {
      const updated: EmailTemplate = await updateEmailTemplate(props.template.id, {
        name: form.value.name,
        subject: form.value.subject,
        body_html: form.value.body_html,
        is_active: form.value.is_active,
      })
      toast.success('Modèle mis à jour')
      emit('saved', updated)
    } else {
      const created: EmailTemplate = await createEmailTemplate({
        name: form.value.name,
        subject: form.value.subject,
        body_html: form.value.body_html,
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
      PREVIEW_SAMPLE_VARIABLES,
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
  (): [boolean, EmailTemplateDrawerMode, number | undefined] => [props.open, props.mode, props.template?.id],
  ([open, mode]: [boolean, EmailTemplateDrawerMode, number | undefined]): void => {
    if (!open) return
    if (mode === 'preview') {
      previewSubject.value = ''
      previewHtml.value = ''
      void loadPreview()
      return
    }
    form.value = {
      name: props.template?.name ?? '',
      subject: props.template?.subject ?? '',
      body_html: props.template?.body_html ?? '',
      is_active: props.template?.is_active ?? true,
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
