/** A product module's key as the API stores it: `websites` (the core), or a key of `product-modules.json`. */
export type ProductModuleKey = string

/** A module the API lists as installed and switched on (`GET /api/v1/product-modules`). */
export type EnabledProductModule = {
  key: ProductModuleKey
  label: string
}

/** One row of the super admin's module list (`GET /api/v1/admin/product-modules`). */
export type AdminProductModule = {
  key: ProductModuleKey
  label: string
  description: string
  is_installed: boolean
  is_enabled: boolean
  is_switchable: boolean
  load_error: string | null
  updated_at: string | null
}

/** Body of `PATCH /api/v1/admin/product-modules/{key}`. */
export type AdminProductModuleUpdate = {
  is_enabled: boolean
}
