/** A category of the bucket's objects, read from the key prefix: a core one, or one a product module declares. */
export type StorageObjectKind = string

/** How the storage page previews a category: a video player, an image, or nothing. */
export type StorageKindMedia = 'video' | 'image' | 'file'

/** How the storage page names, filters and previews one category (`kinds` of the listing, core first). */
export type StorageKind = {
  kind: StorageObjectKind
  label: string
  filter_prefix: string | null
  filter_label: string
  media: StorageKindMedia
}

export type StorageObject = {
  key: string
  kind: StorageObjectKind
  size: number
  last_modified: string | null
  url: string
  slug: string | null
  prospect_name: string | null
  expires_in_days: number | null
  is_expired: boolean
  ttl_pending: boolean
}

export type StorageListResponse = {
  bucket: string
  public_base_url: string
  kinds: StorageKind[]
  items: StorageObject[]
  total: number
  total_size: number
  ttl_days: number
}

export type StorageUploadResponse = {
  key: string
  url: string
  kind: StorageObjectKind
  size: number
  message: string
}

export type StorageHealthResponse = {
  orphan_objects: string[]
  missing_objects: string[]
  expired_objects: string[]
}

export type StorageActionResponse = {
  deleted: number
  copied: number
  unchanged: number
  message: string
}
