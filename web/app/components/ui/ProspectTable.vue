<template>
  <div class="overflow-hidden">
    <BaseTable>
      <template #head>
        <BaseTableTh v-if="!hideSelection" class="w-12">
          <input
            type="checkbox"
            class="h-4 w-4 cursor-pointer accent-(--app-accent)"
            :checked="allSelected"
            :indeterminate.prop="someSelected && !allSelected"
            aria-label="Tout sélectionner sur cette page"
            @change="onToggleAll"
          />
        </BaseTableTh>
        <BaseTableTh>Nom</BaseTableTh>
        <BaseTableTh>Ville</BaseTableTh>
        <BaseTableTh>Téléphone</BaseTableTh>
        <BaseTableTh>Email</BaseTableTh>
        <BaseTableTh>Site web</BaseTableTh>
        <BaseTableTh>Contacté</BaseTableTh>
        <BaseTableTh align="center">Température</BaseTableTh>
        <BaseTableTh>Source</BaseTableTh>
        <BaseTableTh v-if="showAbVariant" align="center">Variante</BaseTableTh>
        <BaseTableTh align="center" sr-only>Actions</BaseTableTh>
      </template>

      <BaseTableTr
        v-for="prospect in prospects"
        :key="prospect.id"
        :class="[
          isSelected(prospect) ? 'bg-[var(--app-accent-soft)] hover:bg-[var(--app-accent-soft)]' : '',
          isLockedForMe(prospect)
            ? 'bg-[var(--app-surface-2)]/40 hover:bg-[var(--app-surface-2)]/40'
            : 'cursor-pointer',
        ]"
        @click="onRowClick(prospect, $event)"
      >
        <BaseTableTd v-if="!hideSelection">
          <input
            type="checkbox"
            class="h-4 w-4 accent-(--app-accent)"
            :class="isLockedForMe(prospect) ? 'cursor-not-allowed opacity-30' : 'cursor-pointer'"
            :checked="isSelected(prospect)"
            :disabled="isLockedForMe(prospect)"
            :aria-label="`Sélectionner ${prospect.name}`"
            @change="emit('toggleSelect', prospect)"
          />
        </BaseTableTd>

        <BaseTableTd>
          <div
            v-if="isLockedForMe(prospect)"
            class="flex items-center gap-2"
            :title="`Réservé par ${prospect.reserved_by_name || 'un membre de votre organisation'}`"
          >
            <UIcon name="i-lucide-lock" class="h-3.5 w-3.5 shrink-0 text-[var(--app-faint)]" />
            <span class="min-w-0">
              <span class="block truncate text-sm font-semibold text-[var(--app-ink-soft)]">
                {{ prospect.name }}
              </span>
              <span class="text-[11px] text-[var(--app-faint)]">
                Réservé par {{ prospect.reserved_by_name || 'un membre' }}
              </span>
            </span>
          </div>
          <button
            v-else
            type="button"
            class="cursor-pointer text-left text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors hover:decoration-[var(--app-accent)]"
            @click="emit('viewProspect', prospect)"
          >
            <span class="flex items-center gap-1.5">
              {{ prospect.name }}
              <UIcon
                v-if="prospect.has_pending_contact_proposal"
                name="i-lucide-user-round-search"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]"
                title="Décisionnaire à confirmer — ouvrez la fiche pour valider ou rejeter le nom proposé"
              />
              <UIcon
                v-if="isReservedByMe(prospect)"
                name="i-lucide-lock-keyhole"
                class="h-3 w-3 text-[var(--app-accent)]"
                title="Vous avez réservé ce prospect"
              />
              <UIcon
                v-if="prospect.sms_opted_out"
                name="i-lucide-message-square-off"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="A répondu STOP — ne plus envoyer de SMS"
              />
              <UIcon
                v-if="prospect.email_unsubscribed"
                name="i-lucide-mail-x"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="Désinscrit de la liste d'emails"
              />
              <UIcon
                v-if="prospect.do_not_contact"
                name="i-lucide-ban"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="Ne plus contacter — exclu des campagnes et des SMS"
              />
              <UIcon
                v-if="prospect.email_undeliverable"
                name="i-lucide-mail-x"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-red)]"
                title="Email injoignable (bounce) — récupérable en campagne SMS"
              />
            </span>
          </button>
        </BaseTableTd>

        <BaseTableTd label="Ville" class="text-sm text-[var(--app-ink-soft)]">{{ prospect.city || '—' }}</BaseTableTd>

        <BaseTableTd
          label="Téléphone"
          class="font-label text-xs whitespace-nowrap text-[var(--app-ink-soft)] tabular-nums"
          :class="isLockedForMe(prospect) && 'blur-[3px] select-none'"
        >
          {{ prospect.phone || '—' }}
        </BaseTableTd>

        <BaseTableTd label="Email" :class="isLockedForMe(prospect) && 'blur-[3px] select-none'">
          <span v-if="prospect.email" class="font-label text-xs text-[var(--app-ink)]">{{ prospect.email }}</span>
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd label="Site web">
          <span
            v-if="prospect.website_status === 'dead'"
            class="app-badge app-badge--danger"
            title="Le site trouvé ne répond plus — cible idéale"
          >
            <UIcon name="i-lucide-unplug" class="h-3 w-3" />
            Site mort
          </span>
          <span
            v-else-if="prospect.website_status === 'placeholder'"
            class="app-badge app-badge--info"
            title="Mini-site annuaire (business.site, Solocal…) — pas un vrai site"
          >
            <UIcon name="i-lucide-layout-template" class="h-3 w-3" />
            Site annuaire
          </span>
          <span v-else-if="prospect.website" class="app-badge">
            <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
            Oui
          </span>
          <span v-else class="app-badge app-badge--progress">
            <UIcon name="i-lucide-sparkle" class="h-3 w-3" />
            Non
          </span>
        </BaseTableTd>

        <BaseTableTd label="Contacté">
          <span
            v-if="prospect.email_undeliverable"
            class="app-badge app-badge--danger"
            title="Email injoignable (bounce) — récupérable en campagne SMS"
          >
            <UIcon name="i-lucide-mail-x" class="h-3 w-3" />
            Email KO
          </span>
          <span v-else-if="prospect.contacted" class="app-badge app-badge--success">
            <UIcon name="i-lucide-circle-check" class="h-3 w-3" />
            Oui
          </span>
          <span v-else class="app-badge">Non</span>
        </BaseTableTd>

        <BaseTableTd label="Température" align="center">
          <UiTemperatureBadge v-if="temperatureOf(prospect)" :temperature="temperatureOf(prospect)" />
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd label="Source">
          <UiProspectSourceBadge :source="prospect.source" />
        </BaseTableTd>

        <BaseTableTd v-if="showAbVariant" label="Variante" align="center">
          <span
            v-if="abVariants?.[prospect.id]"
            :class="[
              'rounded px-1.5 py-0.5 text-xs font-bold',
              abVariants[prospect.id] === 'A'
                ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                : 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
            ]"
          >
            {{ abVariants[prospect.id] }}
          </span>
          <span v-else class="text-sm text-[var(--app-faint)]">—</span>
        </BaseTableTd>

        <BaseTableTd align="center">
          <button
            v-if="rowAction === 'remove' && !isLockedForMe(prospect)"
            type="button"
            class="inline-flex cursor-pointer items-center gap-1 rounded-lg border border-[var(--app-red)]/30 px-2 py-1 text-xs text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/10"
            @click="emit('removeProspect', prospect)"
          >
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
            Retirer
          </button>
          <span v-else-if="rowAction === 'delete' && !isLockedForMe(prospect)" class="inline-flex items-center gap-1">
            <button
              type="button"
              class="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              :aria-label="`Modifier ${prospect.name}`"
              title="Modifier"
              @click="emit('editProspect', prospect)"
            >
              <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              class="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)]"
              :aria-label="`Supprimer ${prospect.name}`"
              title="Supprimer"
              @click="emit('deleteProspect', prospect)"
            >
              <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
            </button>
          </span>
        </BaseTableTd>
      </BaseTableTr>
    </BaseTable>

    <div v-if="prospects.length === 0" class="py-12 text-center">
      <LandingAsterisk class="mb-3 text-3xl text-[var(--app-accent)]" />
      <p class="text-sm text-[var(--app-ink-soft)]">Aucun prospect trouvé.</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import { computed } from 'vue'
