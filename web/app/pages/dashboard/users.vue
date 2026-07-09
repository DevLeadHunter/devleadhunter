<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[var(--app-ink)]">Users</h1>
      <button class="btn-primary" @click="showCreateModal = true">
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>Add User</span>
      </button>
    </div>

    <!-- Search Bar -->
    <div class="card mb-6">
      <div class="relative">
        <i class="fa-solid fa-magnifying-glass absolute top-1/2 left-3 -translate-y-1/2 text-[var(--app-ink-soft)]"></i>
        <input v-model="searchQuery" type="text" placeholder="Search by name or email" class="input-field pl-10" />
      </div>
    </div>

    <!-- Users Table -->
    <div class="card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-[var(--app-line)] bg-[var(--app-bg)]">
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                User
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Email
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Role
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Credits Available
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Credits Consumed
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
                  Unlimited
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
                    <i class="fa-solid fa-ellipsis-vertical h-5 w-5"></i>
                  </button>
                  <!-- Dropdown Menu -->
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
                      <i class="fa-solid fa-pen-to-square mr-2 w-4"></i>
                      Edit User
                    </button>
                    <button
                      class="w-full px-4 py-2 text-left text-sm text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/20"
                      @click="handleDelete(user)"
                    >
                      <i class="fa-solid fa-trash mr-2 w-4"></i>
                      Delete User
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-5/6 rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredUsers.length === 0" class="card py-12 text-center">
      <i class="fa-solid fa-users mb-3 text-5xl text-[var(--app-ink-soft)]"></i>
      <p class="text-[var(--app-ink-soft)]">No users found</p>
    </div>

    <!-- Create User Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)]"
      @click.self="showCreateModal = false"
    >
      <div class="w-full max-w-md rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Add New User</h2>
        <form @submit.prevent="handleCreateSubmit">
          <!-- Name -->
          <div class="mb-4">
            <label for="create-name" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Name </label>
            <input
              id="create-name"
              v-model="createForm.name"
              type="text"
              required
              placeholder="John Doe"
              class="input-field"
            />
          </div>

          <!-- Email -->
          <div class="mb-4">
            <label for="create-email" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]">
              Email
            </label>
            <input
              id="create-email"
              v-model="createForm.email"
              type="email"
              required
              placeholder="john@example.com"
              class="input-field"
            />
          </div>

          <!-- Password -->
          <div class="mb-4">
            <label for="create-password" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]">
              Password
            </label>
            <div class="relative">
              <input
                id="create-password"
                v-model="createForm.password"
                :type="showCreatePassword ? 'text' : 'password'"
                required
                placeholder="Enter password"
                class="input-field pr-10"
              />
              <button
                type="button"
                class="absolute top-1/2 right-3 -translate-y-1/2 text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
                @click="showCreatePassword = !showCreatePassword"
              >
                <i :class="showCreatePassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'" class="h-4 w-4"></i>
              </button>
            </div>
          </div>

          <!-- Role -->
          <div class="mb-4">
            <label for="create-role" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Role </label>
            <select id="create-role" v-model="createForm.role" class="input-field">
              <option value="USER">USER</option>
              <option value="ADMIN">ADMIN</option>
            </select>
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showCreateModal = false">Cancel</button>
            <button type="submit" :disabled="isCreating" class="btn-primary flex-1">
              <span v-if="isCreating">Creating...</span>
              <span v-else>Create User</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit User Modal -->
    <div
      v-if="showEditModal && editingUser"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)]"
      @click.self="showEditModal = false"
    >
      <div class="w-full max-w-md rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Edit User</h2>
        <form @submit.prevent="handleEditSubmit">
          <!-- Name -->
          <div class="mb-4">
            <label for="edit-name" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Name </label>
            <input
              id="edit-name"
              v-model="editForm.name"
              type="text"
              required
              placeholder="John Doe"
              class="input-field"
            />
          </div>

          <!-- Email -->
          <div class="mb-4">
            <label for="edit-email" class="mb-1.5 block text-xs font-medium text-[var(--app-ink-soft)]"> Email </label>
            <input
              id="edit-email"
              v-model="editForm.email"
              type="email"
              required
              placeholder="john@example.com"
              class="input-field"
            />
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showEditModal = false">Cancel</button>
            <button type="submit" :disabled="isEditing" class="btn-primary flex-1">
              <span v-if="isEditing">Saving...</span>
              <span v-else>Save Changes</span>
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="showDeleteModal && deletingUser"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)]"
      @click.self="showDeleteModal = false"
    >
      <div class="w-full max-w-md rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Delete User</h2>
        <p class="mb-6 text-sm text-[var(--app-ink-soft)]">
          Are you sure you want to delete <strong class="text-[var(--app-ink)]">{{ deletingUser.name }}</strong
          >? This action cannot be undone.
        </p>
        <div class="flex gap-3">
          <button type="button" class="btn-secondary flex-1" @click="showDeleteModal = false">Cancel</button>
          <button :disabled="isDeleting" class="btn-danger flex-1" @click="confirmDelete">
            <span v-if="isDeleting">Deleting...</span>
            <span v-else>Delete User</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { User } from '~/types'
