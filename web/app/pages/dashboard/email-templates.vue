<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Modèles d'email</h1>
        <p class="text-muted mt-1 text-sm">Les contenus réutilisés par vos campagnes et relances.</p>
      </div>
      <button class="btn-primary" @click="openCreateDrawer">
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        <span>Nouveau modèle</span>
      </button>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="relative w-full max-w-xs">
        <UIcon
          name="i-lucide-search"
          class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
        />
        <input v-model="searchQuery" type="text" placeholder="Rechercher un modèle…" class="input-field pl-9" />
      </div>
      <p class="text-muted text-xs">
        {{ emailTemplates.length }} modèle{{ emailTemplates.length > 1 ? 's' : '' }}
        <template v-if="inactiveTemplates.length">
          · {{ inactiveTemplates.length }} inactif{{ inactiveTemplates.length > 1 ? 's' : '' }}
        </template>
      </p>
    </div>

    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <div v-else-if="emailTemplates.length === 0" class="card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucun modèle d'email</h3>
      <p class="text-muted mx-auto mt-2 max-w-sm text-sm leading-relaxed">
        Créez un premier modèle pour alimenter vos campagnes de prospection.
      </p>
      <div class="mt-6 flex justify-center">
        <button class="btn-primary" @click="openCreateDrawer">
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          <span>Créer un premier modèle</span>
        </button>
      </div>
    </div>

    <div v-else-if="filteredTemplates.length === 0" class="card px-6 py-10 text-center">
      <p class="text-muted text-sm">Aucun modèle ne correspond à « {{ searchQuery }} ».</p>
    </div>

    <template v-else>
      <section v-for="group in templateGroups" :key="group.key">
        <p class="app-label mb-2">{{ group.heading }} · {{ group.templates.length }}</p>
        <div class="card divide-y divide-[var(--app-line-soft)] overflow-hidden p-0">
          <div
            v-for="template in group.templates"
            :key="template.id"
            class="group flex items-start gap-4 px-4 py-3 transition-colors hover:bg-[var(--app-surface-2)]/60"
            :class="template.is_active ? '' : 'opacity-70'"
          >
            <button type="button" class="min-w-0 flex-1 cursor-pointer text-left" @click="openPreviewDrawer(template)">
              <div class="flex flex-wrap items-center gap-2">
                <h3
                  class="truncate text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors group-hover:decoration-[var(--app-accent)]"
                >
                  {{ template.name }}
                </h3>
                <span v-if="!template.is_active" class="app-badge">Inactif</span>
              </div>
              <p class="text-muted mt-0.5 truncate text-xs">{{ template.subject }}</p>
              <p
                v-if="template.variables && template.variables.length"
                class="font-label mt-1.5 text-[10px] text-[var(--app-faint)]"
              >
                <UIcon name="i-lucide-braces" class="mr-1 inline-block h-3 w-3 align-[-2px]" />{{
                  variablesLabel(template)
                }}
              </p>
            </button>

            <div class="flex shrink-0 items-center gap-1.5">
              <button
                class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
                title="Aperçu avec des données d'exemple"
                @click="openPreviewDrawer(template)"
              >
                <UIcon name="i-lucide-eye" class="h-3.5 w-3.5" />
              </button>
              <button
                class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
                title="Modifier"
                @click="openEditDrawer(template)"
              >
                <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
              </button>
              <button
                class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
                title="Dupliquer"
                @click="duplicateTemplate(template)"
              >
                <UIcon name="i-lucide-copy" class="h-3.5 w-3.5" />
              </button>
              <button
                class="btn-secondary h-8 min-h-8 px-2.5 text-xs"
                :title="template.is_active ? 'Désactiver' : 'Activer'"
                @click="toggleTemplateActive(template)"
              >
                <UIcon :name="template.is_active ? 'i-lucide-pause' : 'i-lucide-play'" class="h-3.5 w-3.5" />
              </button>
              <button
                class="btn-danger flex h-8 min-h-8 items-center justify-center px-2.5 text-xs"
                title="Supprimer"
                @click="confirmDelete(template)"
              >
                <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>

    <UiConfirmModal
      ref="confirmModal"
      title="Supprimer le modèle"
      :message="`Supprimer le modèle « ${templateToDelete?.name} » ? Cette action est irréversible.`"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDeleteTemplate"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { TemplateGroup } from '~/types/EmailTemplatesPage'
import type { ComputedRef, Ref } from 'vue'
import type { EmailTemplate } from '~/types'
import { computed, onMounted, ref, watch } from 'vue'
import { EmailTemplatesService } from '~/services/emailTemplatesService'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast: UseToastReturn = useToast()

