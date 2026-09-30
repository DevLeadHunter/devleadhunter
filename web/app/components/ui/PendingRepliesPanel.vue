<template>
  <div v-if="items.length > 0" class="space-y-2">
    <button
      :class="[
        'flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors',
        expanded
          ? 'border-[var(--app-green)] bg-[var(--app-green-soft)]'
          : 'border-[var(--app-green)]/30 bg-[var(--app-surface)] hover:bg-[var(--app-green-soft)]',
      ]"
      @click="expanded = !expanded"
    >
      <span
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--app-green-soft)] text-[var(--app-green)]"
      >
        <UIcon name="i-lucide-reply" class="h-4 w-4" />
      </span>
      <span class="flex-1 text-sm text-[var(--app-ink)]">
        <span class="font-semibold"> {{ items.length }} réponse{{ items.length > 1 ? 's' : '' }} à traiter </span>
        <span class="text-muted"> — un prospect attend votre réponse.</span>
      </span>
      <span class="text-muted shrink-0 text-xs font-medium">{{ expanded ? 'Masquer' : 'Voir' }}</span>
    </button>

    <ul v-if="expanded" class="card divide-y divide-[var(--app-line)] overflow-hidden">
      <li v-for="item in items" :key="`${item.source ?? 'email_reply'}-${item.id}`" class="flex gap-3 px-4 py-3">
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-[var(--app-ink)]">
            {{ item.prospect_name || item.from_email || 'Prospect' }}
            <span v-if="item.source === 'demo_lead'" class="text-muted ml-1 text-xs font-normal">(démo)</span>
          </p>
          <p v-if="item.subject" class="text-muted text-xs">{{ item.subject }}</p>
          <p class="text-muted mt-1 line-clamp-2 text-xs leading-relaxed">{{ item.preview }}</p>
        </div>
        <div class="flex shrink-0 flex-col gap-1.5">
          <button class="app-btn-primary h-8 px-3 text-xs" @click="emit('open', item)">Ouvrir</button>
          <button
            class="text-muted text-[11px] font-medium hover:text-[var(--app-ink)]"
            @click="emit('markHandled', item)"
          >
            Traité
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import type { EmitFn, Ref } from 'vue'
import type { PendingReply } from '~/types'

type PendingRepliesPanelEmits = {
  open: [item: PendingReply]
  markHandled: [item: PendingReply]
}

defineProps<{
  items: PendingReply[]
}>()

const emit: EmitFn<PendingRepliesPanelEmits> = defineEmits<PendingRepliesPanelEmits>()

const expanded: Ref<boolean> = ref(true)
</script>
