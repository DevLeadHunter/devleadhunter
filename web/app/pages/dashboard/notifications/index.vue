<template>
  <div class="max-w-3xl space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div class="min-w-0">
        <p class="app-label">Activité</p>
        <h1 class="app-page-title">Notifications</h1>
        <p class="text-muted mt-1 text-sm">
          Ouvertures d'email, clics, visites de démo, leads trouvés, ventes : tout ce qui s'est passé, du plus récent au
          plus ancien.
        </p>
      </div>
      <NuxtLink to="/dashboard/settings/notifications" class="app-btn-secondary h-9 shrink-0 px-4 text-xs">
        <UIcon name="i-lucide-settings-2" class="h-3.5 w-3.5" />
        Réglages
      </NuxtLink>
    </header>

    <UiNotificationList />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: ['auth'] })
</script>
