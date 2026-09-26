<template>
  <div class="space-y-2 border-t border-[var(--app-line)] pt-4">
    <h3 class="text-sm font-semibold text-[var(--app-ink)]">Actions</h3>
    <button
      type="button"
      class="btn-secondary inline-flex w-full items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="props.isRegenerating"
      @click="emit('regenerate')"
    >
      <UIcon
        :name="props.isRegenerating ? 'i-lucide-loader-circle' : 'i-lucide-refresh-cw'"
        class="h-3.5 w-3.5"
        :class="{ 'animate-spin': props.isRegenerating }"
      />
      {{ props.isRegenerating ? 'Régénération…' : 'Régénérer depuis le prospect' }}
    </button>
    <button
      v-if="props.status === 'delivered'"
      type="button"
      class="btn-secondary inline-flex w-full items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="props.isSendingClientLink"
      @click="emit('send-client-space')"
    >
      <UIcon
        :name="props.isSendingClientLink ? 'i-lucide-loader-circle' : 'i-lucide-user-round-key'"
        class="h-3.5 w-3.5"
        :class="{ 'animate-spin': props.isSendingClientLink }"
      />
      Envoyer l'espace client
    </button>
    <button
      v-if="props.status === 'active' || props.status === 'expired'"
      type="button"
      class="btn-secondary inline-flex w-full items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="props.isMarkingSold"
      @click="emit('mark-sold')"
    >
      <UIcon
        :name="props.isMarkingSold ? 'i-lucide-loader-circle' : 'i-lucide-badge-check'"
        class="h-3.5 w-3.5"
        :class="{ 'animate-spin': props.isMarkingSold }"
      />
      {{ props.isMarkingSold ? 'Passage en vendu…' : 'Marquer comme vendu (hors Stripe)' }}
    </button>
    <button
      type="button"
      class="btn-secondary w-full text-xs text-[var(--app-red)] disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="props.isDeleting"
      @click="emit('remove')"
    >
      {{ props.isDeleting ? 'Suppression…' : "Supprimer l'assistant" }}
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn } from 'vue'
import type { AssistantActionsCardEmits, AssistantActionsCardProps } from '~/types/AssistantActionsCard'

const props: AssistantActionsCardProps = defineProps({
  status: {
    type: String,
    required: true,
  },
  isRegenerating: {
    type: Boolean,
    default: false,
  },
  isSendingClientLink: {
    type: Boolean,
    default: false,
  },
  isMarkingSold: {
    type: Boolean,
    default: false,
  },
  isDeleting: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<AssistantActionsCardEmits> = defineEmits<AssistantActionsCardEmits>()
</script>
