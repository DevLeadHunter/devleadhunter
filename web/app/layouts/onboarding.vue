<template>
  <div class="app-theme min-h-dvh" :data-theme="theme">
    <header class="border-b border-[var(--app-line)] bg-[var(--app-surface)]">
      <div class="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div class="flex items-center gap-2.5">
          <svg
            class="h-4 w-4 fill-current text-[var(--app-ink)]"
            viewBox="0 0 493 515"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M40.6667 1.73334C13.3333 8.80001 2.93333 27.6 8.53333 59.3333C9.73333 65.8667 15.4667 86.6667 21.3333 105.333C33.4667 143.6 41.2 173.733 45.6 199.333C48 213.867 48.5333 221.867 48.5333 248C48.6667 296.8 44.1333 319.067 19.3333 392.667C3.46667 440 0 453.867 0 469.867C0 489.067 6.8 500.933 21.7333 508.133C44.2667 518.8 77.8667 516.133 107.333 501.333C144.533 482.667 158.933 460.133 168.667 404.933C174.8 369.6 179.733 357.6 194 343.2C199.2 337.867 207.6 331.333 212.933 328.133C233.067 316.533 266.267 305.733 291.467 302.667C298 301.867 305.333 301.067 307.733 300.667L312 300.133V335.067C312 385.6 314.667 410.933 322.267 435.2C333.333 470.533 356.267 493.333 393.867 506.533C435.067 521.067 476 515.067 486.533 492.933C493.6 477.867 491.467 464.133 473.867 410.933C459.867 368.8 452.533 341.733 447.867 315.333C445.2 300.533 444.8 293.6 444.8 267.333C444.8 241.6 445.333 234 447.867 220C453.333 189.2 460 164.4 477.6 108C491.867 62.1333 494.533 45.2 490 29.7333C484.267 10.4 465.6 5.71296e-06 437.067 5.71296e-06C405.867 5.71296e-06 378.533 10.8 358.4 31.0667C341.467 47.8667 331.6 71.3333 325.467 108.667C321.2 134.533 317.733 147.467 312.4 158.667C298 188.8 258.533 207.6 192.933 215.467C182.8 216.667 174.267 217.333 173.867 216.933C173.467 216.533 173.867 206.133 174.8 193.867C178.667 139.867 172.133 78 160.133 53.0667C148.8 29.4667 126 12.1333 96.1333 4.40001C80.5333 0.400006 51.4667 -1.06666 40.6667 1.73334Z"
              fill="currentColor"
            />
          </svg>
          <span class="text-sm font-semibold tracking-tight text-[var(--app-ink)]">devleadhunter</span>
        </div>

        <span class="flex items-center gap-1 rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] p-0.5">
          <button type="button" :class="themeButtonClass('light')" aria-label="Thème clair" @click="setTheme('light')">
            <UIcon name="i-lucide-sun" class="h-3.5 w-3.5" />
          </button>
          <button type="button" :class="themeButtonClass('dark')" aria-label="Thème sombre" @click="setTheme('dark')">
            <UIcon name="i-lucide-moon" class="h-3.5 w-3.5" />
          </button>
        </span>
      </div>
    </header>

    <main class="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-12">
      <slot />
    </main>
  </div>
</template>

<script lang="ts" setup>
import type { AppTheme } from '~/types/AppTheme'
import { onMounted } from 'vue'
import { useAppTheme } from '~/composables/useAppTheme'

/**
 * Focused shell for the post-signup setup wizard: the app's theme world without
 * the dashboard chrome, so nothing competes with the steps being configured.
 */

const { theme, initTheme, toggleTheme } = useAppTheme()

/**
 * Classes of a theme-switch segment button.
 * @param value - The theme this button activates.
 * @returns Tailwind classes for the segment.
 */
function themeButtonClass(value: AppTheme): string {
  const base: string = 'flex h-6 w-6 cursor-pointer items-center justify-center rounded-full transition-colors'
  if (theme.value === value) return `${base} bg-[var(--app-ink)] text-[var(--app-surface)]`
  return `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Activate a specific theme (no-op when already active).
 * @param value - Target theme.
 */
function setTheme(value: AppTheme): void {
  if (theme.value !== value) toggleTheme()
}

onMounted((): void => {
  initTheme()
})
</script>
