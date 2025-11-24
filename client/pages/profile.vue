<template>
  <div class="max-w-2xl">
    <h1 class="text-xl font-semibold text-[#f9f9f9] mb-4">Profile</h1>

    <div class="card">
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Name -->
        <div>
          <label for="name" class="block text-xs font-medium text-muted mb-1.5">
            Name
          </label>
          <input
            id="name"
            v-model="name"
            type="text"
            required
            class="input-field"
          />
        </div>

        <!-- Email -->
        <div>
          <label for="email" class="block text-xs font-medium text-muted mb-1.5">
            Email
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            class="input-field"
          />
        </div>

        <!-- Save Button -->
        <div class="flex gap-3 pt-2 justify-end">
          <NuxtLink
            to="/dashboard"
            class="btn-secondary"
          >
            <span>
              Cancel
            </span>
          </NuxtLink>
          <button
            type="submit"
            :disabled="isLoading"
            class="btn-primary"
          >
            <span v-if="isLoading">Saving...</span>
            <span v-else>Save Changes</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { ref, computed, onMounted } from 'vue';
import { useUserStore } from '~/stores/user';
import { useToast } from '~/composables/useToast';

/**
 * Profile page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

/**
 * User store
 */
const userStore = useUserStore();

/**
 * Toast composable
 */
const toast = useToast();

/**
 * Form state
 */
const name: Ref<string> = ref('');
const email: Ref<string> = ref('');

/**
 * Loading state
 */
const isLoading: Ref<boolean> = computed(() => userStore.isLoading);

/**
 * Initialize form with user data
 */
onMounted(() => {
  if (userStore.user) {
    name.value = userStore.user.name;
    email.value = userStore.user.email;
  }
});

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  try {
    await userStore.updateProfile({
      name: name.value,
      email: email.value
    });
    
    toast.success('Profile updated successfully');
  } catch (error) {
    toast.error('Failed to update profile');
  }
};
</script>
