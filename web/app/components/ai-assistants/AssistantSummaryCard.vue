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
          <dd class="text-right text-[var(--app-ink)]">{{ assistantLanguagesLabel(props.assistant.languages) }}</dd>
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
        <div v-if="isSold" class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Sur son site</dt>
          <dd class="text-right break-all text-[var(--app-ink)]">{{ installedLabel }}</dd>
        </div>
        <div v-if="isSold" class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Fiche Google</dt>
          <dd class="text-right text-[var(--app-ink)]">{{ googleProfileLabel }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-[var(--app-ink-soft)]">Boîte mail</dt>
          <dd class="text-right break-all text-[var(--app-ink)]">{{ mailboxLabel }}</dd>
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
      <UiCopyLinkField :url="props.assistant.demo_url" link-label="Lien de la démo" is-link-label-hidden class="mt-2" />
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
import type { AiAssistantSummary } from '~/types/AiAssistant'
import type { AssistantSummaryCardProps } from '~/types/AssistantSummaryCard'
import type { UseToastReturn } from '~/types/Composables'
import { computed } from 'vue'
import { useToast } from '~/composables/useToast'
import { assistantLanguagesLabel, assistantLifetimeLabel, mailboxStatusLabel } from '~/utils/aiAssistantLabels'
import { ClipboardCopy } from '~/utils/clipboardCopy'
import { formatNumericDate } from '~/utils/date'

const props: AssistantSummaryCardProps = defineProps({
  assistant: {
    type: Object as PropType<AiAssistantSummary>,
    required: true,
  },
})

const toast: UseToastReturn = useToast()

const lifetimeLabel: ComputedRef<string> = computed((): string => assistantLifetimeLabel(props.assistant))

const mailboxLabel: ComputedRef<string> = computed((): string => mailboxStatusLabel(props.assistant))

/** Sold assistants show where they stand: the two « Pour démarrer » steps the client does alone. */
const isSold: ComputedRef<boolean> = computed((): boolean => props.assistant.status === 'delivered')

/** Where the widget's loader was last seen on the client's own site, as reported by the loader itself. */
const installedLabel: ComputedRef<string> = computed((): string => {
  const host: string | null = props.assistant.installed_host
  const seenAt: string | null = props.assistant.installed_at
  if (!host || !seenAt) return 'Pas encore vue'
  return `${host} · vue le ${formatNumericDate(seenAt)}`
})

/** Whether the client said the receptionist's address is on its Google profile. */
const googleProfileLabel: ComputedRef<string> = computed((): string => {
  const linkedAt: string | null = props.assistant.google_profile_linked_at
  return linkedAt ? `Adresse posée le ${formatNumericDate(linkedAt)}` : 'Adresse pas encore posée'
})

/**
 * Copy the embed snippet the client pastes on their site.
 * @returns A promise resolved once the copy was tried.
 */
async function copySnippet(): Promise<void> {
  if (await ClipboardCopy.copyText(props.assistant.embed_snippet)) {
    toast.success('Script copié : à coller avant </body> du site du client.')
  } else {
    toast.error('Copie refusée par le navigateur : sélectionnez le script pour le copier.')
  }
}
</script>
