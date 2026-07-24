<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[var(--app-ink)]">Utilisateurs</h1>
      <button class="btn-primary" @click="showCreateModal = true">
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        <span>Ajouter un utilisateur</span>
      </button>
    </div>

    <div class="card mb-6">
      <div class="relative">
        <UIcon
          name="i-lucide-search"
          class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--app-ink-soft)]"
        />
        <input v-model="searchQuery" type="text" placeholder="Rechercher par nom ou email" class="input-field pl-10" />
      </div>
    </div>

    <div class="card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-[var(--app-line)] bg-[var(--app-bg)]">
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Utilisateur
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Email
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Rôle
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Crédits disponibles
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Crédits consommés
              </th>
              <th class="px-4 py-3 text-right text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(user, index) in filteredUsers"
              :key="user.id"
              class="border-b border-[var(--app-line)] transition-colors last:border-b-0 hover:bg-[var(--app-surface-2)]"
            >
              <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                <div class="flex items-center gap-2">
                  <div
                    class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-bg)]"
                  >
                    <span class="text-xs font-semibold text-[var(--app-ink)]">
                      {{ getUserInitials(user.name) }}
                    </span>
                  </div>
                  <span class="font-medium">{{ user.name }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-[var(--app-ink)]">{{ user.email }}</td>
              <td class="px-4 py-3 text-sm">
                <span
                  :class="[
                    'inline-flex items-center rounded px-2.5 py-0.5 text-xs font-medium',
                    user.role === 'ADMIN'
                      ? 'border border-[var(--app-red)]/30 bg-[var(--app-red)]/20 text-[var(--app-red)]'
                      : 'border border-[var(--app-green)]/30 bg-[var(--app-green)]/20 text-[var(--app-green)]',
                  ]"
                >
                  {{ user.role }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                <span
                  v-if="user.credits_available === -1 || user.credits_available === null"
                  class="text-[var(--app-ink-soft)]"
                >
                  Illimités
                </span>
                <span v-else class="font-medium">
                  {{ user.credits_available }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-[var(--app-ink)]">
                <span class="font-medium">
                  {{ user.credits_consumed ?? 0 }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="user-menu-container relative inline-block">
                  <button
                    class="text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                    @click="toggleUserMenu(user.id, $event)"
                  >
                    <UIcon name="i-lucide-ellipsis-vertical" class="h-5 w-5" />
                  </button>

                  <div
                    v-if="openMenuId === user.id"
                    :class="[
                      'absolute right-0 z-10 w-48 rounded border border-[var(--app-line)] bg-[var(--app-surface)] shadow-lg',
                      index >= filteredUsers.length - 2 ? 'bottom-full mb-1' : 'top-full mt-1',
                    ]"
                  >
                    <button
                      class="w-full px-4 py-2 text-left text-sm text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                      @click="handleEdit(user)"
                    >
                      <UIcon name="i-lucide-square-pen" class="mr-2 h-4 w-4" />
                      Modifier
                    </button>
                    <button
                      class="w-full px-4 py-2 text-left text-sm text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/20"
                      @click="handleDelete(user)"
                    >
                      <UIcon name="i-lucide-trash-2" class="mr-2 h-4 w-4" />
                      Supprimer
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-5/6 rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <UiEmptyState v-else-if="filteredUsers.length === 0" title="Aucun utilisateur trouvé" />

    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)]"
      @click.self="showCreateModal = false"
    >
      <div class="w-full max-w-md rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Ajouter un utilisateur</h2>
        <form @submit.prevent="handleCreateSubmit">
          <div class="mb-4">
            <label for="create-name" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Nom </label>
            <input
              id="create-name"
              v-model="createForm.name"
              type="text"
              required
              placeholder="Jean Dupont"
              class="input-field"
            />
          </div>

          <div class="mb-4">
            <label for="create-email" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]">
              Email
            </label>
            <input
              id="create-email"
              v-model="createForm.email"
              type="email"
              required
              placeholder="jean@exemple.fr"
              class="input-field"
            />
          </div>

          <div class="mb-4">
            <label for="create-password" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]">
              Mot de passe
            </label>
            <div class="relative">
              <input
                id="create-password"
                v-model="createForm.password"
                :type="showCreatePassword ? 'text' : 'password'"
                required
                placeholder="Saisir un mot de passe"
                class="input-field pr-10"
              />
              <button
                type="button"
                class="absolute top-1/2 right-3 -translate-y-1/2 text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                @click="showCreatePassword = !showCreatePassword"
              >
                <UIcon :name="showCreatePassword ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="h-4 w-4" />
              </button>
            </div>
          </div>

          <div class="mb-4">
            <label for="create-role" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Rôle </label>
            <select id="create-role" v-model="createForm.role" class="input-field">
              <option value="USER">USER</option>
              <option value="ADMIN">ADMIN</option>
            </select>
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showCreateModal = false">Annuler</button>
            <button type="submit" :disabled="isCreating" class="btn-primary flex-1">
              <span v-if="isCreating">Création…</span>
              <span v-else>Créer l'utilisateur</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <div
      v-if="showEditModal && editingUser"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)]"
      @click.self="showEditModal = false"
    >
      <div class="w-full max-w-md rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Modifier l'utilisateur</h2>
        <form @submit.prevent="handleEditSubmit">
          <div class="mb-4">
            <label for="edit-name" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Nom </label>
            <input
              id="edit-name"
              v-model="editForm.name"
              type="text"
              required
              placeholder="Jean Dupont"
              class="input-field"
            />
          </div>

          <div class="mb-4">
            <label for="edit-email" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Email </label>
            <input
              id="edit-email"
              v-model="editForm.email"
              type="email"
              required
              placeholder="jean@exemple.fr"
              class="input-field"
            />
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showEditModal = false">Annuler</button>
            <button type="submit" :disabled="isEditing" class="btn-primary flex-1">
              <span v-if="isEditing">Enregistrement…</span>
              <span v-else>Enregistrer</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <div
      v-if="showDeleteModal && deletingUser"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)]"
      @click.self="showDeleteModal = false"
    >
      <div class="w-full max-w-md rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Supprimer l'utilisateur</h2>
        <p class="mb-6 text-sm text-[var(--app-ink-soft)]">
          Supprimer <strong class="text-[var(--app-ink)]">{{ deletingUser.name }}</strong> ? Cette action est
          irréversible.
        </p>
        <div class="flex gap-3">
          <button type="button" class="btn-secondary flex-1" @click="showDeleteModal = false">Annuler</button>
          <button :disabled="isDeleting" class="btn-danger flex-1" @click="confirmDelete">
            <span v-if="isDeleting">Suppression…</span>
            <span v-else>Supprimer</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { UserRole, User } from '~/types'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { UsersService } from '~/services/usersService'
