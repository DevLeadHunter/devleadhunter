<template>
  <div
    class="pointer-events-none fixed inset-x-0 top-[env(safe-area-inset-top)] z-[120] flex justify-center"
    :class="{ 'transition-transform duration-200 ease-out': !isPulling }"
    :style="{ transform: `translateY(${pullDistance - INDICATOR_HIDDEN_OFFSET_PX}px)` }"
    aria-hidden="true"
  >
    <span
      class="mt-2 flex size-10 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] shadow-[var(--app-shadow-soft)]"
      :style="{ opacity: pullProgress }"
    >
      <UIcon
        :name="isRefreshing ? 'i-lucide-loader-circle' : 'i-lucide-arrow-down'"
        class="size-5 text-[var(--app-ink)] transition-transform duration-200"
        :class="{ 'animate-spin': isRefreshing, 'rotate-180': hasReachedRefreshThreshold && !isRefreshing }"
      />
    </span>
  </div>
</template>

<script lang="ts" setup>
import type { UsePullToRefreshReturn } from '~/types/Composables'
import { usePullToRefresh } from '~/composables/usePullToRefresh'
import { useDrawerStackStore } from '~/stores/drawerStack'

const INDICATOR_HIDDEN_OFFSET_PX: number = 48

const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const { pullDistance, pullProgress, isPulling, isRefreshing, hasReachedRefreshThreshold }: UsePullToRefreshReturn =
  usePullToRefresh({
    onRefresh: (): void => {
      reloadNuxtApp({ force: true })
    },
    // A drawer covers the page and scrolls on its own: pulling it down must not reload behind it.
    canStart: (): boolean => drawerStack.topEntry === null,
  })
</script>
