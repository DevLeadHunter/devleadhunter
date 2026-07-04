<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <Transition name="drawer-backdrop">
      <div v-if="open" class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
    </Transition>

    <!-- Slide-over panel -->
    <Transition name="drawer-panel">
      <div
        v-if="open && prospect"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[#30363d] bg-[#0d0d0d] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[#30363d] px-5 py-4">
          <!-- Business icon -->
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#30363d] bg-[#1a1a1a]"
          >
            <UIcon name="i-lucide-store" class="h-4 w-4 text-[#8b949e]" />
          </div>

          <div class="min-w-0 flex-1">
            <!-- Badges -->
            <div class="mb-1 flex flex-wrap items-center gap-1.5">
              <span
                class="inline-flex items-center rounded border border-[#30363d] bg-[#1a1a1a] px-2 py-0.5 text-[10px] font-medium text-[#8b949e]"
              >
                {{ prospect.category }}
              </span>
              <UiProspectSourceBadge :source="prospect.source" />
            </div>

            <!-- Name -->
            <h2 class="truncate text-base leading-tight font-semibold text-[#f9f9f9]">
              {{ prospect.name }}
            </h2>

            <!-- Confidence dots -->
            <div class="mt-1.5 flex items-center gap-1">
              <span
                v-for="i in 4"
                :key="i"
                :class="['h-1.5 w-1.5 rounded-full', i <= prospect.confidence ? confidenceColor : 'bg-[#30363d]']"
              />
              <span class="ml-1 text-[10px] text-[#8b949e]">Confiance {{ prospect.confidence }}/4</span>
            </div>
          </div>

          <!-- Close button -->
          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[#8b949e] transition-colors hover:bg-[#1a1a1a] hover:text-[#f9f9f9]"
            @click="$emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <div class="flex-1 overflow-y-auto">
          <!-- VIEW MODE -->
          <template v-if="!editMode">
            <!-- Contact -->
            <div class="space-y-3 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Contact</p>

              <!-- Phone -->
              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1a1a1a]">
                  <UIcon name="i-lucide-phone" class="h-4 w-4 text-[#8b949e]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[#8b949e]">Téléphone</p>
                  <p v-if="prospect.phone" class="text-sm font-medium text-[#f9f9f9]">
                    {{ prospect.phone }}
                  </p>
                  <p v-else class="text-sm text-[#30363d]">—</p>
                </div>
                <a
                  v-if="prospect.phone"
                  :href="`tel:${prospect.phone}`"
                  class="flex h-7 w-7 items-center justify-center rounded text-[#8b949e] transition-colors hover:bg-[#1a1a1a] hover:text-[#58a6ff]"
                  title="Appeler"
                >
                  <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                </a>
              </div>

              <!-- Email -->
              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1a1a1a]">
                  <UIcon name="i-lucide-mail" class="h-4 w-4 text-[#8b949e]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[#8b949e]">Email</p>
                  <p v-if="prospect.email" class="truncate text-sm font-medium text-[#f9f9f9]">
                    {{ prospect.email }}
                  </p>
                  <p v-else class="text-sm text-[#30363d]">—</p>
                </div>
                <a
                  v-if="prospect.email"
                  :href="`mailto:${prospect.email}`"
                  class="flex h-7 w-7 items-center justify-center rounded text-[#8b949e] transition-colors hover:bg-[#1a1a1a] hover:text-[#58a6ff]"
                  title="Composer un email"
                >
                  <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                </a>
              </div>

              <!-- Website -->
              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1a1a1a]">
                  <UIcon name="i-lucide-globe" class="h-4 w-4 text-[#8b949e]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[#8b949e]">Site web</p>
                  <p v-if="prospect.website" class="truncate text-sm text-[#58a6ff]">
                    {{ prospect.website }}
                  </p>
                  <p v-else class="text-sm text-[#30363d]">—</p>
                </div>
                <a
                  v-if="prospect.website"
                  :href="prospect.website"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex h-7 w-7 items-center justify-center rounded text-[#8b949e] transition-colors hover:bg-[#1a1a1a] hover:text-[#58a6ff]"
                  title="Ouvrir le site"
                >
                  <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                </a>
              </div>
            </div>

            <!-- Divider -->
            <div class="border-t border-[#1f1f1f]"></div>

            <!-- Location -->
            <div class="space-y-3 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Localisation</p>
              <div class="flex items-start gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1a1a1a]">
                  <UIcon name="i-lucide-map-pin" class="h-4 w-4 text-[#8b949e]" />
                </div>
                <div>
                  <p class="text-[10px] text-[#8b949e]">Adresse</p>
                  <div v-if="prospect.address || prospect.city" class="mt-0.5">
                    <p v-if="prospect.address" class="text-sm text-[#f9f9f9]">{{ prospect.address }}</p>
                    <p v-if="prospect.city" class="text-sm text-[#8b949e]">{{ prospect.city }}</p>
                  </div>
                  <p v-else class="text-sm text-[#30363d]">—</p>
                </div>
              </div>
            </div>

            <!-- Divider -->
            <div class="border-t border-[#1f1f1f]"></div>

            <!-- Meta -->
            <div class="px-5 py-4">
              <p class="mb-3 text-[10px] font-semibold tracking-wider text-[#8b949e] uppercase">Informations</p>
              <div class="grid grid-cols-2 gap-x-4 gap-y-3">
                <div>
                  <p class="text-[10px] text-[#8b949e]">Catégorie</p>
                  <p class="mt-0.5 text-sm text-[#f9f9f9]">{{ prospect.category }}</p>
                </div>
                <div>
                  <p class="mb-1 text-[10px] text-[#8b949e]">Source</p>
                  <UiProspectSourceBadge :source="prospect.source" />
                </div>
                <div v-if="prospect.created_at">
                  <p class="text-[10px] text-[#8b949e]">Ajouté le</p>
                  <p class="mt-0.5 text-sm text-[#f9f9f9]">{{ formatDate(prospect.created_at) }}</p>
                </div>
                <div>
                  <p class="text-[10px] text-[#8b949e]">ID</p>
                  <p class="mt-0.5 font-mono text-sm text-[#8b949e]">#{{ prospect.id }}</p>
                </div>
              </div>
            </div>

            <!-- Divider -->
            <div class="border-t border-[#1f1f1f]"></div>

            <!-- Enrichment -->
            <UiProspectEnrichment :prospect-id="prospect.id" :open="open" />

            <!-- Divider -->
            <div class="border-t border-[#1f1f1f]"></div>

            <!-- Behaviour (demo tracking → scoring / timeline / AI) -->
            <UiProspectBehavior
              :prospect-id="prospect.id"
              :prospect-email="prospect.email ?? null"
              :prospect-name="prospect.name"
              :open="open"
            />
          </template>

          <!-- EDIT MODE -->
          <form v-else id="prospect-edit-form" class="space-y-4 p-5" @submit.prevent="handleSave">
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase"> Nom * </label>
              <input v-model="editForm.name" type="text" required class="input-field" placeholder="Nom du prospect" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase">
                  Téléphone
                </label>
                <input v-model="editForm.phone" type="tel" class="input-field" placeholder="06 12 34 56 78" />
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase">
                  Email
                </label>
                <input v-model="editForm.email" type="email" class="input-field" placeholder="contact@..." />
              </div>
            </div>

            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase">
                Site web
              </label>
              <input v-model="editForm.website" type="url" class="input-field" placeholder="https://..." />
            </div>

            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase">
                Adresse
              </label>
              <input v-model="editForm.address" type="text" class="input-field" placeholder="12 Rue de la Paix" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase">
                  Ville
                </label>
                <input v-model="editForm.city" type="text" class="input-field" placeholder="Paris" />
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[#8b949e] uppercase">
                  Catégorie
                </label>
                <input v-model="editForm.category" type="text" class="input-field" placeholder="plombier" />
              </div>
            </div>
          </form>
        </div>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="border-t border-[#30363d] px-5 py-4">
          <!-- Delete confirmation inline -->
          <div v-if="showDeleteConfirm" class="rounded-lg border border-[#da3633]/40 bg-[#da3633]/10 p-4">
            <p class="mb-0.5 text-sm font-medium text-[#f9f9f9]">Supprimer ce prospect ?</p>
            <p class="mb-3 text-xs text-[#8b949e]">Cette action est irréversible.</p>
            <div class="flex gap-2">
              <button class="btn-secondary flex-1 text-xs" :disabled="isDeleting" @click="showDeleteConfirm = false">
                Annuler
              </button>
              <button class="btn-danger flex-1 text-xs" :disabled="isDeleting" @click="handleDelete">
                <UIcon v-if="isDeleting" name="i-lucide-loader-circle" class="mr-1 h-4 w-4 animate-spin" />
                Confirmer
              </button>
            </div>
          </div>

          <!-- View mode actions -->
          <div v-else-if="!editMode" class="space-y-2">
            <button
              class="btn-secondary w-full"
              :class="prospect.contacted ? 'text-[#3fb950]' : ''"
              :title="prospect.contacted ? 'Marquer comme pas contacté' : 'Marquer comme contacté'"
              @click="$emit('toggleContacted', prospect)"
            >
              <UIcon
                :name="prospect.contacted ? 'i-lucide-circle-check-big' : 'i-lucide-circle'"
                class="mr-1.5 h-4 w-4"
              />
              {{ prospect.contacted ? 'Contacté' : 'Marquer comme contacté' }}
            </button>
            <div class="flex gap-2">
              <button class="btn-secondary flex-1" @click="$emit('addToCampaign', prospect)">
                <UIcon name="i-lucide-plus" class="mr-1.5 h-4 w-4" />Campagne
              </button>
              <button
                class="btn-secondary flex-1"
                :class="{ 'cursor-not-allowed opacity-40': !prospect.email }"
                :disabled="!prospect.email"
                @click="prospect.email && $emit('sendEmail', prospect)"
              >
                <UIcon name="i-lucide-mail" class="mr-1.5 h-4 w-4" />Email
              </button>
            </div>
            <div class="flex gap-2">
              <button class="btn-secondary flex-1" @click="startEdit">
                <UIcon name="i-lucide-square-pen" class="mr-1.5 h-4 w-4" />Modifier
              </button>
              <button class="btn-danger flex-1" @click="showDeleteConfirm = true">
                <UIcon name="i-lucide-trash-2" class="mr-1.5 h-4 w-4" />Supprimer
              </button>
            </div>
            <button class="btn-primary w-full" @click="$emit('markAsSold', prospect)">
              <UIcon name="i-lucide-shopping-cart" class="mr-1.5 h-4 w-4" />Marquer comme vendu
            </button>
          </div>

          <!-- Edit mode actions -->
          <div v-else class="flex gap-2">
            <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="cancelEdit">Annuler</button>
            <button type="submit" form="prospect-edit-form" class="btn-primary flex-1" :disabled="isSaving">
              <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
              Enregistrer
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Prospect, ProspectUpdatePayload } from '~/types'
import { updateProspect, deleteProspect as deleteProspectApi } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

// ─── Props & Emits ────────────────────────────────────────────────────────────

interface Props {
  /** Whether the drawer is visible */
  open: boolean
  /** Prospect to display — null means nothing is shown */
  prospect: Prospect | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  /** Close the drawer */
  close: []
  /** Prospect was successfully updated */
  updated: [prospect: Prospect]
  /** Prospect was deleted */
  deleted: [prospectId: number]
  /** User clicked "Add to campaign" */
  addToCampaign: [prospect: Prospect]
  /** User clicked "Send email" */
  sendEmail: [prospect: Prospect]
  /** User clicked "Marquer comme vendu" */
  markAsSold: [prospect: Prospect]
  /** User toggled the contacted status */
  toggleContacted: [prospect: Prospect]
}>()

// ─── State ────────────────────────────────────────────────────────────────────

const toast = useToast()

const editMode = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const showDeleteConfirm = ref(false)

interface EditForm {
  name: string
  phone: string
  email: string
  website: string
  address: string
  city: string
  category: string
}

const editForm = ref<EditForm>({
  name: '',
  phone: '',
  email: '',
  website: '',
  address: '',
  city: '',
  category: '',
})

// ─── Reset state when drawer closes or prospect changes ───────────────────────

watch(
  () => [props.open, props.prospect?.id],
  ([open]) => {
    if (!open) {
      // Give the closing animation time to complete before resetting
      setTimeout(() => {
        editMode.value = false
        showDeleteConfirm.value = false
      }, 250)
    }
  },
)

// ─── Computed ─────────────────────────────────────────────────────────────────

/** Confidence indicator dot colour */
const confidenceColor = computed((): string => {
  switch (props.prospect?.confidence) {
    case 1:
      return 'bg-[#dc4747]'
    case 2:
      return 'bg-[#e3b341]'
    case 3:
      return 'bg-[#58a6ff]'
    case 4:
      return 'bg-[#3fb950]'
    default:
      return 'bg-[#8b949e]'
  }
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format an ISO date string to a French locale date.
 * @param dateStr - ISO date string from the API.
 * @returns Human-readable date (e.g. "1 juin 2026").
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

// ─── Edit mode ────────────────────────────────────────────────────────────────

/**
 * Populate the edit form with the current prospect values and enter edit mode.
 */
function startEdit(): void {
  if (!props.prospect) return
  editForm.value = {
    name: props.prospect.name,
    phone: props.prospect.phone ?? '',
    email: props.prospect.email ?? '',
    website: props.prospect.website ?? '',
    address: props.prospect.address ?? '',
    city: props.prospect.city ?? '',
    category: props.prospect.category,
  }
  editMode.value = true
}

/** Exit edit mode without saving. */
function cancelEdit(): void {
  editMode.value = false
}

/**
 * Persist the edited fields via the REST API.
 * Emits `updated` on success so the parent can refresh its list.
 */
async function handleSave(): Promise<void> {
  if (!props.prospect) return
  isSaving.value = true
  try {
    const payload: ProspectUpdatePayload = {
      name: editForm.value.name || undefined,
      phone: editForm.value.phone || null,
      email: editForm.value.email || null,
      website: editForm.value.website || null,
      address: editForm.value.address || null,
      city: editForm.value.city || null,
      category: editForm.value.category || undefined,
    }
    const updated = await updateProspect(props.prospect.id, payload)
    emit('updated', updated)
    editMode.value = false
    toast.success('Prospect mis à jour')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  } finally {
    isSaving.value = false
  }
}

// ─── Delete ───────────────────────────────────────────────────────────────────

/**
 * Delete the current prospect after the inline confirmation.
 * Emits `deleted` then `close`.
 */
async function handleDelete(): Promise<void> {
  if (!props.prospect) return
  isDeleting.value = true
  try {
    await deleteProspectApi(props.prospect.id)
    emit('deleted', props.prospect.id)
    emit('close')
    toast.success(`Prospect « ${props.prospect.name} » supprimé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    isDeleting.value = false
    showDeleteConfirm.value = false
  }
}
</script>

<style scoped>
/* Backdrop fade */
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}

/* Panel slide from right */
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