import { useToast } from '~/composables/useToast'

/**
 * Dashboard users page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin'],
})

/**
 * Users list state
 */
const users: Ref<User[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const searchQuery: Ref<string> = ref('')

/**
 * Modal states
 */
const showCreateModal: Ref<boolean> = ref(false)
const showEditModal: Ref<boolean> = ref(false)
const showDeleteModal: Ref<boolean> = ref(false)
const openMenuId: Ref<number | null> = ref(null)

/**
 * Form states
 */
const createForm: Ref<{ name: string; email: string; password: string; role: UserRole }> = ref({
  name: '',
  email: '',
  password: '',
  role: 'USER',
})
const editForm: Ref<{ name: string; email: string }> = ref({
  name: '',
  email: '',
})
const showCreatePassword: Ref<boolean> = ref(false)

/**
 * Editing/Deleting states
 */
const editingUser: Ref<User | null> = ref(null)
const deletingUser: Ref<User | null> = ref(null)
const isCreating: Ref<boolean> = ref(false)
const isEditing: Ref<boolean> = ref(false)
const isDeleting: Ref<boolean> = ref(false)

/**
 * Toast composable
 */
const toast: UseToastReturn = useToast()

/**
 * Filtered users based on search query
 */
const filteredUsers: ComputedRef<User[]> = computed(() => {
  if (!searchQuery.value) return users.value
  const query: string = searchQuery.value.toLowerCase()
  return users.value.filter(
    (user: User) => user.name.toLowerCase().includes(query) || user.email.toLowerCase().includes(query),
  )
})

/**
 * Get user initials
 * @param name - User name
 * @returns User initials
 */
const getUserInitials: (name: string) => string = (name: string): string => {
  const parts: string[] = name.split(' ')
  if (parts.length >= 2) {
    return `${parts[0]?.[0] ?? ''}${parts[1]?.[0] ?? ''}`.toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

/**
 * Toggle user menu
 * @param userId - User ID
 * @param event - Click event
 */
const toggleUserMenu: (userId: number, event?: Event) => void = (userId: number, event?: Event): void => {
  if (event) {
    event.stopPropagation()
  }
  openMenuId.value = openMenuId.value === userId ? null : userId
}

/**
 * Close menu on outside click
 * @param event - Click event
 */
const handleClickOutside: (event: Event) => void = (event: Event): void => {
  const target: HTMLElement = event.target as HTMLElement
  // Check if click is outside all menu buttons and dropdowns
  const isClickInsideMenu: Element | null = target.closest('.user-menu-container')
  if (!isClickInsideMenu && openMenuId.value !== null) {
    openMenuId.value = null
  }
}

/**
 * Load users from API
 * @returns {Promise<void>}
 */
const loadUsers: () => Promise<void> = async (): Promise<void> => {
  try {
    isLoading.value = true
    users.value = await UsersService.getAllUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Erreur lors du chargement des utilisateurs')
  } finally {
    isLoading.value = false
  }
}

/**
 * Handle create user form submission
 * @returns {Promise<void>}
 */
const handleCreateSubmit: () => Promise<void> = async (): Promise<void> => {
  try {
    isCreating.value = true
    await UsersService.createUser(createForm.value)
    toast.success('Utilisateur créé')
    showCreateModal.value = false
    createForm.value = { name: '', email: '', password: '', role: 'USER' }
    await loadUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Erreur lors de la création de l'utilisateur")
  } finally {
    isCreating.value = false
  }
}

/**
 * Handle edit user
 * @param user - User to edit
 */
const handleEdit: (user: User) => void = (user: User): void => {
  editingUser.value = user
  editForm.value = {
    name: user.name,
    email: user.email,
  }
  openMenuId.value = null
  showEditModal.value = true
}

/**
 * Handle edit user form submission
 * @returns {Promise<void>}
 */
const handleEditSubmit: () => Promise<void> = async (): Promise<void> => {
  if (!editingUser.value) return

  try {
    isEditing.value = true
    await UsersService.updateUser(editingUser.value.id, editForm.value)
    toast.success('Utilisateur mis à jour')
    showEditModal.value = false
    editingUser.value = null
    await loadUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Erreur lors de la mise à jour')
  } finally {
    isEditing.value = false
  }
}

/**
 * Handle delete user
 * @param user - User to delete
 */
const handleDelete: (user: User) => void = (user: User): void => {
  deletingUser.value = user
  openMenuId.value = null
  showDeleteModal.value = true
}

/**
 * Confirm user deletion
 * @returns {Promise<void>}
 */
const confirmDelete: () => Promise<void> = async (): Promise<void> => {
  if (!deletingUser.value) return

  try {
    isDeleting.value = true
    await UsersService.deleteUser(deletingUser.value.id)
    toast.success('Utilisateur supprimé')
    showDeleteModal.value = false
    deletingUser.value = null
    await loadUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Erreur lors de la suppression')
  } finally {
    isDeleting.value = false
  }
}

/**
 * Initialize component
 */
onMounted(() => {
  loadUsers()
  // Add event listener for outside clicks
  if (import.meta.client) {
    document.addEventListener('click', handleClickOutside)
  }
})

/**
 * Cleanup on component unmount
 */
onUnmounted(() => {
  if (import.meta.client) {
    document.removeEventListener('click', handleClickOutside)
  }
})
</script>
