<template>
  <div class="max-w-3xl space-y-8">
    <UiPageHeader eyebrow="Prospection" title="Vidéo de prospection" :description="pageDescription" />

    <PresenterVideoConfig v-if="isWebsitesTakeShown" />
    <div
      v-for="moduleAdapter in modulePresenterVideoAdapters"
      :id="moduleAdapter.sectionAnchorId ?? undefined"
      :key="moduleAdapter.moduleKey"
      :class="isWebsitesTakeShown ? 'border-t border-[var(--app-line)] pt-8' : ''"
    >
      <PresenterVideoConfig :module="moduleAdapter.moduleKey" />
    </div>
    <StoryblokConnectionCard v-if="isWebsitesTakeShown" />
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

const hasOpenModuleOwnTake: ComputedRef<boolean> = computed(
  (): boolean => PresenterVideoAdapterRegistry.of(moduleStore.activeKey) !== null,
)

const isWebsitesTakeShown: ComputedRef<boolean> = computed(
  (): boolean => !hasOpenModuleOwnTake.value || moduleStore.activeKey === WEBSITES_MODULE_KEY,
)

const modulePresenterVideoAdapters: ComputedRef<PresenterVideoModuleAdapter[]> = computed(
  (): PresenterVideoModuleAdapter[] =>
    PresenterVideoAdapterRegistry.list().filter(
      (adapter: PresenterVideoModuleAdapter): boolean =>
        adapter.moduleKey !== WEBSITES_MODULE_KEY &&
        moduleStore.isModuleUsable(adapter.moduleKey) &&
        (!hasOpenModuleOwnTake.value || adapter.moduleKey === moduleStore.activeKey),
    ),
)

const pageDescription: ComputedRef<string> = computed((): string => {
  const everyDemoLabels: string[] = modulePresenterVideoAdapters.value.map(
    (adapter: PresenterVideoModuleAdapter): string => adapter.wording.everyDemoLabel,
  )

  if (isWebsitesTakeShown.value) {
    everyDemoLabels.unshift(PresenterVideoAdapterRegistry.wordingOf(WEBSITES_MODULE_KEY).everyDemoLabel)
  }
  const hasSeveralTakes: boolean = everyDemoLabels.length > 1
  const lastLabel: string = everyDemoLabels.pop() ?? ''
  const demosLabel: string = hasSeveralTakes ? `${everyDemoLabels.join(', ')} et ${lastLabel}` : lastLabel
  const takesIntroduction: string = hasSeveralTakes ? 'Vos prises webcam, par module.' : 'Vos prises webcam.'
  return (
    `${takesIntroduction} Gardez-en plusieurs, comparez leurs vidéos d'exemple et choisissez celle qui sert : ` +
    `${demosLabel} génère ensuite sa vidéo personnalisée, prête pour vos emails.`
  )
})
</script>
