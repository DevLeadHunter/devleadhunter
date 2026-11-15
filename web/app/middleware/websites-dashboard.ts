import { WEBSITES_DASHBOARD_PATH } from '~/constants/productModules'
import { useModuleStore } from '~/stores/moduleStore'

/** The dashboard shows the websites module's figures: with another module open, it leads to that module's home. */
export default defineNuxtRouteMiddleware((): ReturnType<typeof navigateTo> | undefined => {
  if (import.meta.server) {
    return undefined
  }
  const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()
  moduleStore.initFromStorage()
  const activeModuleHome: string = moduleStore.activeModule.home

  if (activeModuleHome === WEBSITES_DASHBOARD_PATH) {
    return undefined
  }
  return navigateTo(activeModuleHome, { replace: true })
})
