<template>
  <div class="max-w-2xl">
    <h1 class="mb-4 text-xl font-semibold text-[var(--app-ink)]">Profil</h1>

    <div class="card">
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <!-- Name -->
        <div>
          <label for="name" class="text-muted mb-1.5 block text-xs font-medium"> Nom </label>
          <input id="name" v-model="name" type="text" required class="input-field" />
        </div>

        <!-- Email -->
        <div>
          <label for="email" class="text-muted mb-1.5 block text-xs font-medium"> Email </label>
          <input id="email" v-model="email" type="email" required class="input-field" />
        </div>

        <!-- Save Button -->
        <div class="flex justify-end gap-3 pt-2">
          <NuxtLink to="/dashboard" class="btn-secondary">
            <span> Annuler </span>
          </NuxtLink>
          <button type="submit" :disabled="isLoading" class="btn-primary">
            <span v-if="isLoading">Enregistrement…</span>
            <span v-else>Enregistrer</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'

/**
 * Profile page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

/**
 * User store
 */
const userStore = useUserStore()

/**
 * Toast composable
 */
const toast = useToast()

/**
 * Form state
 */
const name: Ref<string> = ref('')
const email: Ref<string> = ref('')

/**
 * Loading state
 */
const isLoading: Ref<boolean> = computed(() => userStore.isLoading)

/**
 * Initialize form with user data
 */
onMounted(() => {
  if (userStore.user) {
    name.value = userStore.user.name
    email.value = userStore.user.email
  }
})

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  try {
    await userStore.updateProfile({
      name: name.value,
      email: email.value,
    })

    toast.success('Profil mis à jour')
  } catch {
    toast.error('Erreur lors de la mise à jour du profil')
  }
}
</script>
