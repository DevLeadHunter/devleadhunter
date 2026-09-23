<template>
  <div class="max-w-3xl space-y-8">
    <div>
      <p class="app-label flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Prospection
      </p>
      <h1 class="app-page-title mt-2">Vidéo de prospection</h1>
      <p class="text-muted mt-2 max-w-2xl text-sm leading-relaxed">
        Un clip webcam enregistré une seule fois. Chaque site démo génère ensuite sa vidéo personnalisée, prête pour vos
        emails.
      </p>
    </div>

    <PresenterVideoConfig />
    <AssistantPresenterClipCard />
    <StoryblokConnectionCard />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: 'auth' })
</script>
