export type StorageObjectKind =
  | 'website_video'
  | 'website_thumbnail'
  | 'website_background'
  | 'assistant_video'
  | 'assistant_thumbnail'
  | 'presenter'
  | 'support'
  | 'prospect_photo'
  | 'assistant_photo'
  | 'assistant_document'
  | 'manual'
  | 'other'

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
