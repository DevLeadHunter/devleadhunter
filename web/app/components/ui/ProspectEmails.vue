<template>
  <div class="space-y-2">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <p class="text-[10px] text-[var(--app-ink-soft)]">
          {{ emails.length > 1 ? 'Emails' : 'Email' }}
        </p>
        <span
          v-if="emails.length > 1"
          class="inline-flex items-center rounded border border-[var(--app-line)] bg-[var(--app-surface-2)] px-1.5 text-[9px] font-medium text-[var(--app-ink-soft)] tabular-nums"
        >
          {{ emails.length }}
        </span>
      </div>
      <button
        v-if="editable && !isEditing && emails.length > 0"
        type="button"
        class="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
        title="Gérer les emails de ce prospect"
        @click="startEditing"
      >
        <UIcon name="i-lucide-pencil" class="h-3 w-3" />
        Gérer
      </button>
    </div>

    <!-- Read mode -->
    <template v-if="!isEditing">
      <p v-if="emails.length === 0" class="text-sm text-[var(--app-faint)]">—</p>
      <ul v-else class="space-y-1.5">
        <li v-for="(address, index) in emails" :key="address" class="flex items-center gap-2">
          <span class="truncate text-sm font-medium text-[var(--app-ink)]" :title="address">
            {{ address }}
          </span>
          <span
            v-if="index === 0"
            class="inline-flex shrink-0 items-center gap-1 rounded bg-[var(--app-accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--app-accent-ink)]"
            title="Adresse principale — celle affichée dans la table et utilisée pour l'envoi"
          >
            <UIcon name="i-lucide-star" class="h-2.5 w-2.5" />
            Principal
          </span>
          <a
            :href="`mailto:${address}`"
            class="ml-auto flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-accent-ink)]"
            title="Composer un email"
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
          v-for="(address, index) in draft"
          :key="address"
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
          <span class="min-w-0 flex-1 truncate text-sm text-[var(--app-ink)]" :title="address">{{ address }}</span>
          <span
            v-if="index === 0"
            class="shrink-0 rounded bg-[var(--app-accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--app-accent-ink)]"
          >
            Principal
          </span>
          <button
            type="button"
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)] disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-[var(--app-ink-soft)] pointer-coarse:size-11"
            :disabled="draft.length <= 1"
            :title="draft.length <= 1 ? 'Au moins un email est requis' : 'Retirer cet email'"
            @click="remove(index)"
          >
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          </button>
        </li>
      </ul>

      <form class="flex gap-1.5" @submit.prevent="add">
        <input
          v-model="newEmail"
          type="email"
          class="input-field h-8 flex-1 text-sm"
          placeholder="contact@exemple.fr"
        />
        <button
          type="submit"
          class="btn-secondary h-8 shrink-0 px-2.5 text-xs"
          :disabled="!canAdd"
          title="Ajouter cet email à la liste"
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
import type { UiProspectEmailsEmits, UiProspectEmailsProps } from '~/types/UiProspectEmails'
import type { UseToastReturn } from '~/types/Composables'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

const props: UiProspectEmailsProps = defineProps({
  prospect: {
    type: Object as PropType<Prospect>,
    required: true,
  },
  editable: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<UiProspectEmailsEmits> = defineEmits<UiProspectEmailsEmits>()

const toast: UseToastReturn = useToast()

const _EMAIL_RE: RegExp = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const isEditing: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const draft: Ref<string[]> = ref([])
const newEmail: Ref<string> = ref('')

/** The prospect's stored emails, falling back to the single `email` field for legacy rows. */
const emails: ComputedRef<string[]> = computed((): string[] => {
  const list: string[] = props.prospect.emails ?? []
  if (list.length > 0) return list
  return props.prospect.email ? [props.prospect.email] : []
})

/** Whether the typed email is a new, valid, not-yet-present address. */
const canAdd: ComputedRef<boolean> = computed((): boolean => {
  const candidate: string = newEmail.value.trim().toLowerCase()
  return _EMAIL_RE.test(candidate) && !draft.value.some((email: string): boolean => email.toLowerCase() === candidate)
})

/** Whether the draft differs from the stored list (order or membership). */
const isDirty: ComputedRef<boolean> = computed((): boolean => {
  return (
    draft.value.length !== emails.value.length ||
    draft.value.some((e: string, i: number): boolean => e !== emails.value[i])
  )
})

/** Enter edit mode with a working copy of the current list. */
function startEditing(): void {
  draft.value = [...emails.value]
  newEmail.value = ''
  isEditing.value = true
}

/** Leave edit mode, discarding unsaved changes. */
function cancel(): void {
  isEditing.value = false
  newEmail.value = ''
}

/**
 * Move an email up or down the fallback order (index 0 is the primary).
 * @param index - Current position of the email.
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
 * Remove an email from the draft list; the last remaining one is kept so a prospect never loses its contact.
 * @param index - Position of the email to drop.
 */
function remove(index: number): void {
  if (draft.value.length <= 1) return
  draft.value = draft.value.filter((_: string, i: number): boolean => i !== index)
}

/** Append the typed email to the draft (validated + deduped) and clear the input. */
function add(): void {
  if (!canAdd.value) return
  draft.value = [...draft.value, newEmail.value.trim()]
  newEmail.value = ''
}

/**
 * Persist the reordered/edited list; the first entry becomes the primary.
 * @returns A promise resolved once saved.
 */
async function save(): Promise<void> {
  isSaving.value = true
  try {
    const updated: Prospect = await ProspectsService.updateProspectEmails(props.prospect.id, draft.value)
    emit('updated', updated)
    isEditing.value = false
    toast.success('Emails mis à jour')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Mise à jour des emails impossible')
  } finally {
    isSaving.value = false
  }
}

/** Reset the editing state whenever the drawer switches to another prospect. */
watch(
  (): number => props.prospect.id,
  (): void => {
    isEditing.value = false
    newEmail.value = ''
  },
)
</script>
