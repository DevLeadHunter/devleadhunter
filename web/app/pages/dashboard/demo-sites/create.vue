<template>
  <div class="py-16 text-center text-sm text-[var(--app-ink-soft)]">Redirection vers le tunnel…</div>
</template>

<script lang="ts" setup>
// Remplacée par le tunnel d'automatisation ; le ?prospect=… est conservé à la redirection.
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const route = useRoute()
await navigateTo({ path: '/dashboard/automations/new', query: route.query })
</script>
