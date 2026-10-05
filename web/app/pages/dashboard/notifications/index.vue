<template>
  <div class="max-w-3xl space-y-6">
    <UiPageHeader
      eyebrow="Activité"
      title="Notifications"
      description="Ouvertures d'email, clics, visites de démo, leads trouvés, ventes : tout ce qui s'est passé, du plus récent au plus ancien."
    >
      <template #actions>
        <NuxtLink
          to="/dashboard/settings/notifications"
          class="app-btn-secondary h-11 px-4 text-sm whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50 @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
        >
          <UIcon name="i-lucide-settings-2" class="h-3.5 w-3.5" />
          Réglages
        </NuxtLink>
      </template>
    </UiPageHeader>

    <UiNotificationList />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: ['auth'] })
</script>
