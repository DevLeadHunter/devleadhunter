<template>
  <div class="min-h-screen bg-[#050505] px-4 py-10 text-[#f9f9f9]">
    <div class="mx-auto max-w-3xl space-y-8">
      <div class="space-y-3">
        <p class="text-sm font-medium text-blue-400">Desktop application</p>
        <h1 class="text-3xl font-semibold tracking-tight">Install DevLeadHunter on your computer</h1>
        <p class="text-muted leading-relaxed">
          Download the desktop app for Windows or macOS. It connects to your DevLeadHunter account and the hosted API —
          no local server required.
        </p>
      </div>

      <div v-if="pending" class="border-muted text-muted rounded-lg border bg-[#1a1a1a] p-6 text-sm">
        Fetching installers from GitHub…
      </div>

      <div v-else-if="error" class="space-y-4 rounded-lg border border-red-500/30 bg-red-500/10 p-6">
        <p class="font-medium text-red-300">Unable to load downloads</p>
        <p class="text-muted text-sm">{{ String(error) }}</p>
        <button type="button" class="btn-secondary" @click="refresh()">Retry</button>
      </div>

      <template v-else>
        <div v-if="releaseVersionLabel" class="text-muted text-sm">
          Latest release: <span class="font-mono text-[#f9f9f9]">{{ releaseVersionLabel }}</span>
        </div>

        <section v-if="windowsDownloads.length" class="space-y-3">
          <h2 class="text-lg font-semibold">Windows</h2>
          <div class="space-y-3">
            <a
              v-for="item in windowsDownloads"
              :key="item.id"
              :href="item.asset.browser_download_url"
              class="border-muted block rounded-lg border bg-[#1a1a1a] p-4 transition hover:border-blue-500/50"
              target="_blank"
              rel="noopener noreferrer"
            >
              <p class="font-medium">{{ item.label }}</p>
              <p class="text-muted mt-1 text-sm">{{ item.description }}</p>
              <p v-if="item.asset.size" class="text-muted mt-2 text-xs">{{ formatBytes(item.asset.size) }}</p>
            </a>
          </div>
        </section>

        <section v-if="macDownloads.length" class="space-y-3">
          <h2 class="text-lg font-semibold">macOS</h2>
          <div class="space-y-3">
            <a
              v-for="item in macDownloads"
              :key="item.id"
              :href="item.asset.browser_download_url"
              class="border-muted block rounded-lg border bg-[#1a1a1a] p-4 transition hover:border-blue-500/50"
              target="_blank"
              rel="noopener noreferrer"
            >
              <p class="font-medium">{{ item.label }}</p>
              <p class="text-muted mt-1 text-sm">{{ item.description }}</p>
              <p v-if="item.asset.size" class="text-muted mt-2 text-xs">{{ formatBytes(item.asset.size) }}</p>
            </a>
          </div>
        </section>

        <p v-if="!windowsDownloads.length && !macDownloads.length" class="text-muted text-sm">
          No desktop installers found in the latest GitHub release yet.
        </p>
      </template>

      <NuxtLink to="/" class="inline-block text-sm text-blue-400 hover:underline">← Back to home</NuxtLink>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'

type ReleaseAsset = {
  id?: number
  name: string
  browser_download_url: string
  size?: number
}

type GithubRelease = {
  tag_name: string
  name?: string
  assets: ReleaseAsset[]
}

type DownloadItem = {
  id: string
  asset: ReleaseAsset
  label: string
  description: string
  platform: 'windows' | 'macos'
  sortKey: number
}

const runtime = useRuntimeConfig()

const repoSlug: ComputedRef<string> = computed(
  (): string => (runtime.public.githubRepo as string | undefined)?.trim() || 'leogu/devleadhunter',
)
const releaseChannel: ComputedRef<string> = computed(
  (): string => (runtime.public.desktopReleaseChannel as string | undefined)?.trim() || 'latest',
)
const releasesBase: ComputedRef<string> = computed(
  (): string => (runtime.public.githubApiBase as string | undefined)?.trim() || 'https://api.github.com',
)

