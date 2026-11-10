import { WEBSITES_PRESENTER_VIDEO_ADAPTER } from '~/services/websitesPresenterVideoAdapter'
import { PresenterVideoAdapterRegistry } from '~/utils/presenterVideoAdapterRegistry'

/** The core registers its own websites module in the registries the product module layers also fill. */
export default defineNuxtPlugin((): void => {
  PresenterVideoAdapterRegistry.register(WEBSITES_PRESENTER_VIDEO_ADAPTER)
})
