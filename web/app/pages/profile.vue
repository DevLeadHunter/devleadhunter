<template>
  <div class="max-w-2xl">
    <UiPageHeader eyebrow="Compte" title="Profil" class="mb-6" />

    <div class="card">
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label for="name" class="text-muted mb-1.5 block text-xs font-medium"> Nom </label>
          <input id="name" v-model="name" type="text" required class="input-field" placeholder="Jean Dupont" />
        </div>

        <div>
          <label for="email" class="text-muted mb-1.5 block text-xs font-medium"> Email </label>
          <input id="email" v-model="email" type="email" required class="input-field" placeholder="jean@exemple.fr" />
        </div>

        <div class="grid grid-cols-2 gap-3 pt-2 sm:flex sm:justify-end">
          <NuxtLink to="/dashboard" class="btn-secondary h-11 sm:h-9">
            <span> Annuler </span>
          </NuxtLink>
          <button type="submit" :disabled="isLoading" class="btn-primary h-11 sm:h-9">
            <span v-if="isLoading">Enregistrement…</span>
            <span v-else>Enregistrer</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
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
const userStore: ReturnType<typeof useUserStore> = useUserStore()

/**
 * Toast composable
 */
const toast: UseToastReturn = useToast()

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
const handleSubmit: () => Promise<void> = async (): Promise<void> => {
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
