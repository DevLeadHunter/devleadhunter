<template>
  <div class="min-h-screen bg-[#050505] text-[#f9f9f9]">
    <!-- Header -->
    <header class="sticky top-0 z-50 border-b border-[#30363d]/30 bg-[#050505]/95 backdrop-blur-lg">
      <nav class="container mx-auto px-4 md:px-6 lg:px-8">
        <div class="flex h-20 items-center justify-between">
          <!-- Logo -->
          <NuxtLink :to="localePath('/')" class="group flex items-center gap-2.5">
            <div class="flex h-5 w-5 items-center justify-center">
              <svg
                class="h-full w-full fill-current text-[#f9f9f9] transition-colors group-hover:text-[#e4e4e4]"
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
            <span class="text-base font-semibold text-[#f9f9f9] transition-colors group-hover:text-[#e4e4e4]">
              devleadhunter
            </span>
          </NuxtLink>

          <!-- Desktop Navigation -->
          <div class="hidden items-center gap-8 md:flex">
            <a
              href="#features"
              class="text-base font-medium text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
              @click.prevent="scrollToSection('#features')"
            >
              {{ $t('nav.features') }}
            </a>
            <a
              href="#pricing"
              class="text-base font-medium text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
              @click.prevent="scrollToSection('#pricing')"
            >
              {{ $t('nav.pricing') }}
            </a>
            <NuxtLink
              :to="localePath('/login')"
              class="text-base font-medium text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
            >
              {{ $t('nav.login') }}
            </NuxtLink>
            <NuxtLink :to="localePath('/signup')" class="btn-primary px-4 py-2 text-sm">
              {{ $t('nav.signup') }}
            </NuxtLink>
          </div>

          <!-- Mobile Menu Button -->
          <button class="p-2 text-[#8b949e] transition-colors hover:text-[#f9f9f9] md:hidden" @click="toggleMobileMenu">
            <i :class="isMobileMenuOpen ? 'fa-solid fa-times' : 'fa-solid fa-bars'" class="h-5 w-5"></i>
          </button>
        </div>
      </nav>
    </header>

    <!-- Mobile Sidebar Menu (slides from left) -->
    <Transition name="slide">
      <div v-if="isMobileMenuOpen" class="fixed inset-0 z-[60] md:hidden">
        <!-- Overlay -->
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="closeMobileMenu"></div>

        <!-- Sidebar -->
        <aside class="fixed left-0 top-0 z-[60] h-full w-full border-r border-[#30363d] bg-[#1a1a1a] shadow-xl">
          <div class="flex h-full flex-col">
            <!-- Header -->
            <div class="border-b border-[#30363d] px-4 py-5">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <div class="flex h-5 w-5 items-center justify-center">
                    <svg
                      class="h-full w-full fill-current text-[#f9f9f9]"
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
                  <span class="text-base font-semibold text-[#f9f9f9]">devleadhunter</span>
                </div>
                <button class="p-2 text-[#8b949e] transition-colors hover:text-[#f9f9f9]" @click="closeMobileMenu">
                  <i class="fa-solid fa-times h-5 w-5"></i>
                </button>
              </div>
            </div>

            <!-- Navigation Links -->
            <nav class="flex-1 space-y-1 overflow-y-auto px-2 py-4">
              <a
                href="#features"
                class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[#8b949e] transition-colors hover:bg-[#21262d] hover:text-[#f9f9f9]"
                @click.prevent="handleMobileSection('#features')"
              >
                <i class="fa-solid fa-star h-4 w-4"></i>
                <span>{{ $t('nav.features') }}</span>
              </a>
              <a
                href="#pricing"
                class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[#8b949e] transition-colors hover:bg-[#21262d] hover:text-[#f9f9f9]"
                @click.prevent="handleMobileSection('#pricing')"
              >
                <i class="fa-solid fa-tag h-4 w-4"></i>
                <span>{{ $t('nav.pricing') }}</span>
              </a>
              <NuxtLink
                :to="localePath('/login')"
                class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[#8b949e] transition-colors hover:bg-[#21262d] hover:text-[#f9f9f9]"
                @click="closeMobileMenu"
              >
                <i class="fa-solid fa-right-to-bracket h-4 w-4"></i>
                <span>{{ $t('nav.login') }}</span>
              </NuxtLink>
            </nav>

            <!-- CTA Button -->
            <div class="border-t border-[#30363d] p-4">
              <NuxtLink
                :to="localePath('/signup')"
                class="btn-primary w-full text-center text-sm"
                @click="closeMobileMenu"
              >
                {{ $t('nav.signup') }}
              </NuxtLink>
            </div>
          </div>
        </aside>
      </div>
    </Transition>

    <!-- Main Content -->
    <main>
      <slot />
    </main>

    <!-- Footer -->
    <footer class="mt-32 border-t border-[#30363d]/30 bg-[#1a1a1a]">
      <div class="container mx-auto px-4 py-20 md:px-6 lg:px-8">
        <div class="grid grid-cols-1 gap-16 md:grid-cols-4">
          <!-- Brand -->
          <div class="col-span-1 md:col-span-2">
            <div class="mb-4 flex items-center gap-2.5">
              <div class="flex h-5 w-5 items-center justify-center">
                <svg
                  class="h-full w-full fill-current text-[#f9f9f9]"
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
              <span class="text-base font-semibold text-[#f9f9f9]">devleadhunter</span>
            </div>
            <p class="max-w-md text-base font-light leading-relaxed text-[#8b949e]">
              {{ $t('footer.description') }}
            </p>
          </div>

          <!-- Links -->
          <div>
            <h3 class="mb-6 text-sm font-semibold uppercase tracking-wider text-[#f9f9f9]">
              {{ $t('footer.product') }}
            </h3>
            <ul class="space-y-4">
              <li>
                <a
                  href="#features"
                  class="text-base font-light text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
                  @click.prevent="scrollToSection('#features')"
                >
                  {{ $t('nav.features') }}
                </a>
              </li>
              <li>
                <a
                  href="#pricing"
                  class="text-base font-light text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
                  @click.prevent="scrollToSection('#pricing')"
                >
                  {{ $t('nav.pricing') }}
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 class="mb-6 text-sm font-semibold uppercase tracking-wider text-[#f9f9f9]">
              {{ $t('footer.account') }}
            </h3>
            <ul class="space-y-4">
              <li>
                <NuxtLink
                  :to="localePath('/login')"
                  class="text-base font-light text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
                >
                  {{ $t('nav.login') }}
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  :to="localePath('/signup')"
                  class="text-base font-light text-[#8b949e] transition-colors hover:text-[#f9f9f9]"
                >
                  {{ $t('nav.signup') }}
                </NuxtLink>
              </li>
            </ul>
          </div>
        </div>

        <div class="mt-16 border-t border-[#30363d]/30 pt-10">
          <div class="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
            <p class="text-base font-light text-[#8b949e]">
              © {{ currentYear }} devleadhunter. {{ $t('footer.copyright') }}
            </p>
            <div class="flex w-full flex-col items-start gap-4 md:w-auto md:flex-row md:items-center md:gap-6">
              <div class="flex w-full items-center justify-start gap-2 md:w-auto">
                <span class="mr-2 text-sm text-[#8b949e]">Language:</span>
                <select
                  :value="currentLocale"
                  class="rounded-lg border border-[#30363d] bg-[#1a1a1a] px-3 py-1.5 text-sm text-[#f9f9f9] transition-colors focus:border-[#f9f9f9] focus:outline-none"
                  @change="switchLocale(($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="langOption in availableLocales" :key="langOption.code" :value="langOption.code">
                    {{ langOption.code.toUpperCase() }}
                  </option>
                </select>
              </div>
              <div class="flex w-full flex-col items-start gap-4 md:w-auto md:flex-row md:items-center md:gap-8">
                <a href="#" class="text-base font-light text-[#8b949e] transition-colors hover:text-[#f9f9f9]">
                  {{ $t('footer.privacy') }}
                </a>
                <a href="#" class="text-base font-light text-[#8b949e] transition-colors hover:text-[#f9f9f9]">
                  {{ $t('footer.terms') }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref, computed } from 'vue'

const { locale, locales, setLocale } = useI18n()
const localePath = useLocalePath()

/**
 * Mobile menu state
 */
const isMobileMenuOpen: Ref<boolean> = ref(false)

/**
 * Current year for copyright
 */
const currentYear = computed(() => new Date().getFullYear())

/**
 * Available locales
 */
const availableLocales = computed(() => locales.value)

/**
 * Current locale
 */
const currentLocale = computed(() => locale.value)

/**
 * Switch locale
 */
const switchLocale = (code: string): void => {
  setLocale(code)
}

/**
 * Toggle mobile menu
 */
const toggleMobileMenu = (): void => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

/**
 * Close mobile menu
 */
const closeMobileMenu = (): void => {
  isMobileMenuOpen.value = false
}

/**
 * Scroll to a section and close the mobile menu.
 */
const handleMobileSection = (selector: string): void => {
  scrollToSection(selector)
  closeMobileMenu()
}

/**
 * Smooth scroll to section
 */
const scrollToSection = (selector: string): void => {
  const element = document.querySelector(selector)
  if (element) {
    const headerOffset = 80
    const elementPosition = element.getBoundingClientRect().top
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth',
    })
  }
}
</script>
