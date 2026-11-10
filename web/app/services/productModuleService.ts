import type {
  AdminProductModule,
  AdminProductModuleUpdate,
  EnabledProductModule,
  ProductModuleKey,
} from '~/types/ProductModule'
import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/product-modules'
const ADMIN_BASE_URL: string = '/api/v1/admin/product-modules'

/** The product modules as the API sees them: which are installed, which are switched on. */
export class ProductModuleService {
  /**
   * List the modules installed and switched on (the websites module is not listed: it is always there).
   * @returns The enabled modules.
   */
  static async listEnabled(): Promise<EnabledProductModule[]> {
    return ApiClient.get<EnabledProductModule[]>(BASE_URL)
  }

  /**
   * List every module for the super admin: websites first, then the installed ones, then switches left uninstalled.
   * @returns The modules with their state.
   */
  static async listForAdmin(): Promise<AdminProductModule[]> {
    return ApiClient.get<AdminProductModule[]>(ADMIN_BASE_URL)
  }

  /**
   * Switch a module on or off (super admin).
   * @param moduleKey - The module to switch.
   * @param isEnabled - Whether it should be on.
   * @returns The module as saved.
   */
  static async setEnabled(moduleKey: ProductModuleKey, isEnabled: boolean): Promise<AdminProductModule> {
    const body: AdminProductModuleUpdate = { is_enabled: isEnabled }
    return ApiClient.patch<AdminProductModule>(`${ADMIN_BASE_URL}/${encodeURIComponent(moduleKey)}`, body)
  }
}
