<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <p class="text-[10px] text-[var(--app-ink-soft)]">
          {{ phones.length > 1 ? 'Téléphones' : 'Téléphone' }}
        </p>
        <span
          v-if="phones.length > 1"
          class="inline-flex items-center rounded border border-[var(--app-line)] bg-[var(--app-surface-2)] px-1.5 text-[9px] font-medium text-[var(--app-ink-soft)] tabular-nums"
        >
          {{ phones.length }}
        </span>
      </div>
      <button
        v-if="editable && !isEditing && phones.length > 0"
        type="button"
        class="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
        title="Gérer les numéros de ce prospect"
        @click="startEditing"
      >
        <UIcon name="i-lucide-pencil" class="h-3 w-3" />
        Gérer
      </button>
    </div>

    <!-- Read mode -->
    <template v-if="!isEditing">
      <p v-if="phones.length === 0" class="text-sm text-[var(--app-faint)]">—</p>
      <ul v-else class="space-y-1.5">
        <li v-for="(number, index) in phones" :key="number" class="flex items-center gap-2">
          <span class="truncate text-sm font-medium text-[var(--app-ink)] tabular-nums" :title="number">
            {{ number }}
          </span>
          <span
            v-if="index === 0"
            class="inline-flex shrink-0 items-center gap-1 rounded bg-[var(--app-accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--app-accent-ink)]"
            title="Numéro principal — celui affiché dans la table et utilisé pour les SMS"
          >
            <UIcon name="i-lucide-star" class="h-2.5 w-2.5" />
            Principal
          </span>
          <a
            :href="`tel:${number}`"
            class="ml-auto flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-accent-ink)]"
            title="Appeler"
          >
            <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
          </a>
        </li>
      </ul>
    </template>

    <!-- Edit mode -->
    <template v-else>
      <ul class="space-y-1.5">
        <li
          v-for="(number, index) in draft"
          :key="number"
          class="flex items-center gap-1 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-2 py-1.5"
        >
          <div class="flex shrink-0 flex-col">
            <button
              type="button"
              class="flex h-3.5 w-5 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-30"
              :disabled="index === 0"
              title="Monter (rapprocher du principal)"
              @click="move(index, -1)"
            >
              <UIcon name="i-lucide-chevron-up" class="h-3 w-3" />
            </button>
            <button
              type="button"
              class="flex h-3.5 w-5 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-30"
              :disabled="index === draft.length - 1"
              title="Descendre"
              @click="move(index, 1)"
            >
              <UIcon name="i-lucide-chevron-down" class="h-3 w-3" />
            </button>
          </div>
          <span class="min-w-0 flex-1 truncate text-sm text-[var(--app-ink)] tabular-nums" :title="number">{{
            number
          }}</span>
          <span
            v-if="index === 0"
            class="shrink-0 rounded bg-[var(--app-accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--app-accent-ink)]"
          >
            Principal
          </span>
          <button
            type="button"
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)] disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-[var(--app-ink-soft)]"
            :disabled="draft.length <= 1"
            :title="draft.length <= 1 ? 'Au moins un numéro est requis' : 'Retirer ce numéro'"
            @click="remove(index)"
          >
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          </button>
        </li>
      </ul>

      <form class="flex gap-1.5" @submit.prevent="add">
        <input v-model="newPhone" type="tel" class="input-field h-8 flex-1 text-sm" placeholder="06 12 34 56 78" />
        <button
          type="submit"
          class="btn-secondary h-8 shrink-0 px-2.5 text-xs"
          :disabled="!canAdd"
          title="Ajouter ce numéro à la liste"
        >
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
        </button>
      </form>

      <div class="flex gap-2 pt-0.5">
        <button type="button" class="btn-secondary h-8 flex-1 text-xs" :disabled="isSaving" @click="cancel">
          Annuler
        </button>
        <button type="button" class="btn-primary h-8 flex-1 text-xs" :disabled="isSaving || !isDirty" @click="save">
          <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1 h-3.5 w-3.5 animate-spin" />
          Enregistrer
        </button>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from 'vue'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { Prospect } from '~/types'
