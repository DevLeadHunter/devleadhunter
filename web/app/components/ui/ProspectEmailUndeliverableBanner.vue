<template>
  <div class="flex items-start gap-2 rounded-lg border border-[var(--app-red)]/40 bg-[var(--app-red-soft)] px-3 py-2.5">
    <UIcon name="i-lucide-mail-x" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-red)]" />
    <div class="min-w-0 text-xs">
      <p class="font-medium text-[var(--app-red)]">Email injoignable — le message a rebondi (bounce).</p>
      <p v-if="props.reason" class="mt-0.5 text-[var(--app-ink-soft)]">« {{ props.reason }} »</p>
      <p v-if="props.phone" class="mt-1 text-[var(--app-ink-soft)]">
        Récupérable en <strong class="font-medium text-[var(--app-ink)]">campagne SMS</strong> :
        {{ props.phone }}
      </p>
      <p v-else class="mt-1 text-[var(--app-ink-soft)]">Aucun numéro connu pour tenter un SMS.</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UiProspectEmailUndeliverableBannerProps } from '~/types/UiProspectEmailUndeliverableBanner'
import type { PropType } from 'vue'

/** Danger banner shown when a prospect's campaign email bounced with no other address to try. */
const props: UiProspectEmailUndeliverableBannerProps = defineProps({
  reason: {
    type: String as PropType<string | null>,
    default: null,
  },
  phone: {
    type: String as PropType<string | null>,
    default: null,
  },
})
</script>
