<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'panne'">
      <path d="M13 2 5 13.5h5L9 22l8-11.5h-5L13 2Z" />
    </template>
    <template v-else-if="name === 'tableau'">
      <rect x="4" y="3" width="16" height="18" rx="1.5" />
      <path d="M4 9h16M4 15h16" />
      <path d="M8 6v0M8 12v0M8 18v0" stroke-width="2.4" />
      <path d="M12.5 6H17M12.5 12H17M12.5 18H17" />
    </template>
    <template v-else-if="name === 'renovation'">
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10v9.5h13V10" />
      <path d="M12.8 12.5 10.5 16h3l-2.3 3.5" />
    </template>
    <template v-else-if="name === 'domotique'">
      <rect x="7" y="2.5" width="10" height="19" rx="2" />
      <path d="M11 18.5h2" />
      <path d="M9.2 9.4a4.4 4.4 0 0 1 5.6 0" />
      <path d="M10.7 11.6a2.2 2.2 0 0 1 2.6 0" />
      <path d="M12 13.8v0" stroke-width="2.4" />
    </template>
    <template v-else-if="name === 'irve'">
      <rect x="4" y="4" width="11" height="17" rx="1.5" />
      <rect x="6.5" y="6.5" width="6" height="4" rx="0.8" />
      <path d="M10.2 12.5 8.5 15.5h2.5l-1.7 3" />
      <path d="M15 9h2.5a2 2 0 0 1 2 2v6.5a1.75 1.75 0 1 1-3.5 0V15" />
    </template>
    <template v-else-if="name === 'interphone'">
      <rect x="5" y="3" width="14" height="18" rx="1.5" />
      <circle cx="12" cy="9" r="2.6" />
      <path d="M8.5 16h7M8.5 18.5h4" />
    </template>
    <template v-else-if="name === 'phone'">
      <path d="M6.8 3.5c.6 0 1.2.4 1.4 1l.9 2.6c.2.6 0 1.3-.5 1.7l-1.2 1a12.4 12.4 0 0 0 6.8 6.8l1-1.2c.4-.5 1.1-.7 1.7-.5l2.6.9c.6.2 1 .8 1 1.4v2.3c0 .9-.7 1.6-1.6 1.5C10.5 20.4 3.6 13.5 3.1 5.1c-.1-.9.7-1.6 1.5-1.6h2.2Z" />
    </template>
    <template v-else-if="name === 'mail'">
      <rect x="3" y="5" width="18" height="14" rx="1.5" />
      <path d="m4 7 8 6.5L20 7" />
    </template>
    <template v-else-if="name === 'check'">
      <path d="m4.5 12.5 5 5L19.5 7" />
    </template>
    <template v-else>
      <path d="M13 2 5 13.5h5L9 22l8-11.5h-5L13 2Z" />
    </template>
  </svg>
</template>

<script lang="ts" setup>
/**
 * Set d'icônes filaires custom de la template 'electrician-lumen'.
 * Icônes dessinées à la main (stroke), pilotées par la prop `name` :
 * panne, tableau, renovation, domotique, irve, interphone, phone, mail, check.
 */
defineProps<{
  name: string
}>()
</script>
