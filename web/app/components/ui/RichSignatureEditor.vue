<template>
  <div>
    <div class="mb-1.5 flex items-center justify-between gap-2">
      <p class="text-muted text-[11px] leading-snug">
        Copiez votre signature depuis Gmail (Ctrl+A puis Ctrl+C dans le champ signature) et collez-la ici — la mise en
        forme et le logo sont conservés.
      </p>
      <button
        type="button"
        class="shrink-0 text-[11px] font-medium text-[var(--app-ink-soft)] underline decoration-[var(--app-line)] underline-offset-2 hover:text-[var(--app-ink)]"
        @click="showSource = !showSource"
      >
        {{ showSource ? 'Éditeur' : 'Voir le HTML' }}
      </button>
    </div>

    <!-- Source (HTML) view -->
    <textarea
      v-if="showSource"
      v-model="sourceProxy"
      rows="8"
      class="input-field font-mono text-xs"
      placeholder="<p>Léo Guillaume — Dibodev</p>"
    ></textarea>

    <!-- Rich (paste-friendly) view -->
    <div
      v-else
      ref="editableRef"
      contenteditable="true"
      role="textbox"
      aria-multiline="true"
      data-placeholder="Collez votre signature ici…"
      class="signature-editable input-field min-h-[140px] overflow-auto bg-white text-neutral-900"
      @input="onInput"
      @paste="onPaste"
      @blur="onInput"
    ></div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

/** Two-way bound signature HTML. */
const model = defineModel<string>({ default: '' })

/** Whether the raw-HTML source textarea is shown instead of the rich editor. */
const showSource: Ref<boolean> = ref<boolean>(false)

/** The contenteditable element. */
const editableRef: Ref<HTMLDivElement | null> = ref<HTMLDivElement | null>(null)

/** Proxy so the source textarea edits the same model value. */
const sourceProxy: ComputedRef<string> = computed({
  get: (): string => model.value,
  set: (value: string): void => {
    model.value = value
  },
})

/**
 * Strip anything unsafe from pasted HTML while keeping formatting and images
 * (so a Gmail signature logo survives). Removes scripts/styles/event handlers
 * and `javascript:` URLs.
 * @param html - Raw pasted HTML.
 * @returns Sanitised HTML safe to inject into the editor.
 */
function sanitizeSignatureHtml(html: string): string {
  const doc: Document = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('script, style, link, meta, title, noscript').forEach((node: Element): void => {
    node.remove()
  })
  doc.querySelectorAll('*').forEach((node: Element): void => {
    for (const attr of Array.from(node.attributes)) {
      const name: string = attr.name.toLowerCase()
      const value: string = attr.value.trim().toLowerCase()
      if (name.startsWith('on') || value.startsWith('javascript:')) {
        node.removeAttribute(attr.name)
      }
    }
  })
  return doc.body.innerHTML
}

/**
 * Insert sanitised HTML at the current caret inside the editor.
 * @param html - Sanitised HTML fragment.
 */
function insertHtmlAtCaret(html: string): void {
  const selection: Selection | null = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    if (editableRef.value) editableRef.value.innerHTML += html
    return
  }
  const range: Range = selection.getRangeAt(0)
  range.deleteContents()
  const fragment: DocumentFragment = range.createContextualFragment(html)
  range.insertNode(fragment)
  range.collapse(false)
  selection.removeAllRanges()
  selection.addRange(range)
}

/**
 * Keep the pasted HTML (formatting + logo) instead of the browser default.
 * @param event - The paste event.
 */
function onPaste(event: ClipboardEvent): void {
  const html: string | undefined = event.clipboardData?.getData('text/html')
  const text: string | undefined = event.clipboardData?.getData('text/plain')
  if (!html && !text) return
  event.preventDefault()
  const clean: string = html
    ? sanitizeSignatureHtml(html)
    : (text ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>')
  insertHtmlAtCaret(clean)
  onInput()
}

/** Push the editor content up to the model. */
function onInput(): void {
  if (editableRef.value) model.value = editableRef.value.innerHTML
}

// Sync external changes (opening the editor for another signature, source edits)
// into the contenteditable — but never while the user is typing in it.
watch(
  (): [string, boolean] => [model.value, showSource.value],
  (): void => {
    void nextTick((): void => {
      const editable = editableRef.value
      if (!editable || showSource.value) return
      if (document.activeElement === editable) return
      if (editable.innerHTML !== model.value) editable.innerHTML = model.value
    })
  },
)

onMounted((): void => {
  if (editableRef.value) editableRef.value.innerHTML = model.value
})
</script>

<style scoped>
.signature-editable:empty::before {
  content: attr(data-placeholder);
  color: #9ca3af;
}
.signature-editable:focus {
  outline: none;
}
</style>
