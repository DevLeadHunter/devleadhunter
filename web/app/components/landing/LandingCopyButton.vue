<template>
  <button type="button" class="landing-btn-ghost landing-btn--compact" @click="copyValue">
    <UIcon
      :name="copyState === 'copied' ? 'i-lucide-check' : 'i-lucide-copy'"
      class="h-4 w-4"
      :class="copyState === 'copied' ? 'text-[#2f7d4e]' : ''"
      aria-hidden="true"
    />
    <span aria-live="polite">{{ buttonLabel }}</span>
  </button>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { LandingCopyButtonProps, LandingCopyState } from '~/types/LandingCopyButton'
import { ClipboardCopy } from '~/utils/clipboardCopy'

const props: LandingCopyButtonProps = defineProps({
  value: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
})

const emit: {
  (e: 'copied'): void
} = defineEmits<{
  (e: 'copied'): void
}>()

const { t }: { t: (key: string, params?: Record<string, unknown>) => string } = useI18n()

const COPY_FEEDBACK_DURATION_MS: number = 1800
let feedbackTimer: ReturnType<typeof setTimeout> | undefined

const copyState: Ref<LandingCopyState> = ref('idle')

const buttonLabel: ComputedRef<string> = computed((): string => {
  if (copyState.value === 'copied') return t('landing.copyButton.copied')
  if (copyState.value === 'failed') return t('landing.copyButton.failed')
  return props.label
})

/**
 * Copy the value, then show the outcome until the feedback delay runs out.
 */
async function copyValue(): Promise<void> {
  const hasCopied: boolean = await ClipboardCopy.copyText(props.value)
  copyState.value = hasCopied ? 'copied' : 'failed'
  if (hasCopied) emit('copied')
  clearTimeout(feedbackTimer)
  feedbackTimer = setTimeout((): void => {
    copyState.value = 'idle'
  }, COPY_FEEDBACK_DURATION_MS)
}

onBeforeUnmount((): void => {
  clearTimeout(feedbackTimer)
})
</script>
