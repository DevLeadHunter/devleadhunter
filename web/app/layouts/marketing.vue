<template>
  <div class="landing-theme font-body flex min-h-screen flex-col antialiased">
    <!-- Paper grain overlay -->
    <div class="landing-grain" aria-hidden="true"></div>

    <!-- Header -->
    <header
      class="sticky top-0 z-50 border-b transition-colors duration-300"
      :class="hasScrolled ? 'border-[#e3dccd] bg-[#f6f3ec]/90 backdrop-blur-md' : 'border-transparent bg-transparent'"
    >
      <nav class="mx-auto flex h-20 max-w-6xl items-center justify-between px-5 md:px-8">
        <!-- Logo -->
        <NuxtLink :to="localePath('index')" class="group flex items-center gap-2.5">
          <svg
            class="h-5 w-5 fill-current text-[#1b1813] transition-colors group-hover:text-[#6b6355]"
            viewBox="0 0 493 515"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
              fill="currentColor"
            />
          </svg>
          <span class="font-display text-lg font-semibold tracking-tight text-[#1b1813]">devleadhunter</span>
        </NuxtLink>

        <!-- Desktop navigation -->
        <div class="hidden items-center gap-8 lg:flex">
          <a
            v-for="link in sectionLinks"
            :key="link.target"
            :href="link.target"
            class="text-sm font-medium text-[#6b6355] transition-colors hover:text-[#1b1813]"
            @click.prevent="onNavClick(link.target)"
          >
            {{ $t(link.label) }}
          </a>
          <NuxtLink
            :to="localePath('/downloads')"
            class="text-sm font-medium text-[#6b6355] transition-colors hover:text-[#1b1813]"
            @click="track('site_download_click', { location: 'nav' })"
          >
            {{ $t('nav.downloads') }}
          </NuxtLink>
          <NuxtLink
            :to="localePath('/signup')"
            class="landing-btn-primary px-5 py-2.5 text-sm"
            @click="track('site_cta_click', { location: 'header', label: 'signup' })"
          >
            {{ $t('nav.signup') }}
          </NuxtLink>
        </div>

        <!-- Mobile menu button -->
        <button
          class="flex h-10 w-10 items-center justify-center text-[#1b1813] lg:hidden"
          :aria-label="isMobileMenuOpen ? 'Close menu' : 'Open menu'"
          :aria-expanded="isMobileMenuOpen"
          @click="toggleMobileMenu"
        >
          <i :class="isMobileMenuOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars'" class="text-lg"></i>
        </button>
      </nav>
    </header>

    <!-- Mobile full-screen menu -->
    <Transition name="menu-fade">
      <div v-if="isMobileMenuOpen" class="fixed inset-0 z-[60] flex flex-col bg-[#f6f3ec] lg:hidden">
        <div class="flex h-20 items-center justify-between border-b border-[#e3dccd] px-5">
          <span class="font-display text-lg font-semibold tracking-tight text-[#1b1813]">devleadhunter</span>
          <button
            class="flex h-10 w-10 items-center justify-center text-[#1b1813]"
            aria-label="Close menu"
            @click="closeMobileMenu"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        <nav class="flex flex-1 flex-col justify-center gap-2 px-8">
          <a
            v-for="(link, index) in sectionLinks"
            :key="link.target"
            :href="link.target"
            class="menu-item font-display text-4xl font-semibold text-[#1b1813] transition-colors hover:text-[#6b6355]"
            :style="{ transitionDelay: `${index * 40}ms` }"
            @click.prevent="handleMobileSection(link.target)"
          >
            {{ $t(link.label) }}
          </a>
          <NuxtLink
            :to="localePath('/downloads')"
            class="menu-item font-display text-4xl font-semibold text-[#1b1813] transition-colors hover:text-[#6b6355]"
            :style="{ transitionDelay: `${sectionLinks.length * 40}ms` }"
            @click="onMobileDownload"
          >
            {{ $t('nav.downloads') }}
          </NuxtLink>
        </nav>
        <div class="border-t border-[#e3dccd] p-6">
          <NuxtLink :to="localePath('/signup')" class="landing-btn-primary w-full text-center" @click="onMobileSignup">
            {{ $t('nav.signup') }}
          </NuxtLink>
        </div>
      </div>
    </Transition>

    <!-- Main content -->
    <main class="flex-1">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="border-t border-[#e3dccd]">
      <div class="mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-20">
        <div class="grid grid-cols-2 gap-x-8 gap-y-12 md:grid-cols-5 md:gap-12">
          <!-- Brand -->
          <div class="col-span-2 md:col-span-2">
            <div class="mb-5 flex items-center gap-2.5">
              <svg
                class="h-5 w-5 fill-current text-[#1b1813]"
                viewBox="0 0 493 515"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                <path
                  d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
                  fill="currentColor"
                />
              </svg>
              <span class="font-display text-lg font-semibold tracking-tight text-[#1b1813]">devleadhunter</span>
            </div>
            <p class="max-w-sm text-sm leading-relaxed text-[#6b6355]">
              {{ $t('footer.description') }}
            </p>
          </div>

          <!-- Product links -->
          <div>
            <h3 class="landing-eyebrow mb-5 !text-[0.65rem]">{{ $t('footer.product') }}</h3>
            <ul class="space-y-3">
              <li v-for="link in footerProductLinks" :key="link.target">
                <a
                  :href="link.target"
                  class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]"
                  @click.prevent="onNavClick(link.target)"
                >
                  {{ $t(link.label) }}
                </a>
              </li>
            </ul>
          </div>

          <!-- Resources links -->
          <div>
            <h3 class="landing-eyebrow mb-5 !text-[0.65rem]">{{ $t('footer.resources') }}</h3>
            <ul class="space-y-3">
              <li>
                <a
                  href="#faq"
                  class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]"
                  @click.prevent="onNavClick('#faq')"
                >
                  {{ $t('footer.links.faq') }}
                </a>
              </li>
              <li>
                <NuxtLink
                  :to="localePath('/downloads')"
                  class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]"
                  @click="track('site_download_click', { location: 'footer' })"
                >
                  {{ $t('footer.links.downloads') }}
                </NuxtLink>
              </li>
            </ul>
          </div>

          <!-- Account links -->
          <div>
            <h3 class="landing-eyebrow mb-5 !text-[0.65rem]">{{ $t('footer.account') }}</h3>
            <ul class="space-y-3">
              <li>
                <NuxtLink
                  :to="localePath('/login')"
                  class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]"
                  @click="track('site_cta_click', { location: 'footer', label: 'login' })"
                >
                  {{ $t('footer.links.login') }}
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  :to="localePath('/signup')"
                  class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]"
                  @click="track('site_cta_click', { location: 'footer', label: 'signup' })"
                >
                  {{ $t('footer.links.signup') }}
                </NuxtLink>
              </li>
            </ul>
          </div>
        </div>

        <div
          class="mt-14 flex flex-col items-start justify-between gap-6 border-t border-[#e3dccd] pt-8 md:flex-row md:items-center"
        >
          <p class="font-label text-xs text-[#6b6355]">
            © {{ currentYear }} devleadhunter · dibodev — {{ $t('footer.copyright') }}
          </p>
          <div class="flex flex-wrap items-center gap-6">
            <label class="font-label flex items-center gap-2 text-xs text-[#6b6355]">
              {{ $t('footer.language') }}
              <select
                :value="currentLocale"
                class="font-label cursor-pointer rounded-lg border border-[#e3dccd] bg-[#fcfaf5] px-2.5 py-1.5 text-xs text-[#1b1813] transition-colors focus:border-[#1b1813] focus:outline-none"
                @change="switchLocale(($event.target as HTMLSelectElement).value)"
              >
                <option v-for="langOption in availableLocales" :key="langOption.code" :value="langOption.code">
                  {{ langOption.code.toUpperCase() }}
                </option>
              </select>
            </label>
            <NuxtLink
              :to="localePath('/privacy')"
              class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]"
            >
              {{ $t('footer.privacy') }}
            </NuxtLink>
            <NuxtLink :to="localePath('/terms')" class="text-sm text-[#6b6355] transition-colors hover:text-[#1b1813]">
              {{ $t('footer.terms') }}
            </NuxtLink>
          </div>
        </div>
      </div>
    </footer>

    <!-- GDPR cookie consent (marketing surface only) -->
    <LandingCookieConsent />
  </div>