import type { Ref } from 'vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import * as usersService from '~/services/usersService'
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
const createForm: Ref<{ name: string; email: string; password: string; role: string }> = ref({
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
const toast = useToast()

/**
 * Filtered users based on search query
 */
const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const query = searchQuery.value.toLowerCase()
  return users.value.filter(
    (user) => user.name.toLowerCase().includes(query) || user.email.toLowerCase().includes(query),
  )
})

/**
 * Get user initials
 * @param {string} name - User name
 * @returns {string} User initials
 */
const getUserInitials = (name: string): string => {
  const parts = name.split(' ')
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

/**
 * Toggle user menu
 * @param {number} userId - User ID
 * @param {Event} event - Click event
 * @returns {void}
 */
const toggleUserMenu = (userId: number, event?: Event): void => {
  if (event) {
    event.stopPropagation()
  }
  openMenuId.value = openMenuId.value === userId ? null : userId
}

/**
 * Close menu on outside click
 * @param {Event} event - Click event
 * @returns {void}
 */
const handleClickOutside = (event: Event): void => {
  const target = event.target as HTMLElement
  // Check if click is outside all menu buttons and dropdowns
  const isClickInsideMenu = target.closest('.user-menu-container')
  if (!isClickInsideMenu && openMenuId.value !== null) {
    openMenuId.value = null
  }
}

/**
 * Load users from API
 * @returns {Promise<void>}
 */
const loadUsers = async (): Promise<void> => {
  try {
    isLoading.value = true
    users.value = await usersService.getAllUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to load users')
  } finally {
    isLoading.value = false
  }
}

/**
 * Handle create user form submission
 * @returns {Promise<void>}
 */
const handleCreateSubmit = async (): Promise<void> => {
  try {
    isCreating.value = true
    await usersService.createUser(createForm.value)
    toast.success('User created successfully')
    showCreateModal.value = false
    createForm.value = { name: '', email: '', password: '', role: 'USER' }
    await loadUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to create user')
  } finally {
    isCreating.value = false
  }
}

/**
 * Handle edit user
 * @param {User} user - User to edit
 * @returns {void}
 */
const handleEdit = (user: User): void => {
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
const handleEditSubmit = async (): Promise<void> => {
  if (!editingUser.value) return

  try {
    isEditing.value = true
    await usersService.updateUser(editingUser.value.id, editForm.value)
    toast.success('User updated successfully')
    showEditModal.value = false
    editingUser.value = null
    await loadUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to update user')
  } finally {
    isEditing.value = false
  }
}

/**
 * Handle delete user
 * @param {User} user - User to delete
 * @returns {void}
 */
const handleDelete = (user: User): void => {
  deletingUser.value = user
  openMenuId.value = null
  showDeleteModal.value = true
}

/**
 * Confirm user deletion
 * @returns {Promise<void>}
 */
const confirmDelete = async (): Promise<void> => {
  if (!deletingUser.value) return

  try {
    isDeleting.value = true
    await usersService.deleteUser(deletingUser.value.id)
    toast.success('User deleted successfully')
    showDeleteModal.value = false
    deletingUser.value = null
    await loadUsers()
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to delete user')
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
