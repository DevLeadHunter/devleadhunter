<template>
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
    <!-- Logs -->
    <div class="flex flex-col overflow-hidden rounded-lg border border-[#30363d] bg-[#050505]">
      <div class="flex items-center justify-between border-b border-[#30363d] px-4 py-2.5">
        <div class="flex items-center gap-2">
          <span class="relative flex h-2 w-2">
            <span
              v-if="isRunning"
              class="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#2BAD5F] opacity-60"
            ></span>
            <span
              class="relative inline-flex h-2 w-2 rounded-full"
              :class="isRunning ? 'bg-[#2BAD5F]' : 'bg-[#8b949e]'"
            ></span>
          </span>
          <h3 class="text-sm font-medium text-[#f9f9f9]">Journal en direct</h3>
        </div>
        <span class="text-muted text-xs">{{ logs.length }} ligne(s)</span>
      </div>

      <div ref="logsContainerRef" class="max-h-80 min-h-48 overflow-y-auto p-3 font-mono text-xs leading-relaxed">
        <p v-if="logs.length === 0" class="text-muted">En attente des premiers événements…</p>
        <div
          v-for="(line, index) in logs"
          :key="`${index}-${line}`"
          class="animate-fade-in break-words whitespace-pre-wrap text-[#c9d1d9]"
        >
          {{ line }}
        </div>
      </div>
    </div>

    <!-- Prospects -->
    <div class="flex flex-col overflow-hidden rounded-lg border border-[#30363d] bg-[#050505]">
      <div class="flex items-center justify-between border-b border-[#30363d] px-4 py-2.5">
        <h3 class="text-sm font-medium text-[#f9f9f9]">Prospects trouvés</h3>
        <span class="text-muted text-xs">{{ prospects.length }} ajouté(s)</span>
      </div>

      <div ref="prospectsContainerRef" class="max-h-80 min-h-48 overflow-y-auto p-3">
        <p v-if="prospects.length === 0" class="text-muted text-sm">
          Les prospects s'afficheront ici au fur et à mesure…
        </p>

        <div
          v-for="prospect in prospects"
          :key="prospect.id"
          class="animate-fade-in mb-2 rounded-lg border border-[#30363d] bg-[#1a1a1a] p-3 last:mb-0"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-[#f9f9f9]">{{ prospect.name }}</p>
              <p v-if="prospect.city" class="text-muted mt-0.5 truncate text-xs">{{ prospect.city }}</p>
              <p v-if="prospect.phone" class="text-muted mt-1 truncate text-xs">
                <i class="fa-solid fa-phone mr-1"></i>{{ prospect.phone }}
              </p>
            </div>
            <span class="text-muted shrink-0 text-[10px] tracking-wide uppercase">
              {{ formatProspectSource(prospect.source) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { Prospect } from '~/types'
import { formatProspectSource } from '~/constants/prospectSources'

const props = defineProps<{
  logs: string[]
  prospects: Prospect[]
  isRunning: boolean
}>()

const logsContainerRef = ref<HTMLElement | null>(null)
const prospectsContainerRef = ref<HTMLElement | null>(null)

watch(
  () => props.logs.length,
  async () => {
    await nextTick()
    const el = logsContainerRef.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  },
)

watch(
  () => props.prospects.length,
  async () => {
    await nextTick()
    const el = prospectsContainerRef.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  },
)
</script>

<style scoped>
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.25s ease-out;
}
</style>