</template>

<script lang="ts" setup>
import type { Ref, ComputedRef } from 'vue'
import type { LocaleObject } from '@nuxtjs/i18n'
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const { locale, locales, setLocale } = useI18n()
const localePath = useLocalePath()
const { track } = useSiteTracking()

// i18n SEO for every marketing page: canonical, hreflang alternates, and the correct
// <html lang> per locale (without this, /fr pages inherit the default lang="en").
const localeHead = useLocaleHead()
useHead(() => ({
  htmlAttrs: localeHead.value.htmlAttrs,
  link: localeHead.value.link,
  meta: localeHead.value.meta,
}))

/** A navigation link that scrolls to an on-page landing section. */
interface LandingSectionLink {
  /** Anchor target (e.g. `#how-it-works`). */
  target: string
  /** i18n key for the link label. */
  label: string
}

/** Section links shown in the desktop header and mobile menu. */
const sectionLinks: LandingSectionLink[] = [
  { target: '#how-it-works', label: 'nav.howItWorks' },
  { target: '#delivered-site', label: 'nav.product' },
  { target: '#pricing', label: 'nav.pricing' },
  { target: '#faq', label: 'nav.faq' },
]

/** Section links shown in the footer "Product" column. */
const footerProductLinks: LandingSectionLink[] = [
  { target: '#how-it-works', label: 'footer.links.howItWorks' },
  { target: '#delivered-site', label: 'footer.links.product' },
  { target: '#pricing', label: 'footer.links.pricing' },
]

