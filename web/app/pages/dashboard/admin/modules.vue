<template>
  <div class="space-y-5">
    <UiPageHeader
      eyebrow="Administration"
      title="Modules"
      description="Les modules installés, et leur interrupteur. Un module coupé disparaît du menu, ses pages ferment et ses envois s'arrêtent."
    >
      <template #actions>
        <button
          type="button"
          class="app-btn-secondary h-11 px-4 text-sm whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50 @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          :disabled="isLoading"
          @click="loadModules"
        >
          <UIcon name="i-lucide-refresh-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
      </template>
    </UiPageHeader>

    <UiCallout v-if="loadErrorMessage" variant="danger">{{ loadErrorMessage }}</UiCallout>

    <UiLoader v-if="isLoading && modules.length === 0" label="Lecture des modules…" />

    <div v-else-if="modules.length > 0" class="space-y-2">
      <div v-for="productModule in modules" :key="productModule.key" class="app-card space-y-3 px-4 py-3.5">
        <div class="flex items-center gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
            <UIcon :name="moduleIcon(productModule)" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <div class="min-w-0 flex-1">
            <p class="flex flex-wrap items-center gap-2 text-sm font-semibold text-[var(--app-ink)]">
              {{ productModule.label }}
              <span v-if="!productModule.is_switchable" class="app-badge app-badge--success">Toujours actif</span>
              <span v-else-if="!productModule.is_installed" class="app-badge">Non installé</span>
              <span v-else-if="productModule.load_error" class="app-badge app-badge--danger">Erreur</span>
            </p>
            <p v-if="productModule.description" class="mt-0.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              {{ productModule.description }}
            </p>
            <p v-if="productModule.updated_at" class="mt-0.5 text-[11px] text-[var(--app-faint)]">
              Modifié le {{ formatNumericDateTime(productModule.updated_at) }}
            </p>
          </div>
          <div v-if="productModule.is_switchable" class="flex shrink-0 items-center gap-2">
            <UIcon
              v-if="switchingModuleKey === productModule.key"
              name="i-lucide-loader-circle"
              class="h-3.5 w-3.5 animate-spin text-[var(--app-ink-soft)]"
            />
            <UiSwitch
              :id="`product-module-${productModule.key}`"
              :model-value="productModule.is_enabled"
              :disabled="!productModule.is_installed || switchingModuleKey !== null"
              @update:model-value="switchModule(productModule, $event)"
            />
          </div>
        </div>

        <UiCallout v-if="!productModule.is_installed" variant="info">
          Son code n'est pas installé sur le serveur : l'interrupteur est gardé, mais rien ne tourne.
        </UiCallout>
        <UiCallout v-if="productModule.load_error" variant="danger">
          Le module n'a pas pu se charger : {{ productModule.load_error }}
        </UiCallout>
      </div>
    </div>

    <UiEmptyState v-else-if="!loadErrorMessage" title="Aucun module" description="L'API n'a listé aucun module." />
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type { AdminProductModule } from '~/types/ProductModule'
import type { DashboardModuleDefinition } from '~/types/UiSidebar'
import { onMounted, ref } from 'vue'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { ProductModuleService } from '~/services/productModuleService'
import { useModuleStore } from '~/stores/moduleStore'
import { useToast } from '~/composables/useToast'
import { DashboardModuleRegistry } from '~/utils/dashboardModuleRegistry'
import { WEBSITES_DASHBOARD_MODULE } from '~/utils/dashboardModules'
import { formatNumericDateTime } from '~/utils/date'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'super-admin'] })

useSeoMeta({ title: 'Modules — DevLeadHunter' })

const UNKNOWN_MODULE_ICON: string = 'i-lucide-blocks'

const toast: UseToastReturn = useToast()
const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()

const modules: Ref<AdminProductModule[]> = ref([])
const isLoading: Ref<boolean> = ref(true)
const loadErrorMessage: Ref<string> = ref('')
/** The module whose switch is being saved: one at a time. */
const switchingModuleKey: Ref<string | null> = ref(null)

/**
 * The icon a module shows in the switcher, or a generic one when no layer registered it.
 * @param productModule - The module row.
 * @returns A Lucide icon name.
 */
function moduleIcon(productModule: AdminProductModule): string {
  if (productModule.key === WEBSITES_MODULE_KEY) {
    return WEBSITES_DASHBOARD_MODULE.icon
  }
  const definition: DashboardModuleDefinition | null = DashboardModuleRegistry.find(productModule.key)
  return definition?.icon ?? UNKNOWN_MODULE_ICON
}

/**
 * Load every module with its state.
 * @returns A promise resolved once the list is shown, or the failure is.
 */
async function loadModules(): Promise<void> {
  isLoading.value = true
  loadErrorMessage.value = ''
  try {
    modules.value = await ProductModuleService.listForAdmin()
  } catch (err: unknown) {
    loadErrorMessage.value = err instanceof Error ? err.message : 'Impossible de lire les modules'
  } finally {
    isLoading.value = false
  }
}

/**
 * Switch a module on or off, then let the module switcher catch up.
 * @param productModule - The module switched.
 * @param isEnabled - Its new state.
 * @returns A promise resolved once saved, or the failure is reported.
 */
async function switchModule(productModule: AdminProductModule, isEnabled: boolean): Promise<void> {
  if (switchingModuleKey.value !== null) {
    return
  }
  switchingModuleKey.value = productModule.key
  try {
    const savedModule: AdminProductModule = await ProductModuleService.setEnabled(productModule.key, isEnabled)
    modules.value = modules.value.map(
      (listedModule: AdminProductModule): AdminProductModule =>
        listedModule.key === savedModule.key ? savedModule : listedModule,
    )
    toast.success(savedModule.is_enabled ? `« ${savedModule.label} » est activé` : `« ${savedModule.label} » est coupé`)
    await moduleStore.refreshEnabledModules()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Le changement n’a pas été enregistré')
  } finally {
    switchingModuleKey.value = null
  }
}

onMounted(async (): Promise<void> => {
  await loadModules()
})
</script>
