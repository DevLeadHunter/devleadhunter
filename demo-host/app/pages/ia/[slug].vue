<template>
  <div class="ia-page" :style="accentStyle">
    <p v-if="pending" class="ia-page__message">Chargement…</p>
    <p v-else-if="!assistant" class="ia-page__message ia-page__message--error">Cette page n'est plus disponible.</p>
    <AssistantBusinessPage v-else-if="isSold" :assistant="assistant" />
    <AssistantDemoPage v-else :assistant="assistant" />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import AssistantBusinessPage from '~/components/AssistantBusinessPage.vue'
import AssistantDemoPage from '~/components/AssistantDemoPage.vue'
import type { AiAssistantConfig } from '~/types/AiAssistant'
import type { AssistantAccentPalette } from '~/utils/AssistantAccentUtils'
import { AssistantAccentUtils } from '~/utils/AssistantAccentUtils'
import { BusinessNameUtils } from '~/utils/BusinessNameUtils'

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const { data: assistant, pending }: Awaited<ReturnType<typeof useAsyncData<AiAssistantConfig | null>>> =
  await useAsyncData(
    (): string => `assistant-${routeSlug()}`,
    async (): Promise<AiAssistantConfig | null> => {
      try {
        return await $fetch<AiAssistantConfig>(`${config.public.apiBase}/api/v1/ai-assistants/public/${routeSlug()}`)
      } catch {
        return null
      }
    },
  )

/** Once sold, the address leads the business's customers to their page: the demo is for the business only. */
const isSold: ComputedRef<boolean> = computed((): boolean => assistant.value?.status === 'delivered')

const palette: ComputedRef<AssistantAccentPalette> = computed((): AssistantAccentPalette =>
  AssistantAccentUtils.palette(assistant.value?.accent_color),
)

const accentStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => ({
  '--a-accent': palette.value.accent,
  '--a-accent-strong': palette.value.strong,
  '--a-accent-text': palette.value.text,
}))

const businessName: ComputedRef<string> = computed((): string =>
  BusinessNameUtils.short(assistant.value?.business_name ?? ''),
)

const pageTitle: ComputedRef<string> = computed((): string => {
  if (!businessName.value) return 'Réceptionniste IA'
  return isSold.value ? `${businessName.value} : demande de devis et rendez-vous` : businessName.value
})

const businessDescription: ComputedRef<string | undefined> = computed((): string | undefined => {
  if (!isSold.value || !assistant.value) return undefined
  const lead: string = `${businessName.value}${tradePhrase(assistant.value.trade_label ?? null, assistant.value.city ?? null)}`
  return `${lead}. Posez votre question, envoyez une photo ou demandez un rendez-vous, même en dehors des horaires.`
})

/**
 * The assistant's slug, as the address names it.
 * @returns The slug.
 */
function routeSlug(): string {
  return String(route.params.slug ?? '')
}

/**
 * What follows the business's name in a sentence (« , couvreur à Rennes », « à Rennes »).
 * @param tradeLabel - The Google Maps category, or null.
 * @param city - The town, or null.
 * @returns The phrase, empty when both are unknown.
 */
function tradePhrase(tradeLabel: string | null, city: string | null): string {
  const trade: string = (tradeLabel ?? '').trim()
  const town: string = (city ?? '').trim()
  const place: string = town ? ` à ${town}` : ''
  if (!trade) return place
  return `, ${trade.charAt(0).toLocaleLowerCase('fr-FR')}${trade.slice(1)}${place}`
}

useSeoMeta({
  title: (): string => pageTitle.value,
  ogTitle: (): string => pageTitle.value,
  description: (): string | undefined => businessDescription.value,
  ogDescription: (): string | undefined => businessDescription.value,
  robots: (): string => (isSold.value ? 'index, follow' : 'noindex'),
  themeColor: (): string | undefined => (isSold.value ? palette.value.accent : undefined),
})
</script>

<style scoped>
.ia-page {
  --ia-paper: #f7f3ec;
  --ia-card: #fffdf9;
  --ia-ink: #17130d;
  --ia-ink-dim: #6d665b;
  --ia-line: rgba(23, 19, 13, 0.14);
  --ia-line-soft: rgba(23, 19, 13, 0.07);
  --ia-font-display: 'Fraunces', Georgia, serif;
  --ia-font-body: 'Inter', system-ui, sans-serif;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--ia-paper);
  color: var(--ia-ink);
  font-family: var(--ia-font-body);
  font-size: 15px;
  line-height: 1.5;
}
.ia-page__message {
  margin: auto;
  color: var(--ia-ink-dim);
}
.ia-page__message--error {
  color: #9f3a2f;
}
</style>
