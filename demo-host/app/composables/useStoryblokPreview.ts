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

const STORYBLOK_CDN_BASES: Record<string, string> = {
  eu: 'https://api.storyblok.com',
  us: 'https://api-us.storyblok.com',
  ap: 'https://api-ap.storyblok.com',
  ca: 'https://api-ca.storyblok.com',
  cn: 'https://api-cn.storyblok.com',
}

export function storyblokCdnBase(region?: string | null): string {
  return STORYBLOK_CDN_BASES[region ?? 'eu'] ?? STORYBLOK_CDN_BASES.eu
}

export function isStoryblokVisualEditor(routeQuery: Record<string, unknown>): boolean {
  return '_storyblok' in routeQuery
}

export async function fetchStoryblokDraftContent(
  token: string,
  region?: string | null,
): Promise<Record<string, unknown> | null> {
  const base: string = storyblokCdnBase(region)
  const response = await $fetch<{ story?: { content?: Record<string, unknown> } }>(
    `${base}/v2/cdn/stories/home`,
    {
      query: {
        token,
        version: 'draft',
      },
    },
  )
  return response.story?.content ?? null
}

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

    const initBridge = (): void => {
      if (!window.StoryblokBridge) {
        return
      }

      const bridge = new window.StoryblokBridge()
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

    const script = document.querySelector('script[src*="storyblok-v2-latest.js"]')
    if (script) {
      script.addEventListener('load', initBridge, { once: true })
    }
  })
}
