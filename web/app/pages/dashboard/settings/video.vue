<template>
  <div class="max-w-3xl space-y-8">
    <UiPageHeader eyebrow="Prospection" title="Vidéo de prospection" :description="pageDescription" />

    <PresenterVideoConfig />
    <div
      v-for="moduleAdapter in modulePresenterVideoAdapters"
      :id="moduleAdapter.sectionAnchorId ?? undefined"
      :key="moduleAdapter.moduleKey"
      class="border-t border-[var(--app-line)] pt-8"
    >
      <PresenterVideoConfig :module="moduleAdapter.moduleKey" />
    </div>
    <StoryblokConnectionCard />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { PresenterVideoModuleAdapter } from '~/types/PresenterVideoConfig'
import { computed } from 'vue'
import { WEBSITES_MODULE_KEY } from '~/constants/productModules'
import { useModuleStore } from '~/stores/moduleStore'
import { PresenterVideoAdapterRegistry } from '~/utils/presenterVideoAdapterRegistry'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const moduleStore: ReturnType<typeof useModuleStore> = useModuleStore()

const modulePresenterVideoAdapters: ComputedRef<PresenterVideoModuleAdapter[]> = computed(
  (): PresenterVideoModuleAdapter[] =>
    PresenterVideoAdapterRegistry.list().filter(
      (adapter: PresenterVideoModuleAdapter): boolean =>
        adapter.moduleKey !== WEBSITES_MODULE_KEY && moduleStore.isModuleUsable(adapter.moduleKey),
    ),
)

const pageDescription: ComputedRef<string> = computed((): string => {
  const everyDemoLabels: string[] = [
    PresenterVideoAdapterRegistry.wordingOf(WEBSITES_MODULE_KEY).everyDemoLabel,
    ...modulePresenterVideoAdapters.value.map(
      (adapter: PresenterVideoModuleAdapter): string => adapter.wording.everyDemoLabel,
    ),
  ]
  const lastLabel: string = everyDemoLabels.pop() ?? ''
  const demosLabel: string = everyDemoLabels.length > 0 ? `${everyDemoLabels.join(', ')} et ${lastLabel}` : lastLabel
  return (
    "Vos prises webcam, par module. Gardez-en plusieurs, comparez leurs vidéos d'exemple et choisissez celle qui sert : " +
    `${demosLabel} génère ensuite sa vidéo personnalisée, prête pour vos emails.`
  )
})
</script>
