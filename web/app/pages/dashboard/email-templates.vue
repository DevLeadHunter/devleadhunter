<template>
  <div class="space-y-5">
    <UiPageHeader
      eyebrow="Prospection"
      title="Modèles d'email"
      description="Les contenus réutilisés par vos campagnes et relances."
    >
      <template #primary-action>
        <button
          class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:h-9 @2xl:text-xs"
          @click="openCreateDrawer"
        >
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Nouveau modèle
        </button>
      </template>
    </UiPageHeader>

    <div
      class="flex flex-col-reverse gap-3 border-b border-[var(--app-line)] @2xl:flex-row @2xl:items-end @2xl:justify-between @2xl:gap-4"
    >
      <UiFilterTabs v-model="activeCategory" :tabs="categoryTabs" />
      <div class="relative w-full @2xl:mb-2.5 @2xl:w-72">
        <UIcon
          name="i-lucide-search"
          class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
        />
        <input v-model="searchQuery" type="text" placeholder="Rechercher un modèle…" class="input-field pl-9" />
      </div>
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

    <div v-else-if="activeTemplates.length === 0" class="card px-6 py-10 text-center">
      <p v-if="searchQuery.trim()" class="text-muted text-sm">
        Aucun modèle ne correspond à « {{ searchQuery }} » dans cet onglet.
      </p>
      <p v-else class="text-muted text-sm">
        Aucun modèle dans « {{ activeCategoryLabel }} » — créez-en un, ou changez la catégorie d'un modèle existant
        depuis sa fiche.
      </p>
    </div>

    <template v-else>
      <div class="card divide-y divide-[var(--app-line-soft)] overflow-hidden p-0">
        <div
          v-for="template in activeTemplates"
          :key="template.id"
          class="group flex items-start gap-4 px-4 py-3 transition-colors hover:bg-[var(--app-surface-2)]/60"
        >
          <button type="button" class="min-w-0 flex-1 cursor-pointer text-left" @click="openPreviewDrawer(template)">
            <div class="flex flex-wrap items-center gap-2">
              <span
                v-if="isTemplateRecommended(template)"
                class="shrink-0 text-sm leading-none text-[var(--app-accent)]"
                title="Modèle recommandé — épinglé en haut de la liste"
                aria-label="Modèle recommandé"
              >
                ★
              </span>
              <h3
                class="truncate text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors group-hover:decoration-[var(--app-accent)]"
              >
                {{ templateNameWithoutStar(template.name) }}
              </h3>
              <span
                v-if="template.is_fork"
                class="shrink-0 rounded-full border border-[var(--app-line)] bg-[var(--app-surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)]"
              >
                Personnalisé
              </span>
              <span
                v-else-if="template.is_library"
                class="shrink-0 rounded-full border border-[var(--app-line)] bg-[var(--app-surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)]"
              >
                Bibliothèque
              </span>
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

          <div class="flex shrink-0 items-center gap-1">
            <button
              type="button"
              class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              title="Aperçu avec des données d'exemple"
              :aria-label="`Aperçu de ${template.name}`"
              @click="openPreviewDrawer(template)"
            >
              <UIcon name="i-lucide-eye" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              title="Modifier"
              :aria-label="`Modifier ${template.name}`"
              @click="openEditDrawer(template)"
            >
              <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
            </button>

            <div class="relative">
              <button
                type="button"
                class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                title="Plus d'actions"
                :aria-label="`Plus d'actions pour ${template.name}`"
                :aria-expanded="openMenuTemplateId === template.id"
                @click.stop="toggleActionsMenu(template.id)"
              >
                <UIcon name="i-lucide-ellipsis-vertical" class="h-3.5 w-3.5" />
              </button>

              <template v-if="openMenuTemplateId === template.id">
                <div class="fixed inset-0 z-40" @click="openMenuTemplateId = null"></div>
                <div
                  class="absolute right-0 z-50 mt-1.5 w-48 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1 shadow-lg shadow-black/5"
                >
                  <button
                    type="button"
                    class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                    @click="runRowAction(template, duplicateTemplate)"
                  >
                    <UIcon name="i-lucide-copy" class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
                    Dupliquer
                  </button>
                  <button
                    type="button"
                    class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                    @click="runRowAction(template, toggleTemplateActive)"
                  >
                    <UIcon
                      :name="template.is_active ? 'i-lucide-pause' : 'i-lucide-play'"
                      class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]"
                    />
                    {{ template.is_active ? 'Désactiver' : 'Activer' }}
                  </button>
                  <button
                    type="button"
                    class="mt-1 flex w-full cursor-pointer items-center gap-2.5 rounded-lg border-t border-[var(--app-line-soft)] px-2.5 py-2 text-left text-xs font-medium text-[var(--app-red)] transition-colors hover:bg-[var(--app-red-soft)]"
                    @click="runRowAction(template, confirmDelete)"
                  >
                    <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5 shrink-0" />
                    Supprimer
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
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
import type { UiFilterTab } from '~/types/UiFilterTabs'
import type { ComputedRef, Ref } from 'vue'
import type { EmailTemplate, EmailTemplateCategory } from '~/types'
import { computed, onMounted, ref, watch } from 'vue'
import { EmailTemplatesService } from '~/services/emailTemplatesService'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import {
  EMAIL_TEMPLATE_CATEGORIES,
  EMAIL_TEMPLATE_CATEGORY_LABELS,
  isTemplateRecommended,
  templateNameWithoutStar,
} from '~/utils/emailTemplate'

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
/** Template whose overflow menu is open, if any. */
const openMenuTemplateId: Ref<number | null> = ref(null)
const confirmModal: Ref<{ open: () => void; close: () => void } | null> = ref(null)

