<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
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
            class="font-label flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--app-ink)] text-xs font-semibold text-[var(--app-surface)]"
          >
            {{ userInitials }}
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Mon profil</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">Modifiez vos informations de compte</p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <form id="profile-form" class="flex-1 space-y-4 overflow-y-auto px-5 py-4" @submit.prevent="handleSave">
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="profile-name">Nom</label>
            <input
              id="profile-name"
              v-model="form.name"
              type="text"
              required
              class="input-field"
              placeholder="Jean Dupont"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="profile-email"> Email de connexion </label>
            <input
              id="profile-email"
              v-model="form.email"
              type="email"
              required
              class="input-field"
              placeholder="jean@exemple.fr"
            />
            <UiCallout variant="info" class="mt-3">
              Cette adresse sert uniquement à
              <strong class="font-medium text-[var(--app-ink)]">vous connecter</strong> à DevLeadHunter. L'adresse
              d'<strong class="font-medium text-[var(--app-ink)]">envoi</strong> de vos emails de prospection se règle
              dans
              <NuxtLink
                to="/dashboard/settings/sending"
                class="font-medium text-[var(--app-blue)] underline underline-offset-2 transition-opacity hover:opacity-80"
                @click="emit('close')"
                >Configuration d'envoi</NuxtLink
              >.
            </UiCallout>
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="profile-company">
              Nom de l'entreprise <span class="text-[var(--app-ink-soft)]">(facultatif)</span>
            </label>
            <input
              id="profile-company"
              v-model="form.company_name"
              type="text"
              class="input-field"
              placeholder="Ex : Dibodev"
            />
            <p class="text-muted mt-1.5 text-xs">
              Utilisé dans les suggestions IA et comme nom affiché dans la configuration d'envoi.
            </p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium" for="profile-company-website">
              Site web de l'entreprise <span class="text-[var(--app-ink-soft)]">(facultatif)</span>
            </label>
            <input
              id="profile-company-website"
              v-model="form.company_website_url"
              type="url"
              class="input-field"
              placeholder="Ex : https://dibodev.fr"
            />
            <p class="text-muted mt-1.5 text-xs">
              Lien de la signature « Site réalisé par… » affichée sur vos pages vidéo de prospection.
            </p>
          </div>
        </form>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="profile-form"
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
import type { ProfileForm, UiProfileDrawerEmits } from '~/types/UiProfileDrawer'
import type { ComputedRef, EmitFn, Ref } from 'vue'
import type { UiDrawerProps } from '~/types/UiDrawer'
import { computed, ref, watch } from 'vue'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'

/** User profile and password drawer. */
const props: UiDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProfileDrawerEmits> = defineEmits<UiProfileDrawerEmits>()

const userStore: ReturnType<typeof useUserStore> = useUserStore()

const toast: UseToastReturn = useToast()

/** Whether the save request is in flight. */
const isSaving: Ref<boolean> = ref(false)

/** Editable profile form state. */
const form: Ref<ProfileForm> = ref({ name: '', email: '', company_name: '', company_website_url: '' })

/** Initials shown in the header avatar. */
const userInitials: ComputedRef<string> = computed((): string => {
  const name: string = userStore.userName || ''
  if (!name) return 'U'
  const parts: string[] = name.split(' ')
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
})

/**
 * Persist the edited profile.
 * @returns A promise that resolves once the profile is saved.
 */
async function handleSave(): Promise<void> {
  isSaving.value = true
  try {
    await userStore.updateProfile({
      name: form.value.name,
      email: form.value.email,
      company_name: form.value.company_name.trim() || null,
      company_website_url: form.value.company_website_url.trim() || null,
    })
    toast.success('Profil mis à jour')
    emit('close')
  } catch {
    toast.error('Erreur lors de la mise à jour du profil')
  } finally {
    isSaving.value = false
  }
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) {
      form.value = {
        name: userStore.user?.name ?? '',
        email: userStore.user?.email ?? '',
        company_name: userStore.user?.company_name ?? '',
        company_website_url: userStore.user?.company_website_url ?? '',
      }
    }
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
