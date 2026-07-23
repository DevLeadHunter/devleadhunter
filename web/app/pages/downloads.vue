<template>
  <section class="mx-auto max-w-3xl px-5 pt-14 pb-24 text-[#1b1813] md:px-8 md:pt-20 md:pb-32">
    <div class="space-y-10">
      <div class="space-y-5">
        <p
          class="font-label flex items-center gap-2 text-[0.65rem] font-medium tracking-[0.18em] text-[#6b6355] uppercase"
        >
          <LandingAsterisk class="text-[0.7rem] text-[#e8a33c]" />
          Application de bureau
        </p>
        <h1 class="font-display text-4xl leading-[1.06] font-semibold tracking-[-0.015em] md:text-5xl">
          Installez DevLeadHunter sur votre ordinateur
        </h1>
        <p class="max-w-xl text-lg leading-relaxed text-[#6b6355]">
          Téléchargez l'application pour Windows ou macOS. Elle se connecte à votre compte DevLeadHunter et à l'API
          hébergée — aucun serveur local requis.
        </p>
      </div>

      <div v-if="pending" class="rounded-2xl border border-[#e3dccd] bg-[#fcfaf5] p-6 text-sm text-[#6b6355]">
        Récupération des installateurs depuis GitHub…
      </div>

      <div v-else-if="error" class="space-y-4 rounded-2xl border border-[#bf4d33]/30 bg-[#bf4d33]/10 p-6">
        <p class="font-medium text-[#bf4d33]">Impossible de charger les téléchargements</p>
        <p class="text-sm text-[#6b6355]">{{ String(error) }}</p>
        <button
          type="button"
          class="inline-flex cursor-pointer items-center rounded-full border border-[#1b1813] px-5 py-2 text-sm font-semibold text-[#1b1813] transition-colors hover:bg-[#1b1813] hover:text-[#fcfaf5]"
          @click="refresh()"
        >
          Réessayer
        </button>
      </div>

      <template v-else>
        <div v-if="releaseVersionLabel" class="font-label text-xs tracking-wide text-[#6b6355]">
          Dernière version : <span class="text-[#1b1813]">{{ releaseVersionLabel }}</span>
        </div>

        <section v-if="windowsDownloads.length" class="space-y-4">
          <h2 class="font-display text-2xl font-semibold">Windows</h2>
          <div class="space-y-3">
            <a
              v-for="item in windowsDownloads"
              :key="item.id"
              :href="item.asset.browser_download_url"
              class="block rounded-2xl border border-[#e3dccd] bg-[#fcfaf5] p-5 transition-colors hover:border-[#1b1813]"
              target="_blank"
              rel="noopener noreferrer"
            >
              <p class="font-semibold text-[#1b1813]">{{ item.label }}</p>
              <p class="mt-1 text-sm text-[#6b6355]">{{ item.description }}</p>
              <p v-if="item.asset.size" class="font-label mt-2 text-xs text-[#6b6355]">
                {{ formatBytes(item.asset.size) }}
              </p>
            </a>
          </div>
        </section>

        <section v-if="macDownloads.length" class="space-y-4">
          <h2 class="font-display text-2xl font-semibold">macOS</h2>
          <div class="space-y-3">
            <a
              v-for="item in macDownloads"
              :key="item.id"
              :href="item.asset.browser_download_url"
              class="block rounded-2xl border border-[#e3dccd] bg-[#fcfaf5] p-5 transition-colors hover:border-[#1b1813]"
              target="_blank"
              rel="noopener noreferrer"
            >
              <p class="font-semibold text-[#1b1813]">{{ item.label }}</p>
              <p class="mt-1 text-sm text-[#6b6355]">{{ item.description }}</p>
              <p v-if="item.asset.size" class="font-label mt-2 text-xs text-[#6b6355]">
                {{ formatBytes(item.asset.size) }}
              </p>
            </a>
          </div>
        </section>

        <p v-if="!windowsDownloads.length && !macDownloads.length" class="text-sm text-[#6b6355]">
          Aucun installateur de bureau dans la dernière version GitHub pour l'instant.
        </p>
      </template>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { DesktopDownload, GithubRelease, ReleaseAsset } from '~/types/DownloadsPage'
import type { ComputedRef } from 'vue'

definePageMeta({
  layout: 'marketing',
})

const runtime = useRuntimeConfig()

const repoSlug: ComputedRef<string> = computed(
  (): string => (runtime.public.githubRepo as string | undefined)?.trim() || 'DevLeadHunter/devleadhunter',
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
function classifyAsset(asset: ReleaseAsset): DesktopDownload | null {
  const n: string = asset.name

  if (/\.msi$/i.test(n)) {
    return {
      id: n,
      asset,
      platform: 'windows',
      sortKey: 20,
      label: 'Windows x64 — installateur MSI',
      description: 'Paquet MSI pour les environnements Windows administrés.',
    }
  }

  if (/\.exe$/i.test(n)) {
    const isSetup: boolean = /setup\.exe$/i.test(n) || /-setup\.exe$/i.test(n)
    return {
      id: n,
      asset,
      platform: 'windows',
      sortKey: isSetup ? 10 : 15,
      label: isSetup ? 'Windows x64 — installateur (recommandé)' : 'Windows x64 — installateur',
      description: 'Installateur standard pour Windows 10/11 (64 bits).',
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
      description: appleSilicon ? 'Pour les Mac Apple Silicon (M1 et suivants).' : 'Pour les Mac Intel.',
    }
  }

  return null
}

/**
 * Sort download rows for stable UI ordering.
 * @param items - Parsed download rows.
 * @returns Sorted copy of the input list.
 */
function sortItems(items: DesktopDownload[]): DesktopDownload[] {
  return [...items].sort(
    (a: DesktopDownload, b: DesktopDownload): number => a.sortKey - b.sortKey || a.label.localeCompare(b.label),
  )
}

const windowsDownloads: ComputedRef<DesktopDownload[]> = computed((): DesktopDownload[] => {
  const items: DesktopDownload[] = (release.value?.assets ?? [])
    .map(classifyAsset)
    .filter((x: DesktopDownload | null): x is DesktopDownload => Boolean(x && x.platform === 'windows'))
  return sortItems(items)
})

const macDownloads: ComputedRef<DesktopDownload[]> = computed((): DesktopDownload[] => {
  const items: DesktopDownload[] = (release.value?.assets ?? [])
    .map(classifyAsset)
    .filter((x: DesktopDownload | null): x is DesktopDownload => Boolean(x && x.platform === 'macos'))
  return sortItems(items)
})

const releaseVersionLabel: ComputedRef<string> = computed((): string => {
  const r: GithubRelease | null = release.value ?? null
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
  title: 'Télécharger DevLeadHunter Desktop',
  description: "Téléchargez l'application de bureau DevLeadHunter pour Windows et macOS.",
})
</script>
