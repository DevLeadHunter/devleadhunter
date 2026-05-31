<template>
  <div>
    <UiLoader v-if="isLoading || isNavigating" />
    <div v-else class="relative flex min-h-screen items-center justify-center bg-[#050505] px-4">
      <!-- Logo en haut à gauche -->
      <div class="absolute top-6 left-6 flex items-center gap-2">
        <div class="flex h-5 w-5 items-center justify-center rounded">
          <svg
            class="h-full w-full fill-current text-white"
            viewBox="0 0 493 515"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
              fill="currentColor"
            />
          </svg>
        </div>
        <h1 class="text-base font-semibold text-[#f9f9f9]">Devleadhunter</h1>
      </div>

      <div class="w-full max-w-sm">
        <!-- Welcome Section -->
        <div class="mb-8 text-left">
          <h2 class="mb-2 text-2xl font-semibold text-[#f9f9f9]">Welcome to Devleadhunter</h2>
          <p class="text-sm text-[#8b949e]">The smarter way to find prospects</p>
        </div>

        <form class="space-y-4" @submit.prevent="handleSubmit">
          <!-- General Error -->
          <div v-if="generalError" class="text-sm text-[#DC4747]">
            {{ generalError }}
          </div>

          <!-- Email -->
          <div>
            <label for="email" class="text-muted mb-1.5 block text-xs font-medium"> Email </label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              placeholder="Enter your email address"
              :class="['input-field', emailError && 'border-[#DC4747]']"
            />
            <p v-if="emailError" class="mt-1 text-xs text-[#DC4747]">{{ emailError }}</p>
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="text-muted mb-1.5 block text-xs font-medium"> Password </label>
            <UiPasswordInput
              id="password"
              v-model="password"
              required
              placeholder="Enter your password"
              :has-error="Boolean(passwordError)"
            />
            <p v-if="passwordError" class="mt-1 text-xs text-[#DC4747]">{{ passwordError }}</p>
          </div>

          <!-- Submit Button -->
          <button type="submit" :disabled="isLoading" class="btn-primary w-full">
            <span v-if="isLoading">Logging in...</span>
            <span v-else>Login</span>
          </button>

          <!-- Sign Up Link -->
          <p class="text-muted text-center text-sm">
            Don't have an account?
            <NuxtLink to="/signup" class="text-[#f9f9f9] transition-colors hover:underline"> Sign up </NuxtLink>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref, onMounted } from 'vue'
import UiLoader from '~/components/ui/Loader.vue'
import UiPasswordInput from '~/components/ui/PasswordInput.vue'
import { useAuth } from '~/composables/useAuth'
import { useUserStore } from '~/stores/user'

/**
 * Login page
 */
definePageMeta({
  layout: false,
})

/**
 * Auth composable
 */
const { login, isLoading, isAuthenticated } = useAuth()

/**
 * User store instance
 */
const userStore = useUserStore()

/**
 * Router for navigation
 */
const router = useRouter()

/**
 * Form state
 */
const email: Ref<string> = ref('')
const password: Ref<string> = ref('')

/**
 * Navigation state - keeps loader visible during redirect
 */
const isNavigating: Ref<boolean> = ref(false)

/**
 * Error state
 */
const emailError: Ref<string> = ref('')
const passwordError: Ref<string> = ref('')
const generalError: Ref<string> = ref('')

/**
 * Check if user is already authenticated on mount
 * Redirect to dashboard if already logged in
 * Validate the token first to avoid redirecting with expired tokens
 */
onMounted(async () => {
  if (isAuthenticated.value) {
    isNavigating.value = true
    // Validate token before redirecting to avoid issues with expired tokens
    const isValid = await userStore.validateAuth()
    if (isValid) {
      router.push('/dashboard')
    } else {
      // Token was invalid, stay on login page
      isNavigating.value = false
    }
  }
})

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  // Reset errors
  emailError.value = ''
  passwordError.value = ''
  generalError.value = ''

  // Validate email
  if (!email.value) {
    emailError.value = 'Please enter your email address to access your account.'
    return
  }

  if (!validateEmail(email.value)) {
    emailError.value = 'Invalid email format.'
    return
  }

  // Validate password
  if (!password.value) {
    passwordError.value = 'Please enter your password.'
    return
  }

  // Try to login
  try {
    await login({
      email: email.value,
      password: password.value,
    })
    // Keep loader visible during navigation
    isNavigating.value = true
  } catch {
    // Set general error message
    generalError.value = 'Incorrect login credentials. Please try again.'
  }
}
</script>
