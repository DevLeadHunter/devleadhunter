<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 bottom-[var(--app-drawer-bottom)] z-50 flex w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 cursor-pointer items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon
              :name="isEditing ? 'i-lucide-user-pen' : 'i-lucide-user-plus'"
              class="h-4 w-4 text-[var(--app-ink-soft)]"
            />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ isEditing ? "Modifier l'utilisateur" : 'Ajouter un utilisateur' }}
            </h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              {{ isEditing ? props.user?.email : 'Il recevra ces identifiants pour se connecter' }}
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 cursor-pointer items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-4">
          <form id="user-form" class="space-y-4" @submit.prevent="submit">
            <div>
              <label class="app-label mb-1.5 block" for="user-form-name">
                Nom <span class="text-[var(--app-accent)]">*</span>
              </label>
              <input
                id="user-form-name"
                v-model="form.name"
                type="text"
                required
                autocomplete="name"
                placeholder="Jean Dupont"
                class="app-input"
              />
            </div>

            <div>
              <label class="app-label mb-1.5 block" for="user-form-email">
                Email <span class="text-[var(--app-accent)]">*</span>
              </label>
              <input
                id="user-form-email"
                v-model="form.email"
                type="email"
                required
                autocomplete="email"
                placeholder="jean@exemple.fr"
                class="app-input"
              />
            </div>

            <div v-if="!isEditing">
              <label class="app-label mb-1.5 block" for="user-form-password">
                Mot de passe <span class="text-[var(--app-accent)]">*</span>
              </label>
              <div class="relative">
                <input
                  id="user-form-password"
                  v-model="form.password"
                  :type="isPasswordVisible ? 'text' : 'password'"
                  required
                  autocomplete="new-password"
                  placeholder="Saisir un mot de passe"
                  class="app-input pr-10"
                />
                <button
                  type="button"
                  class="absolute top-1/2 right-3 -translate-y-1/2 cursor-pointer text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                  :aria-label="isPasswordVisible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
                  @click="isPasswordVisible = !isPasswordVisible"
                >
                  <UIcon :name="isPasswordVisible ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="h-4 w-4" />
                </button>
              </div>
            </div>

            <div v-if="!isEditing || canEditRole">
              <label class="app-label mb-1.5 block">Rôle</label>
              <UiSelectField v-model="roleValue" :options="ROLE_OPTIONS" :disabled="!canEditRole" />
              <p class="mt-1.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Un administrateur bénéficie de crédits illimités et accède au monitoring et au stockage.
              </p>
            </div>

            <UiCallout v-if="errorMessage" variant="danger">{{ errorMessage }}</UiCallout>
          </form>
        </div>

        <div class="flex flex-col gap-2 border-t border-[var(--app-line)] px-5 py-4 sm:flex-row">
          <button type="button" class="app-btn-secondary w-full sm:flex-1" :disabled="isSaving" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="user-form"
            class="app-btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50 sm:flex-1"
            :disabled="isSaving || !canSave"
          >
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
            {{ saveLabel }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UiUserFormDrawerEmits, UiUserFormDrawerProps, UserForm } from '~/types/UiUserFormDrawer'
import type { ComputedRef, EmitFn, PropType, Ref, WritableComputedRef } from 'vue'
import { computed, ref, watch } from 'vue'
import type { User, UserRole } from '~/types'
import { isSuperAdmin } from '~/utils/userRoles'
import type { UserFormDrawerMode } from '~/types/DrawerStack'
import type { SelectFieldOption } from '~/types/SelectField'
import { UsersService } from '~/services/usersService'

/** Drawer creating or editing a dashboard user (admin only). */
const props: UiUserFormDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String as PropType<UserFormDrawerMode>,
    default: 'create',
  },
  user: {
    type: Object as PropType<User | null>,
    default: null,
  },
})

const emit: EmitFn<UiUserFormDrawerEmits> = defineEmits<UiUserFormDrawerEmits>()

const ROLE_OPTIONS: SelectFieldOption[] = [
  { value: 'USER', label: 'Utilisateur' },
  { value: 'ADMIN', label: 'Administrateur' },
]

const form: Ref<UserForm> = ref(createEmptyForm())
const isPasswordVisible: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const errorMessage: Ref<string | null> = ref(null)

const userStore: ReturnType<typeof useUserStore> = useUserStore()

const isEditing: ComputedRef<boolean> = computed((): boolean => props.mode === 'edit')

const canEditRole: ComputedRef<boolean> = computed(
  (): boolean =>
    isSuperAdmin(userStore.user?.role) &&
    (!isEditing.value || (props.user?.role !== 'SUPER_ADMIN' && props.user?.id !== userStore.user?.id)),
)

/** The select binds a plain string while the form holds the narrowed role union. */
const roleValue: WritableComputedRef<string> = computed({
  get: (): string => form.value.role,
  set: (value: string): void => {
    form.value.role = value as UserRole
  },
})

const canSave: ComputedRef<boolean> = computed((): boolean => {
  const hasIdentity: boolean = Boolean(form.value.name.trim() && form.value.email.trim())
  return isEditing.value ? hasIdentity : hasIdentity && form.value.password.length > 0
})

const saveLabel: ComputedRef<string> = computed((): string => {
  if (isSaving.value) return isEditing.value ? 'Enregistrement…' : 'Création…'
  return isEditing.value ? 'Enregistrer' : "Créer l'utilisateur"
})

/**
 * Build a blank user form.
 * @returns An empty form with the default role.
 */
function createEmptyForm(): UserForm {
  return { name: '', email: '', password: '', role: 'USER' }
}

/**
 * Create or update the user, then hand the result back to the host.
 * @returns A promise resolved once the user is saved.
 */
async function submit(): Promise<void> {
  if (!canSave.value) return
  isSaving.value = true
  errorMessage.value = null
  try {
    const identity: { name: string; email: string } = {
      name: form.value.name.trim(),
      email: form.value.email.trim(),
    }
    const saved: User =
      isEditing.value && props.user
        ? await UsersService.updateUser(props.user.id, {
            ...identity,
            ...(canEditRole.value ? { role: form.value.role } : {}),
          })
        : await UsersService.createUser({ ...identity, password: form.value.password, role: form.value.role })
    emit('saved', saved)
  } catch (err: unknown) {
    errorMessage.value = err instanceof Error ? err.message : "Impossible d'enregistrer l'utilisateur"
  } finally {
    isSaving.value = false
  }
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (!open) return
    const editedUser: User | null = props.user ?? null
    form.value = editedUser
      ? { name: editedUser.name, email: editedUser.email, password: '', role: editedUser.role }
      : createEmptyForm()
    isPasswordVisible.value = false
    errorMessage.value = null
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
