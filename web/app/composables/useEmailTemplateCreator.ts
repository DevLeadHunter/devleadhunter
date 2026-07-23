import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import { useDrawerStackStore } from '~/stores/drawerStack'

type IdentifiableTemplate = {
  id: number
}

export type EmailTemplateCreator = {
  openCreate: (assign?: (templateId: number) => void) => void
}

/**
 * Shared create flow for pages hosting `UiTemplateSelect` (drawer + reload + auto-select).
 * @param templates - Caller's reactive template list.
 * @param reload - Reloads that list in place after a template is saved.
 * @returns Handler to bind to `UiTemplateSelect`'s `@create`.
 */
export function useEmailTemplateCreator<T extends IdentifiableTemplate>(
  templates: Ref<T[]>,
  reload: () => Promise<void>,
): EmailTemplateCreator {
  const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
  const pendingAssign: Ref<((templateId: number) => void) | null> = ref(null)

  /**
   * Open the creation drawer and optionally auto-select the new template id.
   * @param assign - Optional auto-select callback for the new template id.
   */
  function openCreate(assign?: (templateId: number) => void): void {
    pendingAssign.value = assign ?? null
    drawerStack.push({ kind: 'email-template', mode: 'create', template: null })
  }

  watch(
    (): number => drawerStack.emailTemplatesRefreshCounter,
    async (): Promise<void> => {
      const previousIds: Set<number> = new Set<number>(templates.value.map((t: T): number => t.id))
      await reload()
      const assign: ((templateId: number) => void) | null = pendingAssign.value
      if (assign) {
        const created: T | undefined = templates.value.find((t: T): boolean => !previousIds.has(t.id))
        if (created) assign(created.id)
        pendingAssign.value = null
      }
    },
  )

  return { openCreate }
}
