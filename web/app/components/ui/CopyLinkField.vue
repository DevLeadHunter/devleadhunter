<template>
  <div class="space-y-1.5">
    <p class="text-xs font-medium text-[var(--app-ink)]">{{ props.label }}</p>
    <div class="flex items-center gap-2">
      <input
        ref="linkInput"
        :value="props.url"
        readonly
        class="input-field h-9 min-w-0 flex-1 truncate text-xs"
        :aria-label="props.label"
        @focus="selectLink"
      />
      <button type="button" class="btn-secondary h-9 shrink-0 px-3 text-xs" @click="copyLink">
        {{ isCopied ? 'Copié' : 'Copier' }}
      </button>
    </div>
    <p v-if="hasCopyFailed" class="text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
      Le navigateur a refusé la copie : le lien est sélectionné, copiez-le à la main.
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import type { UiCopyLinkFieldProps } from '~/types/UiCopyLinkField'
import { ref } from 'vue'
import { ClipboardCopy } from '~/utils/clipboardCopy'

const props: UiCopyLinkFieldProps = defineProps({
  url: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
})

const linkInput: Ref<HTMLInputElement | null> = ref(null)
const isCopied: Ref<boolean> = ref(false)
const hasCopyFailed: Ref<boolean> = ref(false)

/** Select the whole link in the field, ready for a manual copy (iOS included). */
function selectLink(): void {
  linkInput.value?.setSelectionRange(0, props.url.length)
}

/**
 * Copy the link from the click itself; when the browser refuses, select it for a manual copy.
 * @returns A promise resolved once the copy was tried.
 */
async function copyLink(): Promise<void> {
  const isWritten: boolean = await ClipboardCopy.copyText(props.url)
  hasCopyFailed.value = !isWritten
  if (!isWritten) {
    linkInput.value?.focus()
    selectLink()
    return
  }
  isCopied.value = true
  setTimeout((): void => {
    isCopied.value = false
  }, 2000)
}
</script>