/** Whether the mobile full-screen menu is open. */
const isMobileMenuOpen: Ref<boolean> = ref<boolean>(false)

/** Whether the page is scrolled past the top (drives the header backdrop). */
const hasScrolled: Ref<boolean> = ref<boolean>(false)

/** Current year for the copyright line. */
const currentYear: ComputedRef<number> = computed((): number => new Date().getFullYear())

/** Locales available in the language switcher. */
const availableLocales: ComputedRef<LocaleObject[]> = computed((): LocaleObject[] => locales.value)

/** Currently active locale code. */
const currentLocale: ComputedRef<string> = computed((): string => locale.value)

/**
 * Switch the active locale.
 * @param code - Locale code selected in the language switcher.
 */
function switchLocale(code: string): void {
  setLocale(code as 'en' | 'fr')
}

/**
 * Toggle the mobile full-screen menu.
 */
function toggleMobileMenu(): void {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

/**
 * Close the mobile full-screen menu.
 */
function closeMobileMenu(): void {
  isMobileMenuOpen.value = false
}

/**
 * Track a section nav click, then smooth-scroll to it.
 * @param selector - CSS selector of the target section.
 */
function onNavClick(selector: string): void {
  track('site_nav_click', { target: selector })
  scrollToSection(selector)
}

/**
 * Scroll to a section then close the mobile menu (tracked).
 * @param selector - CSS selector of the target section.
 */
function handleMobileSection(selector: string): void {
  track('site_nav_click', { target: selector })
  closeMobileMenu()
  scrollToSection(selector)
}

/**
 * Track the mobile-menu download link, then close the menu.
 */
function onMobileDownload(): void {
  track('site_download_click', { location: 'mobile_menu' })
  closeMobileMenu()
}

/**
 * Track the mobile-menu signup CTA, then close the menu.
 */
function onMobileSignup(): void {
  track('site_cta_click', { location: 'mobile_menu', label: 'signup' })
  closeMobileMenu()
}

/**
 * Smooth-scroll to a landing section, accounting for the sticky header height.
 * @param selector - CSS selector of the target section.
 */
function scrollToSection(selector: string): void {
  const element: Element | null = document.querySelector(selector)
  if (element) {
    const headerOffset: number = 80
    const elementPosition: number = element.getBoundingClientRect().top
    const offsetPosition: number = elementPosition + window.pageYOffset - headerOffset
    window.scrollTo({ top: offsetPosition, behavior: 'smooth' })
  }
}

/**
 * Track scroll position to reveal the header backdrop once the page moves.
 */
function handleScroll(): void {
  hasScrolled.value = window.scrollY > 8
}

onMounted((): void => {
  handleScroll()
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onBeforeUnmount((): void => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
/* Mobile menu fade + staggered items */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.25s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
}

.menu-fade-enter-active .menu-item {
  transition:
    opacity 0.4s ease,
    transform 0.4s ease;
}

.menu-fade-enter-from .menu-item {
  opacity: 0;
  transform: translateY(12px);
}
</style>
