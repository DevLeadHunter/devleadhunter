<template>
  <div class="max-w-3xl space-y-8">
    <UiPageHeader
      eyebrow="Prospection"
      title="Vidéo de prospection"
      description="Un clip webcam par module, enregistré une seule fois. Chaque site démo et chaque réceptionniste génère ensuite sa vidéo personnalisée, prête pour vos emails."
    />

    <PresenterVideoConfig />
    <div id="clip-receptionniste" class="border-t border-[var(--app-line)] pt-8">
      <PresenterVideoConfig module="ai-assistant" />
    </div>
    <StoryblokConnectionCard />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: 'auth' })
</script>
