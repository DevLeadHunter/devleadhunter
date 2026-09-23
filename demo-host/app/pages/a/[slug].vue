<template>
  <div class="a-page" :style="accentStyle">
    <div v-if="pending" class="a-message">Chargement…</div>
    <div v-else-if="!assistant" class="a-message a-message--error">Assistant introuvable ou inactif.</div>
    <template v-else>
      <header class="a-top">
        <div class="a-logo">{{ assistant.business_name }}</div>
        <span class="a-live"><span class="a-live__dot" />En ligne</span>
      </header>
      <main class="a-hero">
        <p class="a-eyebrow">Assistant en ligne</p>
        <h1>{{ assistant.business_name }}</h1>
        <p class="a-lead">
          Posez votre question à {{ assistant.assistant_name }}, en bas à droite. Réponse immédiate, 24h/24.
        </p>

        <ul class="a-values">
          <li class="a-value">
            <span class="a-value__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <div>
              <p class="a-value__title">Disponible 24h/24</p>
              <p class="a-value__text">
                {{ assistant.assistant_name }} répond en quelques secondes, jour et nuit, même quand c'est fermé.
              </p>
            </div>
          </li>
          <li class="a-value">
            <span class="a-value__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" stroke-linecap="round" />
              </svg>
            </span>
            <div>
              <p class="a-value__title">Dans la langue du visiteur</p>
              <p class="a-value__text">Il détecte la langue et répond en {{ languagesLabel }}.</p>
            </div>
          </li>
          <li class="a-value">
            <span class="a-value__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path
                  d="M20 8v6a2 2 0 0 1-2 2H8l-4 3V6a2 2 0 0 1 2-2h8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path d="M17 3v5M19.5 5.5h-5" stroke-linecap="round" />
              </svg>
            </span>
            <div>
              <p class="a-value__title">Capte vos clients</p>
              <p class="a-value__text">Il note leurs coordonnées et leur besoin, et vous les recevez aussitôt.</p>
            </div>
          </li>
        </ul>

        <p class="a-cue">Essayez : posez-lui une question, en bas à droite →</p>
      </main>
      <AssistantChat :config="assistant" />
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed, onMounted } from 'vue'
import type { AiAssistantConfig } from '~/types/AiAssistant'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'
import { useDemoTracking } from '~/composables/useDemoTracking'

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

const { data: assistant, pending }: Awaited<ReturnType<typeof useAsyncData<AiAssistantConfig | null | undefined>>> =
  await useAsyncData<AiAssistantConfig | null>(
    () => `assistant-${slug.value}`,
    async (): Promise<AiAssistantConfig | null> => {
      try {
        return await $fetch<AiAssistantConfig>(`${config.public.apiBase}/api/v1/ai-assistants/public/${slug.value}`)
      } catch {
        return null
      }
    },
  )

/** French names of the languages the widget can speak, for the value section. */
const LANGUAGE_NAMES: Record<string, string> = {
  fr: 'français',
  nl: 'néerlandais',
  de: 'allemand',
  en: 'anglais',
  lu: 'luxembourgeois',
  it: 'italien',
  es: 'espagnol',
}

/** The assistant's languages as a natural French list (« français, néerlandais et anglais »). */
const languagesLabel: ComputedRef<string> = computed((): string => {
  const names: string[] = (assistant.value?.languages ?? []).map((code: string): string => LANGUAGE_NAMES[code] ?? code)
  if (names.length === 0) return 'plusieurs langues'
  if (names.length === 1) return names[0] ?? 'plusieurs langues'
  return `${names.slice(0, -1).join(', ')} et ${names[names.length - 1]}`
})

/** Bind the business's own accent colour to the page (falls back to the editorial gold). */
const accentStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => ({
  '--a-accent': assistant.value?.accent_color || '#a9793f',
}))

const { init: initTracking }: ReturnType<typeof useDemoTracking> = useDemoTracking()

onMounted((): void => {
  const current: AiAssistantConfig | null | undefined = assistant.value
  if (!current) return
  void initTracking(current.slug, current.status, null, DemoBeaconUtils.channelFromQuery(route.query.src))
})

useHead({
  title: computed((): string => assistant.value?.business_name ?? 'Assistant'),
  link: [
    {
      rel: 'stylesheet',
      href: 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap',
    },
  ],
})
</script>

<style scoped>
.a-page {
  min-height: 100dvh;
  background: #f7f3ec;
  color: #17130d;
  font-family: 'Inter', system-ui, sans-serif;
  display: flex;
  flex-direction: column;
}
.a-message {
  margin: auto;
  color: #6d665b;
  font-size: 0.95rem;
}
.a-message--error {
  color: #9f3a2f;
}
.a-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(23, 19, 13, 0.07);
  padding: 22px 24px;
}
.a-logo {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.4rem;
  font-weight: 600;
}
.a-live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.75rem;
  font-weight: 500;
  color: #6d665b;
  white-space: nowrap;
}
.a-live__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--a-accent);
  box-shadow: 0 0 0 0 var(--a-accent);
  animation: a-pulse 2.4s ease-out infinite;
}
@keyframes a-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--a-accent) 45%, transparent);
  }
  70% {
    box-shadow: 0 0 0 7px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}
.a-hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 72px 24px;
}
.a-eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #a9793f;
}
.a-hero h1 {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  font-size: clamp(2.4rem, 6vw, 3.8rem);
  line-height: 1.04;
  margin: 16px 0 18px;
  text-wrap: balance;
}
.a-lead {
  margin: 0;
  font-size: 1.06rem;
  color: #6d665b;
  max-width: 46ch;
}
.a-values {
  list-style: none;
  margin: 44px 0 0;
  padding: 0;
  display: grid;
  gap: 22px 32px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.a-value {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.a-value__icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  color: var(--a-accent);
  background: color-mix(in srgb, var(--a-accent) 12%, #fff);
}
.a-value__icon svg {
  width: 20px;
  height: 20px;
}
.a-value__title {
  margin: 2px 0 4px;
  font-size: 0.92rem;
  font-weight: 600;
  color: #17130d;
}
.a-value__text {
  margin: 0;
  font-size: 0.86rem;
  line-height: 1.5;
  color: #6d665b;
}
.a-cue {
  margin: 40px 0 0;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--a-accent);
}
@media (max-width: 640px) {
  .a-hero {
    padding: 40px 24px 132px;
  }
  .a-values {
    grid-template-columns: 1fr;
    gap: 18px;
    margin-top: 32px;
  }
  .a-cue {
    margin-top: 28px;
  }
}
</style>