/** Persistent drawer stack (create/edit/preview live there). */
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const emailTemplates: Ref<EmailTemplate[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const searchQuery: Ref<string> = ref('')
const templateToDelete: Ref<EmailTemplate | null> = ref(null)
const confirmModal: Ref<{ open: () => void; close: () => void } | null> = ref(null)

/** Templates matching the search query (name or subject). */
const filteredTemplates: ComputedRef<EmailTemplate[]> = computed((): EmailTemplate[] => {
  const query: string = searchQuery.value.trim().toLowerCase()
  if (!query) return emailTemplates.value
  return emailTemplates.value.filter(
    (template: EmailTemplate): boolean =>
      template.name.toLowerCase().includes(query) || template.subject.toLowerCase().includes(query),
  )
})

/** Inactive templates (used by the counter). */
const inactiveTemplates: ComputedRef<EmailTemplate[]> = computed((): EmailTemplate[] => {
  return emailTemplates.value.filter((template: EmailTemplate): boolean => !template.is_active)
})

/** Filtered templates grouped into « Actifs » / « Inactifs » sections. */
const templateGroups: ComputedRef<TemplateGroup[]> = computed((): TemplateGroup[] => {
  const active: EmailTemplate[] = filteredTemplates.value.filter(
    (template: EmailTemplate): boolean => template.is_active,
  )
  const inactive: EmailTemplate[] = filteredTemplates.value.filter(
    (template: EmailTemplate): boolean => !template.is_active,
  )
  const groups: TemplateGroup[] = []
  if (active.length) groups.push({ key: 'active', heading: 'Modèles actifs', templates: active })
  if (inactive.length) groups.push({ key: 'inactive', heading: 'Modèles inactifs', templates: inactive })
  return groups
})

/**
 * Load every template of the current user.
 * @returns A promise that resolves once the list is loaded.
 */
async function loadTemplates(): Promise<void> {
  try {
    isLoading.value = true
    emailTemplates.value = await EmailTemplatesService.getEmailTemplates()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du chargement des modèles')
  } finally {
    isLoading.value = false
  }
}

/**
 * Human-readable list of a template's variables (e.g. "{name} {company_name}").
 * Built in script because a template literal containing braces breaks the Vue
 * template expression parser.
 * @param template - Template whose variables are displayed.
 * @returns Space-separated variable placeholders.
 */
function variablesLabel(template: EmailTemplate): string {
  return (template.variables ?? []).map((variableName: string): string => '{' + variableName + '}').join(' ')
}

/** Open the creation drawer. */
function openCreateDrawer(): void {
  drawerStack.push({ kind: 'email-template', mode: 'create', template: null })
}

/**
 * Open the edit drawer for a template.
 * @param template - Template to edit.
 */
function openEditDrawer(template: EmailTemplate): void {
  drawerStack.push({ kind: 'email-template', mode: 'edit', template })
}

/**
 * Open the preview drawer for a template (rendered with sample data).
 * @param template - Template to preview.
 */
function openPreviewDrawer(template: EmailTemplate): void {
  drawerStack.push({ kind: 'email-template', mode: 'preview', template })
}

/**
 * Duplicate a template (suffixe « (copie) »), useful to iterate on a variant.
 * @param template - Template to duplicate.
 */
async function duplicateTemplate(template: EmailTemplate): Promise<void> {
  try {
    const copy: EmailTemplate = await EmailTemplatesService.createEmailTemplate({
      name: `${template.name} (copie)`,
      subject: template.subject,
      body_html: template.body_html,
      signature_id: template.signature_id ?? null,
    })
    emailTemplates.value.unshift(copy)
    toast.success(`Modèle « ${template.name} » dupliqué`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la duplication')
  }
}

/**
 * Toggle the active flag of a template without opening the drawer.
 * @param template - Template to toggle.
 */
async function toggleTemplateActive(template: EmailTemplate): Promise<void> {
  try {
    const updated: EmailTemplate = await EmailTemplatesService.updateEmailTemplate(template.id, {
      is_active: !template.is_active,
    })
    const index: number = emailTemplates.value.findIndex((t: EmailTemplate): boolean => t.id === updated.id)
    if (index !== -1) emailTemplates.value.splice(index, 1, updated)
    toast.success(updated.is_active ? `« ${updated.name} » activé` : `« ${updated.name} » désactivé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  }
}

/**
 * Ask for confirmation before deleting a template.
 * @param template - Template to delete.
 */
function confirmDelete(template: EmailTemplate): void {
  templateToDelete.value = template
  confirmModal.value?.open()
}

/**
 * Delete the pending template after confirmation.
 * @returns A promise that resolves once the template is removed.
 */
async function handleDeleteTemplate(): Promise<void> {
  const template: EmailTemplate | null = templateToDelete.value
  if (!template) return
  try {
    await EmailTemplatesService.deleteEmailTemplate(template.id)
    emailTemplates.value = emailTemplates.value.filter((t: EmailTemplate): boolean => t.id !== template.id)
    toast.success(`Modèle « ${template.name} » supprimé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    templateToDelete.value = null
  }
}

// Créations/éditions faites dans le drawer (hébergé par le layout) → recharger.
watch(
  (): number => drawerStack.emailTemplatesRefreshCounter,
  (): void => {
    void loadTemplates()
  },
)

onMounted(async (): Promise<void> => {
  await loadTemplates()
})
</script>