import type { Prospect } from '~/types'
import type { UiProspectTableEmits, UiProspectTableProps } from '~/types/UiProspectTable'
import { useUserStore } from '~/stores/user'

/** Paginated prospect rows with per-row and select-all checkboxes. */
const props: UiProspectTableProps = defineProps({
  prospects: {
    type: Array as PropType<Prospect[]>,
    required: true,
  },
  selectedProspects: {
    type: Array as PropType<string[]>,
    default: () => [],
  },
  showAbVariant: {
    type: Boolean,
    default: false,
  },
  abVariants: {
    type: Object as PropType<Record<number, string | null | undefined>>,
    default: () => ({}),
  },
  temperatures: {
    type: Object as PropType<Record<number, string>>,
    default: () => ({}),
  },
  rowAction: {
    type: String as PropType<'delete' | 'remove'>,
    default: 'delete',
  },
  hideSelection: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProspectTableEmits> = defineEmits<UiProspectTableEmits>()

const userStore: ReturnType<typeof useUserStore> = useUserStore()

/** Current user id (0 while the store hydrates). */
const currentUserId: ComputedRef<number> = computed((): number => userStore.user?.id ?? 0)

/** Fast lookup set of the currently-selected prospect IDs. */
const selectedSet: ComputedRef<Set<string>> = computed((): Set<string> => new Set(props.selectedProspects ?? []))

/**
 * Whether the prospect is reserved by ANOTHER organization member → locked for me.
 * @param prospect - The prospect to test.
 * @returns True when someone else holds the reservation.
 */
function isLockedForMe(prospect: Prospect): boolean {
  return prospect.reserved_by_user_id != null && prospect.reserved_by_user_id !== currentUserId.value
}

/**
 * Whether the current user holds the reservation on this prospect.
 * @param prospect - The prospect to test.
 * @returns True when the reservation is mine.
 */
function isReservedByMe(prospect: Prospect): boolean {
  return prospect.reserved_by_user_id != null && prospect.reserved_by_user_id === currentUserId.value
}

/** Whether every visible prospect is selected. */
const allSelected: ComputedRef<boolean> = computed(
  (): boolean =>
    props.prospects.length > 0 && props.prospects.every((p: Prospect): boolean => selectedSet.value.has(String(p.id))),
)

/** Whether at least one visible prospect is selected. */
const someSelected: ComputedRef<boolean> = computed((): boolean =>
  props.prospects.some((p: Prospect): boolean => selectedSet.value.has(String(p.id))),
)

/**
 * Whether a given prospect is currently selected.
 * @param prospect - The prospect to test.
 * @returns True when the prospect's id is in the selection.
 */
function isSelected(prospect: Prospect): boolean {
  return selectedSet.value.has(String(prospect.id))
}

/**
 * Return the prospect's badge-worthy temperature, or '' when there is no activity.
 * @param prospect - The prospect to read the temperature for.
 * @returns 'hot' | 'warm' | 'cold', or '' to hide the badge.
 */
function temperatureOf(prospect: Prospect): string {
  const temperature: string | undefined = props.temperatures?.[prospect.id]
  return temperature === 'hot' || temperature === 'warm' || temperature === 'cold' ? temperature : ''
}

/**
 * Relay the header checkbox toggle to the parent.
 * @param event - The native change event.
 */
function onToggleAll(event: Event): void {
  emit('toggleSelectAll', (event.target as HTMLInputElement).checked)
}

/**
 * Open the prospect drawer when a bare part of the row is clicked, leaving controls to their handlers.
 * @param prospect - The prospect of the clicked row.
 * @param event - The native click event.
 */
function onRowClick(prospect: Prospect, event: MouseEvent): void {
  if (isLockedForMe(prospect)) return
  const target: HTMLElement | null = event.target instanceof HTMLElement ? event.target : null
  if (target?.closest('button, a, input, label, select, textarea')) return
  emit('viewProspect', prospect)
}
</script>
