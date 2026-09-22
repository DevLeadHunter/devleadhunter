<template>
  <div class="a-page">
    <div v-if="pending" class="a-message">Chargement…</div>
    <div v-else-if="!assistant" class="a-message a-message--error">Assistant introuvable ou inactif.</div>
    <template v-else>
      <header class="a-top">
        <div class="a-logo">{{ assistant.business_name }}</div>
      </header>
      <main class="a-hero">
        <p class="a-eyebrow">Assistant en ligne</p>
        <h1>{{ assistant.business_name }}</h1>
        <p class="a-lead">
          Posez votre question à {{ assistant.assistant_name }}, en bas à droite. Réponse immédiate, 24h/24.
        </p>
      </main>
      <AssistantChat :config="assistant" />
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import type { AiAssistantConfig } from '~/types/AiAssistant'

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
  border-bottom: 1px solid rgba(23, 19, 13, 0.07);
  padding: 22px 24px;
}
.a-logo {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.4rem;
  font-weight: 600;
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
</style>
