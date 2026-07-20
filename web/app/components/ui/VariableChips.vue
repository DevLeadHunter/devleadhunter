<template>
  <div class="flex flex-wrap gap-1.5">
    <div v-for="variable in variables" :key="variable.key" class="group relative">
      <button
        type="button"
        class="rounded-md border border-[var(--app-line)] bg-[var(--app-surface-2)] px-2 py-1 font-mono text-[11px] text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-accent)] hover:text-[var(--app-ink)]"
        @click="emit('insert', variable.token)"
      >
        {{ variable.token }}
      </button>

      <!-- Hover preview: what the variable contains + an example -->
      <div
        class="pointer-events-none absolute bottom-full left-0 z-10 mb-1.5 hidden w-max max-w-[260px] rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-2.5 text-left shadow-xl group-hover:block"
      >
        <p class="text-xs font-semibold text-[var(--app-ink)]">{{ variable.label }}</p>
        <p class="text-muted mt-0.5 text-[11px] leading-snug">{{ variable.description }}</p>
        <p class="mt-1.5 text-[11px] text-[var(--app-ink-soft)]">
          <span class="text-[var(--app-faint)]">Ex :</span> {{ variable.example }}
        </p>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { EmailVariable } from '~/utils/emailVariables'
import { EMAIL_VARIABLES } from '~/utils/emailVariables'

const emit = defineEmits<{
  /** A variable chip was clicked — insert its token at the caret. */
  insert: [token: string]
}>()

/** The available variables rendered as chips. */
const variables: EmailVariable[] = EMAIL_VARIABLES
</script>
