<template>
  <div>
    <div v-if="isLoading || isNavigating" class="landing-loader-vars">
      <UiLoader />
    </div>
    <AuthShell v-else mode="signup">
      <LandingAsterisk class="text-2xl text-[#e8a33c]" />
      <h1 class="font-display mt-4 text-3xl font-semibold tracking-[-0.015em]">{{ $t('auth.signup.title') }}</h1>
      <p class="mt-2 text-sm leading-relaxed text-[#6b6355]">{{ $t('auth.signup.subtitle') }}</p>

      <form class="landing-card mt-8 space-y-4 p-6" @submit.prevent="handleSubmit">
        <!-- General Error -->
        <div
          v-if="generalError"
          class="rounded-xl border border-[#e0b6a9] bg-[#f9ece7] px-3 py-2 text-sm text-[#8f3a25]"
        >
          {{ generalError }}
        </div>

        <!-- Name -->
        <div>
          <label for="name" class="font-label mb-1.5 block text-xs tracking-[0.08em] text-[#6b6355] uppercase">
            {{ $t('auth.fields.name') }}
          </label>
          <input
            id="name"
            v-model="name"
            type="text"
            required
            :placeholder="$t('auth.fields.namePlaceholder')"
            :class="['landing-input', nameError && 'landing-input--error']"
          />
          <p v-if="nameError" class="mt-1 text-xs text-[#8f3a25]">{{ nameError }}</p>
        </div>

        <!-- Email -->
        <div>
          <label for="email" class="font-label mb-1.5 block text-xs tracking-[0.08em] text-[#6b6355] uppercase">
            {{ $t('auth.fields.email') }}
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            :placeholder="$t('auth.fields.emailPlaceholder')"
            :class="['landing-input', emailError && 'landing-input--error']"
          />
          <p v-if="emailError" class="mt-1 text-xs text-[#8f3a25]">{{ emailError }}</p>
        </div>

        <!-- Password -->
        <div>
          <label for="password" class="font-label mb-1.5 block text-xs tracking-[0.08em] text-[#6b6355] uppercase">
            {{ $t('auth.fields.password') }}
          </label>
          <UiPasswordInput
            id="password"
            v-model="password"
            required
            appearance="landing"
            :placeholder="$t('auth.signup.passwordPlaceholder')"
            :has-error="Boolean(passwordError)"
          />
          <p v-if="passwordError" class="mt-1 text-xs text-[#8f3a25]">{{ passwordError }}</p>
        </div>

        <!-- Submit Button -->
        <button type="submit" :disabled="isLoading" class="landing-btn-primary w-full">
          <span v-if="isLoading">{{ $t('auth.signup.submitting') }}</span>
          <span v-else>{{ $t('auth.signup.submit') }}</span>
        </button>

        <!-- Login Link -->
        <p class="text-center text-sm text-[#6b6355]">
          {{ $t('auth.signup.switchQuestion') }}
          <NuxtLink :to="localePath('/login')" class="landing-link">{{ $t('auth.signup.switchCta') }}</NuxtLink>
        </p>
      </form>
    </AuthShell>
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
 * Signup page
 */
definePageMeta({
  layout: false,
  sitemap: false,
})

// Auth utility page — keep it out of the index (no SEO value, avoids thin-content pages).
useSeoMeta({
  title: 'Créer un compte — DevLeadHunter',
  robots: 'noindex, nofollow',
})

/**
 * Auth composable
 */
const { signup, isLoading, isAuthenticated } = useAuth()

/**
 * Marketing-site tracking (records the signup conversion).
 */
const { track } = useSiteTracking()

/**
 * i18n — script-side error messages + locale-aware links.
 */
const { t } = useI18n()
const localePath = useLocalePath()

/**
 * User store
 */
const userStore = useUserStore()

/**
 * Router for navigation
 */
const router = useRouter()

/**
 * Form state
 */
const name: Ref<string> = ref('')
const email: Ref<string> = ref('')
const password: Ref<string> = ref('')

/**
 * Navigation state - keeps loader visible during redirect
 */
const isNavigating: Ref<boolean> = ref(false)

/**
 * Error state
 */
const nameError: Ref<string> = ref('')
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
      // Token was invalid, stay on signup page
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
  nameError.value = ''
  emailError.value = ''
  passwordError.value = ''
  generalError.value = ''

  // Validate name
  if (!name.value) {
    nameError.value = t('auth.signup.errorNameRequired')
    return
  }

  // Validate email
  if (!email.value) {
    emailError.value = t('auth.signup.errorEmailRequired')
    return
  }

  if (!validateEmail(email.value)) {
    emailError.value = t('auth.errors.emailFormat')
    return
  }

  // Validate password
  if (!password.value) {
    passwordError.value = t('auth.signup.errorPasswordRequired')
    return
  }

  if (password.value.length < 6) {
    passwordError.value = t('auth.signup.errorPasswordLength')
    return
  }

  // Try to signup
  try {
    await signup({
      name: name.value,
      email: email.value,
      password: password.value,
    })
    track('site_signup_completed')
    // Keep loader visible during navigation
    isNavigating.value = true
  } catch (error) {
    // Set general error message
    const errorMessage = error instanceof Error ? error.message : t('auth.signup.errorGeneral')
    generalError.value = errorMessage
  }
}
</script>