/** Sequence step currently displayed. */
const activeCategory: Ref<EmailTemplateCategory> = ref('first_email')

/** Templates of the active tab only, before the search filter. */
const categoryTemplates: ComputedRef<EmailTemplate[]> = computed((): EmailTemplate[] =>
  emailTemplates.value.filter((template: EmailTemplate): boolean => template.category === activeCategory.value),
)

/** One tab per sequence step, each badged with how many active templates it holds. */
const categoryTabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] =>
  EMAIL_TEMPLATE_CATEGORIES.map(
    (category: EmailTemplateCategory): UiFilterTab => ({
      key: category,
      label: EMAIL_TEMPLATE_CATEGORY_LABELS[category],
      count: emailTemplates.value.filter(
        (template: EmailTemplate): boolean => template.category === category && template.is_active,
      ).length,
    }),
  ),
)

/** Label of the active tab, used by the empty state. */
const activeCategoryLabel: ComputedRef<string> = computed(
  (): string => EMAIL_TEMPLATE_CATEGORY_LABELS[activeCategory.value],
)

/** Templates of the active tab matching the search query (name or subject). */
const filteredTemplates: ComputedRef<EmailTemplate[]> = computed((): EmailTemplate[] => {
  const query: string = searchQuery.value.trim().toLowerCase()
  if (!query) return categoryTemplates.value
  return categoryTemplates.value.filter(
    (template: EmailTemplate): boolean =>
      template.name.toLowerCase().includes(query) || template.subject.toLowerCase().includes(query),
  )
})

/** Active templates of the current tab (search-filtered), in the API's pinned order. */
const activeTemplates: ComputedRef<EmailTemplate[]> = computed((): EmailTemplate[] =>
  filteredTemplates.value.filter((template: EmailTemplate): boolean => template.is_active),
)

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
 * Hands the drawer the list currently displayed, so it can step to its neighbours.
 * @param template - Template to preview.
 */
function openPreviewDrawer(template: EmailTemplate): void {
  drawerStack.setEmailTemplateBrowseList(activeTemplates.value)
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
      category: template.category,
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
    await loadTemplates()
    toast.success(updated.is_active ? `« ${updated.name} » activé` : `« ${updated.name} » désactivé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  }
}

/**
 * Ask for confirmation before deleting a template.
 * @param template - Template to delete.
 */
/**
 * Open or close the overflow menu of a row.
 * @param templateId - Identifier of the row's template.
 */
function toggleActionsMenu(templateId: number): void {
  openMenuTemplateId.value = openMenuTemplateId.value === templateId ? null : templateId
}

/**
 * Run an overflow-menu action, then close the menu.
 * @param template - Template the action applies to.
 * @param action - Handler to run on that template.
 */
function runRowAction(template: EmailTemplate, action: (template: EmailTemplate) => void): void {
  openMenuTemplateId.value = null
  action(template)
}

/**
 * Ask confirmation before deleting a template.
 * @param template - Template about to be deleted.
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
