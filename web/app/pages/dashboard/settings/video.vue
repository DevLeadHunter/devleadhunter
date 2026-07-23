<template>
  <div class="mx-auto max-w-2xl space-y-8">
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Vidéo de prospection</h1>
      <p class="text-muted mt-2 text-sm leading-relaxed">
        Un clip webcam enregistré une seule fois. Chaque site démo génère ensuite sa vidéo personnalisée, prête pour vos
        emails.
      </p>
    </div>

    <PresenterVideoConfig />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: 'auth' })
</script>
