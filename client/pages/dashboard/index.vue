<template>
  <div></div>
</template>

<script setup lang="ts">
/**
 * Dashboard home page - Redirects to search prospects
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

// Redirect to search prospects page
navigateTo('/dashboard/search-prospects', { replace: true });
</script>
