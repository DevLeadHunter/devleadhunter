<template>
  <Teleport to="body">
    <!-- Pas de backdrop : drawer non-modal (navigation possible pendant qu'il
         est ouvert), fermeture par X / Échap. -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-megaphone" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Nouvelle campagne</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              Séquence de cold email : envoi initial A/B puis relances
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <form
          id="create-campaign-form"
          class="flex-1 space-y-4 overflow-y-auto px-5 py-4"
          @submit.prevent="handleCreate"
        >
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="campaign-name">Nom de la campagne</label>
            <input
              id="campaign-name"
              v-model="form.name"
              type="text"
              required
              minlength="2"
              placeholder="Ex : Plombiers Lyon — juillet"
              class="input-field"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="campaign-description">
              Description (optionnel)
            </label>
            <textarea
              id="campaign-description"
              v-model="form.description"
              rows="3"
              placeholder="Objectif, cible, notes…"
              class="input-field h-auto min-h-20 py-2"
            ></textarea>
          </div>

          <p class="text-muted text-xs leading-relaxed">
            Vous choisirez ensuite les modèles d'email (variantes A/B), les relances et les prospects depuis la page de
            la campagne.
          </p>
        </form>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isCreating" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="create-campaign-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isCreating"
          >
            <UIcon v-if="isCreating" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isCreating ? 'Création…' : 'Créer la campagne' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import { useCampaignsStore } from '~/stores/campaigns'
import { useToast } from '~/composables/useToast'

/** Local shape of the campaign creation form. */
interface CreateCampaignForm {
  name: string
  description: string
}

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

const campaignsStore = useCampaignsStore()
const toast = useToast()

/** Whether the create request is in flight. */
const isCreating: Ref<boolean> = ref<boolean>(false)

/** Campaign creation form state. */
const form: Ref<CreateCampaignForm> = ref<CreateCampaignForm>({ name: '', description: '' })

/**
 * Create the campaign then close the drawer (the store prepends it to the list).
 * @returns A promise resolved once the campaign is created.
 */
async function handleCreate(): Promise<void> {
  isCreating.value = true
  try {
    await campaignsStore.createCampaign({
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      prospect_ids: [],
    })
    toast.success('Campagne créée avec succès')
    emit('close')
  } catch {
    toast.error('Erreur lors de la création de la campagne')
  } finally {
    isCreating.value = false
  }
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) {
      form.value = { name: '', description: '' }
    }
  },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
