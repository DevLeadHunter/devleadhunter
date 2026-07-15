<template>
  <div>
    <div v-if="isLoading || isNavigating" class="landing-loader-vars">
      <UiLoader />
    </div>
    <AuthShell v-else mode="login">
      <LandingAsterisk class="auth-rise text-2xl text-[#e8a33c]" :style="{ animationDelay: '0ms' }" />
      <h1
        class="auth-rise font-display mt-5 text-4xl font-semibold tracking-[-0.02em]"
        :style="{ animationDelay: '70ms' }"
      >
        {{ $t('auth.login.title') }}
      </h1>
      <p class="auth-rise mt-2.5 text-sm leading-relaxed text-[#6b6355]" :style="{ animationDelay: '140ms' }">
        {{ $t('auth.login.subtitle') }}
      </p>

      <form class="mt-10 space-y-5" @submit.prevent="handleSubmit">
        <!-- General Error -->
        <div
          v-if="generalError"
          class="rounded-xl border border-[#e0b6a9] bg-[#f9ece7] px-3 py-2 text-sm text-[#8f3a25]"
        >
          {{ generalError }}
        </div>

        <!-- Email -->
        <div class="auth-rise" :style="{ animationDelay: '210ms' }">
          <label for="email" class="font-label mb-2 block text-xs tracking-[0.08em] text-[#6b6355] uppercase">
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
          <p v-if="emailError" class="mt-1.5 text-xs text-[#8f3a25]">{{ emailError }}</p>
        </div>

        <!-- Password -->
        <div class="auth-rise" :style="{ animationDelay: '280ms' }">
          <label for="password" class="font-label mb-2 block text-xs tracking-[0.08em] text-[#6b6355] uppercase">
            {{ $t('auth.fields.password') }}
          </label>
          <UiPasswordInput
            id="password"
            v-model="password"
            required
            appearance="landing"
            :placeholder="$t('auth.login.passwordPlaceholder')"
            :has-error="Boolean(passwordError)"
          />
          <p v-if="passwordError" class="mt-1.5 text-xs text-[#8f3a25]">{{ passwordError }}</p>
        </div>

        <!-- Submit Button -->
        <div class="auth-rise pt-2" :style="{ animationDelay: '350ms' }">
          <button type="submit" :disabled="isLoading" class="landing-btn-primary w-full">
            <span v-if="isLoading">{{ $t('auth.login.submitting') }}</span>
            <span v-else>{{ $t('auth.login.submit') }}</span>
          </button>
        </div>

        <!-- Sign Up Link -->
        <p class="auth-rise text-center text-sm text-[#6b6355]" :style="{ animationDelay: '420ms' }">
          {{ $t('auth.login.switchQuestion') }}
          <NuxtLink :to="localePath('/signup')" class="landing-link">{{ $t('auth.login.switchCta') }}</NuxtLink>
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
 * Login page
 */
definePageMeta({
  layout: false,
  sitemap: false,
})

// Auth utility page — keep it out of the index (no SEO value, avoids thin-content pages).
useSeoMeta({
  title: 'Connexion — DevLeadHunter',
  robots: 'noindex, nofollow',
})

/**
 * Auth composable
 */
const { login, isLoading, isAuthenticated } = useAuth()

/**
 * Marketing-site tracking (records the login conversion).
 */
const { track } = useSiteTracking()

/**
 * i18n — script-side error messages + locale-aware links.
 */
const { t } = useI18n()
const localePath = useLocalePath()

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
    emailError.value = t('auth.login.errorEmailRequired')
    return
  }

  if (!validateEmail(email.value)) {
    emailError.value = t('auth.errors.emailFormat')
    return
  }

  // Validate password
  if (!password.value) {
    passwordError.value = t('auth.login.errorPasswordRequired')
    return
  }

  // Try to login
  try {
    await login({
      email: email.value,
      password: password.value,
    })
    track('site_login_completed')
    // Keep loader visible during navigation
    isNavigating.value = true
  } catch {
    // Set general error message
    generalError.value = t('auth.login.errorGeneral')
  }
}
</script>