const {
  data: release,
  pending,
  error,
  refresh,
} = await useAsyncData(
  'devleadhunter-desktop-github-release',
  async (): Promise<GithubRelease> => {
    const base: string = releasesBase.value
    const slug: string = repoSlug.value
    const channel: string = releaseChannel.value

    if (channel === 'latest') {
      try {
        return await $fetch<GithubRelease>(`${base}/repos/${slug}/releases/latest`)
      } catch (e: unknown) {
        const status: number | undefined =
          (e as { status?: number; statusCode?: number })?.status ?? (e as { statusCode?: number })?.statusCode
        if (status !== 404) {
          throw e
        }
        const rows: GithubRelease[] = await $fetch<GithubRelease[]>(`${base}/repos/${slug}/releases`, {
          query: { per_page: '20' },
        })
        const picked: GithubRelease | undefined =
          rows.find((r: GithubRelease): boolean => !('draft' in r) || !(r as { draft?: boolean }).draft) ?? rows[0]
        if (!picked) {
          throw new Error('No published release found on this repository.')
        }
        return picked
      }
    }

    return await $fetch<GithubRelease>(`${base}/repos/${slug}/releases/tags/${encodeURIComponent(channel)}`)
  },
  { watch: [releasesBase, repoSlug, releaseChannel] },
)

/**
 * Map a GitHub release asset to a download row, or skip unsupported extensions.
 * @param asset - Release asset from the GitHub API.
 * @returns Parsed download row, or null when the extension is not supported.
 */
function classifyAsset(asset: ReleaseAsset): DownloadItem | null {
  const n: string = asset.name

  if (/\.msi$/i.test(n)) {
    return {
      id: n,
      asset,
      platform: 'windows',
      sortKey: 20,
      label: 'Windows x64 — MSI installer',
      description: 'MSI package for managed Windows environments.',
    }
  }

  if (/\.exe$/i.test(n)) {
    const isSetup: boolean = /setup\.exe$/i.test(n) || /-setup\.exe$/i.test(n)
    return {
      id: n,
      asset,
      platform: 'windows',
      sortKey: isSetup ? 10 : 15,
      label: isSetup ? 'Windows x64 — installer (recommended)' : 'Windows x64 — installer',
      description: 'Standard Windows installer for Windows 10/11 (64-bit).',
    }
  }

  if (/\.dmg$/i.test(n)) {
    const appleSilicon: boolean = /aarch64|arm64/i.test(n)
    return {
      id: n,
      asset,
      platform: 'macos',
      sortKey: appleSilicon ? 10 : 20,
      label: appleSilicon ? 'macOS — Apple Silicon' : 'macOS — Intel',
      description: appleSilicon ? 'For Macs with Apple Silicon (M1 and later).' : 'For Intel-based Macs.',
    }
  }

  return null
}

/**
 * Sort download rows for stable UI ordering.
 * @param items - Parsed download rows.
 * @returns Sorted copy of the input list.
 */
function sortItems(items: DownloadItem[]): DownloadItem[] {
  return [...items].sort(
    (a: DownloadItem, b: DownloadItem): number => a.sortKey - b.sortKey || a.label.localeCompare(b.label),
  )
}

const windowsDownloads: ComputedRef<DownloadItem[]> = computed((): DownloadItem[] => {
  const items: DownloadItem[] = (release.value?.assets ?? [])
    .map(classifyAsset)
    .filter((x: DownloadItem | null): x is DownloadItem => Boolean(x && x.platform === 'windows'))
  return sortItems(items)
})

const macDownloads: ComputedRef<DownloadItem[]> = computed((): DownloadItem[] => {
  const items: DownloadItem[] = (release.value?.assets ?? [])
    .map(classifyAsset)
    .filter((x: DownloadItem | null): x is DownloadItem => Boolean(x && x.platform === 'macos'))
  return sortItems(items)
})

const releaseVersionLabel: ComputedRef<string> = computed((): string => {
  const r: GithubRelease | null = release.value
  if (!r) {
    return ''
  }
  if (r.name?.trim()) {
    return r.name.trim()
  }
  return r.tag_name ?? ''
})

/**
 * Format a byte size for display.
 * @param n - Size in bytes from the GitHub API.
 * @returns Human-readable label such as `12.4 MB`.
 */
function formatBytes(n?: number): string {
  if (!n || n <= 0) {
    return ''
  }
  const units: string[] = ['B', 'KB', 'MB', 'GB']
  let i: number = 0
  let val: number = n
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024
    i += 1
  }
  return `${val.toFixed(val >= 10 || i === 0 ? 0 : 1)} ${units[i]}`
}

useSeoMeta({
  title: 'Download DevLeadHunter Desktop',
  description: 'Download the DevLeadHunter desktop app for Windows and macOS.',
  robots: 'noindex, nofollow',
})
</script>
