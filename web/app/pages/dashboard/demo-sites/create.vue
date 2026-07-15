<template>
  <div class="py-16 text-center text-sm text-[var(--app-ink-soft)]">Redirection vers le tunnel…</div>
</template>

<script lang="ts" setup>
// « Créer un site » a été remplacé par le tunnel d'automatisation. On redirige
// (en conservant un éventuel ?prospect=… pour pré-sélectionner le prospect).
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const route = useRoute()
await navigateTo({ path: '/dashboard/automations/new', query: route.query })
</script>
