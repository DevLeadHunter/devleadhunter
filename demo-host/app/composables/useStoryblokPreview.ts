type StoryblokBridgeEvent = {
  story?: {
    content?: Record<string, unknown>
  }
}

type StoryblokBridgeInstance = {
  on: (events: string[], callback: (event: StoryblokBridgeEvent) => void) => void
}

declare global {
  interface Window {
    StoryblokBridge?: new () => StoryblokBridgeInstance
  }
}

const STORYBLOK_EU_CDN_BASE: string = 'https://api.storyblok.com'

const STORYBLOK_CDN_BASES: Record<string, string> = {
  eu: STORYBLOK_EU_CDN_BASE,
  us: 'https://api-us.storyblok.com',
  ap: 'https://api-ap.storyblok.com',
  ca: 'https://api-ca.storyblok.com',
  cn: 'https://api-cn.storyblok.com',
}

/**
 * Resolve the Storyblok CDN host for a space region.
 *
 * @param region - Space region code, defaulting to `eu`.
 * @returns The CDN base URL, falling back to the EU one for an unknown region.
 */
export function storyblokCdnBase(region?: string | null): string {
  return STORYBLOK_CDN_BASES[region ?? 'eu'] ?? STORYBLOK_EU_CDN_BASE
}

/**
 * Tell whether the page is being rendered inside the Storyblok Visual Editor iframe.
 *
 * @param routeQuery - Current route query.
 * @returns Whether Storyblok added its `_storyblok` marker.
 */
export function isStoryblokVisualEditor(routeQuery: Record<string, unknown>): boolean {
  return '_storyblok' in routeQuery
}

/**
 * Fetch the unpublished `home` story so the editor previews its pending edits.
 *
 * @param token - Space preview token.
 * @param region - Space region code.
 * @returns The draft content, or null when the story carries none.
 */
export async function fetchStoryblokDraftContent(
  token: string,
  region?: string | null,
): Promise<Record<string, unknown> | null> {
  const base: string = storyblokCdnBase(region)
  const response: { story?: { content?: Record<string, unknown> | undefined } | undefined } = await $fetch<{
    story?: { content?: Record<string, unknown> }
  }>(`${base}/v2/cdn/stories/home`, {
    query: {
      token,
      version: 'draft',
    },
  })
  return response.story?.content ?? null
}

/**
 * Load the Storyblok bridge script in the editor and relay every live content edit.
 *
 * @param enabled - Whether the page runs inside the Visual Editor.
 * @param onContentChange - Called with the edited content on each bridge event.
 */
export function useStoryblokBridge(
  enabled: Ref<boolean>,
  onContentChange: (content: Record<string, unknown>) => void,
): void {
  useHead(() => ({
    script: enabled.value
      ? [
          {
            key: 'storyblok-bridge',
            src: 'https://app.storyblok.com/f/storyblok-v2-latest.js',
            defer: true,
            tagPosition: 'bodyClose',
          },
        ]
      : [],
  }))

  onMounted((): void => {
    if (!enabled.value) {
      return
    }

    const initBridge: () => void = (): void => {
      if (!window.StoryblokBridge) {
        return
      }

      const bridge: StoryblokBridgeInstance = new window.StoryblokBridge()
      bridge.on(['input', 'published', 'change'], (event: StoryblokBridgeEvent): void => {
        if (event.story?.content) {
          onContentChange(event.story.content)
        }
      })
    }

    if (window.StoryblokBridge) {
      initBridge()
      return
    }

    const script: Element | null = document.querySelector('script[src*="storyblok-v2-latest.js"]')
    if (script) {
      script.addEventListener('load', initBridge, { once: true })
    }
  })
}
