<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Configuration d'envoi</h1>
      <p class="text-muted mt-2 text-sm">
        Choisissez et configurez la méthode d'envoi de vos emails de prospection : votre domaine (via Resend) ou Gmail.
      </p>
    </div>

    <EmailSendingConfig />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: ['auth'] })
</script>