import type { UiProspectPhonesEmits, UiProspectPhonesProps } from '~/types/UiProspectPhones'
import type { UseToastReturn } from '~/types/Composables'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

const props: UiProspectPhonesProps = defineProps({
  prospect: {
    type: Object as PropType<Prospect>,
    required: true,
  },
  editable: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<UiProspectPhonesEmits> = defineEmits<UiProspectPhonesEmits>()

const toast: UseToastReturn = useToast()

/** Loose French-format check — the API normalises to E.164 and dedupes for real. */
const _PHONE_RE: RegExp = /^\+?[0-9][0-9 .\-()]{7,18}$/

const isEditing: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const draft: Ref<string[]> = ref([])
const newPhone: Ref<string> = ref('')

/** The prospect's stored numbers, falling back to the single `phone` field for legacy rows. */
const phones: ComputedRef<string[]> = computed((): string[] => {
  const list: string[] = props.prospect.phones ?? []
  if (list.length > 0) return list
  return props.prospect.phone ? [props.prospect.phone] : []
})

/**
 * Identity key of a number, digits only, so « 06 42 19 38 12 » and « +33642193812 » match.
 * @param phone - The number as typed.
 * @returns The digits-only key.
 */
function phoneKey(phone: string): string {
  const digits: string = phone.replace(/[^0-9]/g, '')
  return digits.startsWith('33') ? `0${digits.slice(2)}` : digits
}

/** Whether the typed number is a new, plausible, not-yet-present one. */
const canAdd: ComputedRef<boolean> = computed((): boolean => {
  const candidate: string = newPhone.value.trim()
  return (
    _PHONE_RE.test(candidate) && !draft.value.some((phone: string): boolean => phoneKey(phone) === phoneKey(candidate))
  )
})

/** Whether the draft differs from the stored list (order or membership). */
const isDirty: ComputedRef<boolean> = computed((): boolean => {
  return (
    draft.value.length !== phones.value.length ||
    draft.value.some((p: string, i: number): boolean => p !== phones.value[i])
  )
})

/** Enter edit mode with a working copy of the current list. */
function startEditing(): void {
  draft.value = [...phones.value]
  newPhone.value = ''
  isEditing.value = true
}

/** Leave edit mode, discarding unsaved changes. */
function cancel(): void {
  isEditing.value = false
  newPhone.value = ''
}

/**
 * Move a number up or down the order (index 0 is the primary).
 * @param index - Current position of the number.
 * @param delta - -1 to move up, +1 to move down.
 */
function move(index: number, delta: number): void {
  const target: number = index + delta
  if (target < 0 || target >= draft.value.length) return
  const next: string[] = [...draft.value]
  const [moved]: string[] = next.splice(index, 1)
  if (moved === undefined) return
  next.splice(target, 0, moved)
  draft.value = next
}

/**
 * Remove a number from the draft list; the last remaining one is kept so a prospect never loses its contact.
 * @param index - Position of the number to drop.
 */
function remove(index: number): void {
  if (draft.value.length <= 1) return
  draft.value = draft.value.filter((_: string, i: number): boolean => i !== index)
}

/** Append the typed number to the draft (validated + deduped) and clear the input. */
function add(): void {
  if (!canAdd.value) return
  draft.value = [...draft.value, newPhone.value.trim()]
  newPhone.value = ''
}

/**
 * Persist the reordered/edited list; the first entry becomes the primary.
 * @returns A promise resolved once saved.
 */
async function save(): Promise<void> {
  isSaving.value = true
  try {
    const updated: Prospect = await ProspectsService.updateProspectPhones(props.prospect.id, draft.value)
    emit('updated', updated)
    isEditing.value = false
    toast.success('Numéros mis à jour')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Mise à jour des numéros impossible')
  } finally {
    isSaving.value = false
  }
}

/** Reset the editing state whenever the drawer switches to another prospect. */
watch(
  (): number => props.prospect.id,
  (): void => {
    isEditing.value = false
    newPhone.value = ''
  },
)
</script>
