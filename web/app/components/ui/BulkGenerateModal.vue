<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div class="border-muted w-full max-w-md rounded-xl border bg-[#1a1a1a] p-6">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 class="text-base font-semibold text-[#f9f9f9]">Générer les sites web</h2>
            <p class="text-muted mt-1 text-sm">
              {{ prospectIds.length }} prospect{{ prospectIds.length > 1 ? 's' : '' }} — même template
            </p>
          </div>
          <button
            type="button"
            class="text-muted cursor-pointer p-1 transition-colors hover:text-[#f9f9f9]"
            aria-label="Fermer"
            @click="emit('close')"
          >
            <i class="fa-solid fa-times"></i>
          </button>
        </div>

        <!-- Result summary -->
        <div v-if="result" class="space-y-4">
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="rounded-lg border border-[#2BAD5F]/30 bg-[#2BAD5F]/10 px-2 py-3">
              <div class="text-xl font-bold text-[#3fb950]">{{ result.created }}</div>
              <div class="text-[10px] tracking-wide text-[#8b949e] uppercase">Créés</div>
            </div>
            <div class="rounded-lg border border-[#30363d] bg-[#161b22] px-2 py-3">
              <div class="text-xl font-bold text-[#e3b341]">{{ result.skipped_no_email.length }}</div>
              <div class="text-[10px] tracking-wide text-[#8b949e] uppercase">Sans email</div>
            </div>
            <div class="rounded-lg border border-[#30363d] bg-[#161b22] px-2 py-3">
              <div class="text-xl font-bold text-[#DC4747]">{{ result.failed }}</div>
              <div class="text-[10px] tracking-wide text-[#8b949e] uppercase">Échecs</div>
            </div>
          </div>
          <p v-if="result.skipped_no_email.length" class="text-muted text-xs leading-relaxed">
            Ignorés (pas d'email) :
            {{ result.skipped_no_email.map((s) => s.name || `#${s.id}`).join(', ') }}
          </p>
          <button type="button" class="btn-primary w-full" @click="emit('close')">Fermer</button>
        </div>

        <!-- Form -->
        <div v-else>
          <label class="text-muted mb-1.5 block text-xs font-medium" for="bulk-template-select">Template</label>
          <div v-if="loading" class="text-muted py-3 text-sm">
            <i class="fa-solid fa-spinner fa-spin mr-2"></i>Chargement des templates…
          </div>
          <select v-else id="bulk-template-select" v-model="selectedTemplateId" class="input-field appearance-none">
            <option v-for="tpl in templates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
          </select>

          <label class="mt-4 flex cursor-pointer items-center gap-2.5 text-sm text-[#c9d1d9]">
            <input v-model="inviteCms" type="checkbox" class="h-4 w-4 cursor-pointer accent-[#2BAD5F]" />
            Inviter chaque client au CMS immédiatement
          </label>

          <p class="text-muted mt-3 text-xs leading-relaxed">
            Les prospects sans email sont ignorés (un site a besoin de l'email du client). L'enrichissement disponible
            est appliqué automatiquement.
          </p>

          <p v-if="error" class="mt-3 text-sm text-[#DC4747]">{{ error }}</p>

          <div class="mt-6 flex gap-3">
            <button type="button" class="btn-secondary flex-1" :disabled="submitting" @click="emit('close')">
              Annuler
            </button>
            <button
              type="button"
              class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="submitting || !selectedTemplateId"
              @click="submit"
            >
              <i v-if="submitting" class="fa-solid fa-spinner fa-spin mr-2"></i>
              {{ submitting ? 'Génération…' : 'Générer' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { PropType, Ref } from 'vue'
import { ref, watch } from 'vue'
import type { UiBulkGenerateModalProps } from '~/types/UiBulkGenerateModal'
import {
  createDemoSitesBulk,
  listDemoSiteTemplates,
  type BulkGenerateResult,
  type DemoSiteTemplate,
} from '~/services/demoSiteService'
import { useToast } from '~/composables/useToast'

/**
 * Defines the component props.
 */
const props: UiBulkGenerateModalProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospectIds: {
    type: Array as PropType<number[]>,
    required: true,
  },
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'generated', result: BulkGenerateResult): void
}>()

const toast = useToast()

/** Available demo-site templates. */
const templates: Ref<DemoSiteTemplate[]> = ref<DemoSiteTemplate[]>([])

/** Selected template id. */
const selectedTemplateId: Ref<string> = ref<string>('')

/** Whether to send a CMS invite to each client immediately. */
const inviteCms: Ref<boolean> = ref<boolean>(false)

/** Whether templates are loading. */
const loading: Ref<boolean> = ref<boolean>(false)

/** Whether a generation is in flight. */
const submitting: Ref<boolean> = ref<boolean>(false)

/** Inline error message. */
const error: Ref<string | null> = ref<string | null>(null)

/** Result of the last generation (null while the form is shown). */
const result: Ref<BulkGenerateResult | null> = ref<BulkGenerateResult | null>(null)

/**
 * Load the demo-site templates and pre-select the first one.
 */
async function loadTemplates(): Promise<void> {
  try {
    loading.value = true
    templates.value = await listDemoSiteTemplates()
    const first: DemoSiteTemplate | undefined = templates.value[0]
    if (first) selectedTemplateId.value = first.id
  } catch {
    templates.value = []
  } finally {
    loading.value = false
  }
}

/**
 * Generate demo sites for the selected prospects with the chosen template.
 */
async function submit(): Promise<void> {
  if (!selectedTemplateId.value || submitting.value) return
  error.value = null
  submitting.value = true
  try {
    const res = await createDemoSitesBulk({
      prospect_ids: props.prospectIds,
      template_id: selectedTemplateId.value,
      invite_client_to_cms: inviteCms.value,
    })
    result.value = res
    emit('generated', res)
    toast.success(`${res.created} site(s) généré(s)`)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erreur lors de la génération'
    toast.error(error.value)
  } finally {
    submitting.value = false
  }
}

watch(
  (): boolean => props.open,
  (isOpen: boolean): void => {
    if (isOpen) {
      error.value = null
      result.value = null
      inviteCms.value = false
      loadTemplates()
    }
  },
)
</script>
