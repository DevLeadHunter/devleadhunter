<template>
  <div class="space-y-5">
    <div>
      <h2 class="text-sm font-semibold tracking-wide text-[var(--app-ink)] uppercase">Résumé</h2>
      <dl class="mt-4 space-y-3 text-xs">
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Statut</dt>
          <dd class="text-right text-[var(--app-ink)]">{{ lifetimeLabel }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Prénom</dt>
          <dd class="text-right text-[var(--app-ink)]">{{ props.assistant.assistant_name }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Langues</dt>
          <dd class="text-right text-[var(--app-ink)] uppercase">{{ props.assistant.languages.join(' · ') }}</dd>
        </div>
        <div v-if="props.assistant.tone" class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Ton</dt>
          <dd class="text-right text-[var(--app-ink)]">{{ props.assistant.tone }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Couleur</dt>
          <dd class="flex items-center justify-end gap-2 text-[var(--app-ink)]">
            <span
              class="inline-block h-3.5 w-3.5 rounded-full border border-[var(--app-line)]"
              :style="{ background: props.assistant.accent_color ?? 'transparent' }"
            />
            {{ props.assistant.accent_color ?? 'Neutre' }}
          </dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Email du commerçant</dt>
          <dd class="text-right break-all text-[var(--app-ink)]">{{ props.assistant.email ?? 'Aucun' }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Mobile d'alerte</dt>
          <dd class="text-right text-[var(--app-ink)]">{{ props.assistant.alerts.phone ?? 'Aucun' }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Modèle</dt>
          <dd class="text-right text-[var(--app-ink)]">
            {{ props.assistant.eu_only ? 'IA hébergée en Europe' : 'Mistral, secours Groq' }}
          </dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Créé le</dt>
          <dd class="text-right text-[var(--app-ink)]">{{ formatNumericDate(props.assistant.created_at) }}</dd>
        </div>
      </dl>
    </div>

    <div class="border-t border-[var(--app-line)] pt-4">
      <h3 class="text-sm font-semibold text-[var(--app-ink)]">Lien de la démo</h3>
      <div class="mt-2 flex items-center gap-2">
        <input :value="props.assistant.demo_url" readonly class="input-field h-9 flex-1 truncate text-xs" />
        <button
          type="button"
          class="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded border border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
          :title="copied ? 'Lien copié !' : 'Copier le lien'"
          @click="copy(props.assistant.demo_url)"
        >
          <UIcon :name="copied ? 'i-lucide-check' : 'i-lucide-copy'" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <div class="border-t border-[var(--app-line)] pt-4">
      <h3 class="text-sm font-semibold text-[var(--app-ink)]">Script pour le site du client</h3>
      <p class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        Une ligne à coller avant la balise de fin du site : la bulle apparaît en bas à droite.
      </p>
      <code
        class="mt-2 block rounded-md bg-[var(--app-surface-2)] px-2.5 py-2 text-[11px] leading-relaxed break-all text-[var(--app-ink-soft)]"
      >
        {{ props.assistant.embed_snippet }}
      </code>
      <button type="button" class="btn-secondary mt-2 w-full text-xs" @click="copySnippet">
        <UIcon name="i-lucide-code" class="mr-1.5 h-3.5 w-3.5" />
        Copier le script
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { AiAssistantSummary } from '~/types/AiAssistant'
import type { AssistantSummaryCardProps } from '~/types/AssistantSummaryCard'
import type { UseCopyToClipboardReturn, UseToastReturn } from '~/types/Composables'
import { useToast } from '~/composables/useToast'
import { assistantLifetimeLabel } from '~/utils/aiAssistantLabels'
import { formatNumericDate } from '~/utils/date'

const props: AssistantSummaryCardProps = defineProps({
  assistant: {
    type: Object as PropType<AiAssistantSummary>,
    required: true,
  },
})

const toast: UseToastReturn = useToast()
const { copy, copied }: UseCopyToClipboardReturn = useCopyToClipboard()

const lifetimeLabel: ComputedRef<string> = computed((): string => assistantLifetimeLabel(props.assistant))

/**
 * Copy the embed snippet the client pastes on their site.
 * @returns A promise resolved once copied.
 */
async function copySnippet(): Promise<void> {
  await copy(props.assistant.embed_snippet)
  toast.success('Script copié : à coller avant </body> du site du client.')
}
</script>
