export type ReleaseAsset = {
  id?: number
  name: string
  browser_download_url: string
  size?: number
}

export type GithubRelease = {
  tag_name: string
  name?: string
  assets: ReleaseAsset[]
}

export type DesktopDownload = {
  id: string
  asset: ReleaseAsset
  label: string
  description: string
  platform: 'windows' | 'macos'
  sortKey: number
}
