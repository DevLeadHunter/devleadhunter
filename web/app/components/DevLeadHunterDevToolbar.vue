<template>
  <div
    v-if="isDesktopDev"
    class="fixed right-4 bottom-4 z-[90] flex items-center gap-2 rounded-full border border-[#30363d] bg-[#1a1a1a]/90 px-2 py-1 shadow-lg backdrop-blur"
  >
    <span class="pl-2 text-[10px] font-semibold tracking-[0.12em] text-amber-400 uppercase">Dev</span>
    <UButton
      size="xs"
      color="warning"
      variant="soft"
      icon="i-lucide-database"
      :loading="isSyncing"
      title="Écrase la base LOCALE avec les données de PROD (desktop dev uniquement). Requiert web/.env.sync (voir .env.sync.example)."
      @click="onSyncDatabase"
    >
      Sync DB prod → local
    </UButton>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'

const { isDesktopDev, syncDevDatabaseFromProd } = useDesktopRuntime()
const toast = useToast()

const isSyncing: Ref<boolean> = ref<boolean>(false)

/**
 * Confirm, then pull the prod database into the local dev database. Shows the result
 * (or error) via a toast. Only reachable in desktop dev (button is gated + the Tauri
 * command is compiled only into debug builds).
 */
async function onSyncDatabase(): Promise<void> {
  const confirmed: boolean = window.confirm(
    'Synchroniser la base LOCALE avec les données de PROD ?\n\nLes tables locales seront REMPLACÉES par le dump de prod.',
  )
  if (!confirmed) {
    return
  }
  isSyncing.value = true
  try {
    const message: string = await syncDevDatabaseFromProd()
    toast.add({ title: 'Synchro DB terminée', description: message, color: 'success' })
  } catch (error) {
    toast.add({
      title: 'Synchro DB — échec',
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  } finally {
    isSyncing.value = false
  }
}
</script>
