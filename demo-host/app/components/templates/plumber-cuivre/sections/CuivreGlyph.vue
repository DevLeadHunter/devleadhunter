<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'phone'">
      <path d="M6.8 3.5c.6 0 1.2.4 1.4 1l.9 2.6c.2.6 0 1.3-.5 1.7l-1.2 1a12.4 12.4 0 0 0 6.8 6.8l1-1.2c.4-.5 1.1-.7 1.7-.5l2.6.9c.6.2 1 .8 1 1.4v2.3c0 .9-.7 1.6-1.6 1.5C10.5 20.4 3.6 13.5 3.1 5.1c-.1-.9.7-1.6 1.5-1.6h2.2Z" />
    </template>
    <template v-else-if="name === 'mail'">
      <rect x="3" y="5" width="18" height="14" rx="1" />
      <path d="m4 7 8 6.5L20 7" />
    </template>
    <template v-else-if="name === 'check'">
      <path d="m4.5 12.5 5 5L19.5 7" />
    </template>
    <template v-else-if="name === 'star'">
      <path d="M12 3.2l2.7 5.6 6.1.8-4.5 4.2 1.2 6-5.5-3-5.5 3 1.2-6L3.2 9.6l6.1-.8L12 3.2z" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'drop'">
      <path d="M12 3.5c3.2 4.2 5.5 7.3 5.5 10.2a5.5 5.5 0 1 1-11 0c0-2.9 2.3-6 5.5-10.2Z" />
      <path d="M9.6 13.8a2.6 2.6 0 0 0 1.8 2.4" />
    </template>
    <template v-else>
      <path d="M12 3.5c3.2 4.2 5.5 7.3 5.5 10.2a5.5 5.5 0 1 1-11 0c0-2.9 2.3-6 5.5-10.2Z" />
    </template>
  </svg>
</template>

<script lang="ts" setup>
/**
 * Petits glyphes filaires de la template 'plumber-cuivre', dessinés à la main.
 * Pilotés par la prop `name` : phone, mail, check, star, drop.
 */
defineProps<{
  name: string
}>()
</script>
