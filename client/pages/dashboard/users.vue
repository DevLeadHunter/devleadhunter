<template>
  <div>
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Users</h1>
      <button
        @click="showCreateModal = true"
        class="btn-primary"
      >
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>Add User</span>
      </button>
    </div>

    <!-- Search Bar -->
    <div class="card mb-6">
      <div class="relative">
        <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-[#8b949e]"></i>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name or email"
          class="input-field pl-10"
        />
      </div>
    </div>

    <!-- Users Table -->
    <div class="card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="bg-[#050505] border-b border-[#30363d]">
              <th class="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                User
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                Email
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                Role
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                Credits Available
              </th>
              <th class="px-4 py-3 text-left text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                Credits Consumed
              </th>
              <th class="px-4 py-3 text-right text-xs font-medium text-[#8b949e] uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(user, index) in filteredUsers"
              :key="user.id"
              class="hover:bg-[#2a2a2a] border-b border-[#30363d] last:border-b-0 transition-colors"
            >
              <td class="px-4 py-3 text-sm text-[#f9f9f9]">
                <div class="flex items-center gap-2">
                  <div class="w-8 h-8 rounded-full bg-[#050505] border border-[#30363d] flex items-center justify-center flex-shrink-0">
                    <span class="text-[#f9f9f9] text-xs font-semibold">
                      {{ getUserInitials(user.name) }}
                    </span>
                  </div>
                  <span class="font-medium">{{ user.name }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-sm text-[#f9f9f9]">{{ user.email }}</td>
              <td class="px-4 py-3 text-sm">
                <span
                  :class="[
                    'px-2.5 py-0.5 rounded text-xs font-medium inline-flex items-center',
                    user.role === 'ADMIN' 
                      ? 'bg-[#da3633]/20 text-[#DC4747] border border-[#da3633]/30' 
                      : 'bg-[#2BAD5F]/20 text-[#3fb950] border border-[#2BAD5F]/30'
                  ]"
                >
                  {{ user.role }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-[#f9f9f9]">
                <span v-if="user.credits_available === -1 || user.credits_available === null" class="text-[#8b949e]">
                  Unlimited
                </span>
                <span v-else class="font-medium">
                  {{ user.credits_available }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-[#f9f9f9]">
                <span class="font-medium">
                  {{ user.credits_consumed ?? 0 }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="relative inline-block user-menu-container">
                  <button
                    @click="toggleUserMenu(user.id, $event)"
                    class="text-[#8b949e] hover:text-[#f9f9f9] transition-colors"
                  >
                    <i class="fa-solid fa-ellipsis-vertical w-5 h-5"></i>
                  </button>
                  <!-- Dropdown Menu -->
                  <div
                    v-if="openMenuId === user.id"
                    :class="[
                      'absolute right-0 w-48 bg-[#1a1a1a] border border-[#30363d] rounded shadow-lg z-10',
                      index >= filteredUsers.length - 2
                        ? 'bottom-full mb-1'
                        : 'top-full mt-1'
                    ]"
                  >
                    <button
                      @click="handleEdit(user)"
                      class="w-full px-4 py-2 text-left text-sm text-[#f9f9f9] hover:bg-[#2a2a2a] transition-colors"
                    >
                      <i class="fa-solid fa-pen-to-square mr-2 w-4"></i>
                      Edit User
                    </button>
                    <button
                      @click="handleDelete(user)"
                      class="w-full px-4 py-2 text-left text-sm text-[#DC4747] hover:bg-[#da3633]/20 transition-colors"
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
        <div class="h-4 bg-[#2a2a2a] rounded w-3/4"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-5/6"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredUsers.length === 0" class="card text-center py-12">
      <i class="fa-solid fa-users text-5xl text-[#8b949e] mb-3"></i>
      <p class="text-[#8b949e]">No users found</p>
    </div>

    <!-- Create User Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      @click.self="showCreateModal = false"
    >
      <div class="bg-[#1a1a1a] border border-[#30363d] rounded-lg p-6 w-full max-w-md shadow-lg">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Add New User</h2>
        <form @submit.prevent="handleCreateSubmit">
          <!-- Name -->
          <div class="mb-4">
            <label for="create-name" class="block text-xs font-medium text-[#8b949e] mb-1.5">
              Name
            </label>
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
            <label for="create-email" class="block text-xs font-medium text-[#8b949e] mb-1.5">
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
            <label for="create-password" class="block text-xs font-medium text-[#8b949e] mb-1.5">
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
                @click="showCreatePassword = !showCreatePassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-[#8b949e] hover:text-[#f9f9f9] transition-colors"
              >
                <i :class="showCreatePassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'" class="w-4 h-4"></i>
              </button>
            </div>
          </div>

          <!-- Role -->
          <div class="mb-4">
            <label for="create-role" class="block text-xs font-medium text-[#8b949e] mb-1.5">
              Role
            </label>
            <select
              id="create-role"
              v-model="createForm.role"
              class="input-field"
            >
              <option value="USER">USER</option>
              <option value="ADMIN">ADMIN</option>
            </select>
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="showCreateModal = false"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isCreating"
              class="btn-primary flex-1"
            >
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
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      @click.self="showEditModal = false"
    >
      <div class="bg-[#1a1a1a] border border-[#30363d] rounded-lg p-6 w-full max-w-md shadow-lg">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Edit User</h2>
        <form @submit.prevent="handleEditSubmit">
          <!-- Name -->
          <div class="mb-4">
            <label for="edit-name" class="block text-xs font-medium text-[#8b949e] mb-1.5">
              Name
            </label>
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
            <label for="edit-email" class="block text-xs font-medium text-[#8b949e] mb-1.5">
              Email
            </label>
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
            <button
              type="button"
              @click="showEditModal = false"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isEditing"
              class="btn-primary flex-1"
            >
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
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      @click.self="showDeleteModal = false"
    >
      <div class="bg-[#1a1a1a] border border-[#30363d] rounded-lg p-6 w-full max-w-md shadow-lg">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Delete User</h2>
        <p class="text-sm text-[#8b949e] mb-6">
          Are you sure you want to delete <strong class="text-[#f9f9f9]">{{ deletingUser.name }}</strong>? This action cannot be undone.
        </p>
        <div class="flex gap-3">
          <button
            type="button"
            @click="showDeleteModal = false"
            class="btn-secondary flex-1"
          >
            Cancel
          </button>
          <button
            @click="confirmDelete"
            :disabled="isDeleting"
            class="btn-danger flex-1"
          >
            <span v-if="isDeleting">Deleting...</span>
            <span v-else>Delete User</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { User } from '~/types';
import type { Ref } from 'vue';
import { ref, computed, onMounted, onUnmounted } from 'vue';
import * as usersService from '~/services/usersService';
import { useToast } from '~/composables/useToast';

/**
 * Dashboard users page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin']
});

/**
 * Users list state
 */
const users: Ref<User[]> = ref([]);
const isLoading: Ref<boolean> = ref(false);
const searchQuery: Ref<string> = ref('');

/**
 * Modal states
 */
const showCreateModal: Ref<boolean> = ref(false);
const showEditModal: Ref<boolean> = ref(false);
const showDeleteModal: Ref<boolean> = ref(false);
const openMenuId: Ref<number | null> = ref(null);

/**
 * Form states
 */
const createForm: Ref<{ name: string; email: string; password: string; role: string }> = ref({
  name: '',
  email: '',
  password: '',
  role: 'USER'
});
const editForm: Ref<{ name: string; email: string }> = ref({
  name: '',
  email: ''
});
const showCreatePassword: Ref<boolean> = ref(false);

/**
 * Editing/Deleting states
 */
const editingUser: Ref<User | null> = ref(null);
const deletingUser: Ref<User | null> = ref(null);
const isCreating: Ref<boolean> = ref(false);
const isEditing: Ref<boolean> = ref(false);
const isDeleting: Ref<boolean> = ref(false);

/**
 * Toast composable
 */
const toast = useToast();

/**
 * Filtered users based on search query
 */
const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value;
  const query = searchQuery.value.toLowerCase();
  return users.value.filter(user => 
    user.name.toLowerCase().includes(query) || 
    user.email.toLowerCase().includes(query)
  );
});

/**
 * Get user initials
 * @param {string} name - User name
 * @returns {string} User initials
 */
const getUserInitials = (name: string): string => {
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
};

/**
 * Toggle user menu
 * @param {number} userId - User ID
 * @param {Event} event - Click event
 * @returns {void}
 */
const toggleUserMenu = (userId: number, event?: Event): void => {
  if (event) {
    event.stopPropagation();
  }
  openMenuId.value = openMenuId.value === userId ? null : userId;
};

/**
 * Close menu on outside click
 * @param {Event} event - Click event
 * @returns {void}
 */
const handleClickOutside = (event: Event): void => {
  const target = event.target as HTMLElement;
  // Check if click is outside all menu buttons and dropdowns
  const isClickInsideMenu = target.closest('.user-menu-container');
  if (!isClickInsideMenu && openMenuId.value !== null) {
    openMenuId.value = null;
  }
};

/**
 * Load users from API
 * @returns {Promise<void>}
 */
const loadUsers = async (): Promise<void> => {
  try {
    isLoading.value = true;
    users.value = await usersService.getAllUsers();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to load users');
  } finally {
    isLoading.value = false;
  }
};

/**
 * Handle create user form submission
 * @returns {Promise<void>}
 */
const handleCreateSubmit = async (): Promise<void> => {
  try {
    isCreating.value = true;
    await usersService.createUser(createForm.value);
    toast.success('User created successfully');
    showCreateModal.value = false;
    createForm.value = { name: '', email: '', password: '', role: 'USER' };
    await loadUsers();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to create user');
  } finally {
    isCreating.value = false;
  }
};

/**
 * Handle edit user
 * @param {User} user - User to edit
 * @returns {void}
 */
const handleEdit = (user: User): void => {
  editingUser.value = user;
  editForm.value = {
    name: user.name,
    email: user.email
  };
  openMenuId.value = null;
  showEditModal.value = true;
};

/**
 * Handle edit user form submission
 * @returns {Promise<void>}
 */
const handleEditSubmit = async (): Promise<void> => {
  if (!editingUser.value) return;
  
  try {
    isEditing.value = true;
    await usersService.updateUser(editingUser.value.id, editForm.value);
    toast.success('User updated successfully');
    showEditModal.value = false;
    editingUser.value = null;
    await loadUsers();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to update user');
  } finally {
    isEditing.value = false;
  }
};

/**
 * Handle delete user
 * @param {User} user - User to delete
 * @returns {void}
 */
const handleDelete = (user: User): void => {
  deletingUser.value = user;
  openMenuId.value = null;
  showDeleteModal.value = true;
};

/**
 * Confirm user deletion
 * @returns {Promise<void>}
 */
const confirmDelete = async (): Promise<void> => {
  if (!deletingUser.value) return;
  
  try {
    isDeleting.value = true;
    await usersService.deleteUser(deletingUser.value.id);
    toast.success('User deleted successfully');
    showDeleteModal.value = false;
    deletingUser.value = null;
    await loadUsers();
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Failed to delete user');
  } finally {
    isDeleting.value = false;
  }
};

/**
 * Initialize component
 */
onMounted(() => {
  loadUsers();
  // Add event listener for outside clicks
  if (process.client) {
    document.addEventListener('click', handleClickOutside);
  }
});

/**
 * Cleanup on component unmount
 */
onUnmounted(() => {
  if (process.client) {
    document.removeEventListener('click', handleClickOutside);
  }
});
</script>

