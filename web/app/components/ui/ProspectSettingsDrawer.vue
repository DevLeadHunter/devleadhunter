<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && prospect"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au prospect"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[var(--app-ink)]"
          >
            <UIcon name="i-lucide-settings" class="h-4 w-4" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Réglages du prospect</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">{{ prospect.name }}</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            aria-label="Fermer"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <form
          id="prospect-settings-form"
          class="flex-1 space-y-4 overflow-y-auto px-5 py-4"
          @submit.prevent="handleSave"
        >
          <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
            Sources de données
          </p>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="prospect-settings-facebook">
              Page Facebook <span class="text-[var(--app-ink-soft)]">(facultatif)</span>
            </label>
            <input
              id="prospect-settings-facebook"
              v-model="form.facebook_url"
              type="url"
              class="input-field"
              placeholder="Ex : https://www.facebook.com/monentreprise"
            />
            <p class="text-muted mt-1.5 text-xs">Ajoutez-la à la main si vous l'avez trouvée vous-même.</p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="prospect-settings-maps">
              Fiche Google Maps <span class="text-[var(--app-ink-soft)]">(facultatif)</span>
            </label>
            <input
              id="prospect-settings-maps"
              v-model="form.google_maps_url"
              type="url"
              class="input-field"
              placeholder="Ex : https://www.google.com/maps/place/…"
            />
            <p class="text-muted mt-1.5 text-xs">Corrigez-la si elle a été mal détectée.</p>
          </div>

          <UiCallout variant="info">
            Ces deux liens guident l'<strong class="font-medium text-[var(--app-ink)]">enrichissement</strong> —
            réglez-les avant de le lancer.
          </UiCallout>

          <div class="border-t border-[var(--app-line)] pt-4">
            <p class="mb-3 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Contact</p>

            <UiProspectDoNotContactBanner
              v-if="prospect.do_not_contact"
              :reason="prospect.do_not_contact_reason ?? null"
              :is-toggling="isTogglingContact"
              @resume="handleResumeContact"
            />

            <div v-else-if="showStopForm" class="space-y-2 rounded-lg border border-[var(--app-line)] p-3">
              <label class="block text-xs font-medium text-[var(--app-ink-soft)]" for="prospect-settings-stop-reason">
                Raison (optionnel)
              </label>
              <textarea
                id="prospect-settings-stop-reason"
                v-model="stopReason"
                rows="2"
                class="input-field text-sm"
                placeholder="Ex. m'a dit au téléphone qu'il n'est pas intéressé"
              />
              <div class="flex gap-2">
                <button type="button" class="btn-secondary flex-1" :disabled="isTogglingContact" @click="closeStopForm">
                  Annuler
                </button>
                <button
                  type="button"
                  class="btn-danger flex-1"
                  :disabled="isTogglingContact"
                  @click="handleStopContact"
                >
                  <UIcon v-if="isTogglingContact" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
                  Ne plus contacter
                </button>
              </div>
            </div>

            <button v-else type="button" class="btn-danger w-full" @click="showStopForm = true">
              <UIcon name="i-lucide-ban" class="mr-1.5 h-4 w-4" />
              Ne plus contacter ce prospect
            </button>
          </div>
        </form>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="emit('back')">Annuler</button>
          <button
            type="submit"
            form="prospect-settings-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSaving"
          >
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isSaving ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type {
  ProspectSettingsForm,
  UiProspectSettingsDrawerEmits,
  UiProspectSettingsDrawerProps,
} from '~/types/UiProspectSettingsDrawer'
import type { EmitFn, PropType, Ref } from 'vue'
import type { Prospect } from '~/types'
import { ref, watch } from 'vue'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

/** Prospect settings sub-drawer: source URLs (Facebook / Google Maps) + « ne plus contacter ». */
const props: UiProspectSettingsDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospect: {
    type: Object as PropType<Prospect | null>,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProspectSettingsDrawerEmits> = defineEmits<UiProspectSettingsDrawerEmits>()

const toast: UseToastReturn = useToast()

const isSaving: Ref<boolean> = ref(false)
const isTogglingContact: Ref<boolean> = ref(false)
const showStopForm: Ref<boolean> = ref(false)
const stopReason: Ref<string> = ref('')

/** Editable source-URL form state. */
const form: Ref<ProspectSettingsForm> = ref({ facebook_url: '', google_maps_url: '' })

/**
 * Persist the edited source URLs, then hand back to the prospect drawer.
 * @returns A promise resolved once the prospect is saved.
 */
async function handleSave(): Promise<void> {
  if (!props.prospect) return
  isSaving.value = true
  try {
    const updated: Prospect = await ProspectsService.updateProspect(props.prospect.id, {
      facebook_url: form.value.facebook_url.trim() || null,
      google_maps_url: form.value.google_maps_url.trim() || null,
    })
    emit('updated', updated)
    toast.success('Réglages du prospect enregistrés')
    emit('back')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour du prospect')
  } finally {
    isSaving.value = false
  }
}

/**
 * Hide the « ne plus contacter » reason form and forget the typed reason.
 */
function closeStopForm(): void {
  showStopForm.value = false
  stopReason.value = ''
}

/**
 * Mark the prospect « ne plus contacter » — blocks all outreach and holds back its pending sends.
 * @returns A promise resolved once the flag is set.
 */
async function handleStopContact(): Promise<void> {
  if (!props.prospect || isTogglingContact.value) return
  isTogglingContact.value = true
  try {
    const updated: Prospect = await ProspectsService.setDoNotContact(
      props.prospect.id,
      true,
      stopReason.value.trim() || null,
    )
    emit('updated', updated)
    closeStopForm()
    toast.success('Prospect marqué « ne plus contacter » — exclu des campagnes et des SMS')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Action impossible')
  } finally {
    isTogglingContact.value = false
  }
}

/**
 * Lift the « ne plus contacter » flag so the prospect can be contacted again.
 * @returns A promise resolved once the flag is cleared.
 */
async function handleResumeContact(): Promise<void> {
  if (!props.prospect || isTogglingContact.value) return
  isTogglingContact.value = true
  try {
    const updated: Prospect = await ProspectsService.setDoNotContact(props.prospect.id, false, null)
    emit('updated', updated)
    toast.success('Contact ré-autorisé pour ce prospect')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Action impossible')
  } finally {
    isTogglingContact.value = false
  }
}

watch(
  () => [props.open, props.prospect?.id],
  ([open]: (boolean | number | undefined)[]): void => {
    if (!open) return
    form.value = {
      facebook_url: props.prospect?.facebook_url ?? '',
      google_maps_url: props.prospect?.google_maps_url ?? '',
    }
    closeStopForm()
  },
  { immediate: true },
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
