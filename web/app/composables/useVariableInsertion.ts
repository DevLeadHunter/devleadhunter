/**
 * Assisted variable insertion for a subject/body field.
 *
 * Provides two things on top of a plain `<input>`/`<textarea>`:
 * 1. cursor-aware insertion (`insertToken`) used by the clickable palette;
 * 2. an inline `{`-triggered autocomplete (the "Nuxt-like" hint) with keyboard
 *    navigation, anchored at the caret.
 * @module composables/useVariableInsertion
 */
import type { Ref } from 'vue'
import type { EmailVariable } from '~/utils/emailVariables'
import { nextTick, ref } from 'vue'
import { EmailVariables } from '~/utils/emailVariables'
import { getCaretCoordinates } from '~/utils/textareaCaret'

/** Viewport position (px) where the autocomplete dropdown is anchored. */
export type AutocompletePosition = {
  top: number
  left: number
}

/** Reactive state + handlers returned by {@link useVariableInsertion}. */
export type VariableInsertion = {
  open: Ref<boolean>
  items: Ref<EmailVariable[]>
  activeIndex: Ref<number>
  position: Ref<AutocompletePosition>
  insertToken: (token: string) => void
  selectVariable: (variable: EmailVariable) => void
  onInput: () => void
  onKeydown: (event: KeyboardEvent) => void
  onBlur: () => void
}

/** Matches a `{` + partial identifier at the very end of the pre-caret text. */
const PARTIAL_TOKEN_REGEX: RegExp = /\{([a-zA-Z_]*)$/

/**
 * Wire assisted variable insertion to a field.
 * @param fieldRef - The bound `<input>`/`<textarea>` element.
 * @param getValue - Reads the current field value (the v-model getter).
 * @param setValue - Writes the field value (the v-model setter).
 * @returns Reactive autocomplete state and event handlers.
 */
export function useVariableInsertion(
  fieldRef: Ref<HTMLTextAreaElement | HTMLInputElement | null>,
  getValue: () => string,
  setValue: (value: string) => void,
): VariableInsertion {
  const open: Ref<boolean> = ref(false)
  const items: Ref<EmailVariable[]> = ref([])
  const activeIndex: Ref<number> = ref(0)
  const position: Ref<AutocompletePosition> = ref({ top: 0, left: 0 })

  /** Start index of the `{query` currently being completed (-1 when none). */
  let queryStart: number = -1

  /**
   * Move the caret to `index` after the value change has been rendered.
   * @param index - Target caret position.
   */
  function setCaret(index: number): void {
    void nextTick((): void => {
      const field = fieldRef.value
      if (!field) return
      field.focus()
      field.setSelectionRange(index, index)
    })
  }

  /** Hide the dropdown and reset its transient state. */
  function close(): void {
    open.value = false
    activeIndex.value = 0
    queryStart = -1
  }

  /**
   * Insert a full token at the caret (splice over the current selection).
   * @param token - The placeholder to insert (e.g. `{lien_demo}`).
   */
  function insertToken(token: string): void {
    const field = fieldRef.value
    const value: string = getValue()
    const start: number = field?.selectionStart ?? value.length
    const end: number = field?.selectionEnd ?? value.length
    setValue(value.slice(0, start) + token + value.slice(end))
    close()
    setCaret(start + token.length)
  }

  /**
   * Anchor the dropdown at the caret using the mirror-div measurement.
   * @param caretIndex - Caret index to measure.
   */
  function updatePosition(caretIndex: number): void {
    const field = fieldRef.value
    if (!field) return
    const caret = getCaretCoordinates(field, caretIndex)
    const rect: DOMRect = field.getBoundingClientRect()
    position.value = {
      top: rect.top + caret.top - field.scrollTop + caret.height,
      left: rect.left + caret.left - field.scrollLeft,
    }
  }

  /**
   * Detect a `{query` immediately before the caret and open/refresh the list.
   */
  function onInput(): void {
    const field = fieldRef.value
    if (!field) return
    const caret: number = field.selectionStart ?? 0
    const beforeCaret: string = field.value.slice(0, caret)
    const match: RegExpMatchArray | null = beforeCaret.match(PARTIAL_TOKEN_REGEX)

    if (!match) {
      close()
      return
    }

    const query: string = (match[1] ?? '').toLowerCase()
    queryStart = caret - match[0].length
    items.value = query
      ? EmailVariables.catalog.filter(
          (variable: EmailVariable): boolean =>
            variable.key.toLowerCase().includes(query) || variable.label.toLowerCase().includes(query),
        )
      : [...EmailVariables.catalog]

    if (items.value.length === 0) {
      close()
      return
    }

    activeIndex.value = 0
    updatePosition(caret)
    open.value = true
  }

  /**
   * Replace the active `{query` with a chosen variable's token.
   * @param variable - The variable to insert.
   */
  function selectVariable(variable: EmailVariable): void {
    const field = fieldRef.value
    const value: string = getValue()
    const caret: number = field?.selectionStart ?? value.length
    const start: number = queryStart >= 0 ? queryStart : caret
    setValue(value.slice(0, start) + variable.token + value.slice(caret))
    const nextCaret: number = start + variable.token.length
    close()
    setCaret(nextCaret)
  }

  /**
   * Keyboard control while the dropdown is open.
   * @param event - The keydown event.
   */
  function onKeydown(event: KeyboardEvent): void {
    if (!open.value || items.value.length === 0) return
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        activeIndex.value = (activeIndex.value + 1) % items.value.length
        break
      case 'ArrowUp':
        event.preventDefault()
        activeIndex.value = (activeIndex.value - 1 + items.value.length) % items.value.length
        break
      case 'Enter':
      case 'Tab': {
        event.preventDefault()
        const variable: EmailVariable | undefined = items.value[activeIndex.value]
        if (variable) selectVariable(variable)
        break
      }
      case 'Escape':
        event.preventDefault()
        close()
        break
      default:
        break
    }
  }

  /** Close on blur, deferred so a click on a dropdown item still registers. */
  function onBlur(): void {
    window.setTimeout((): void => close(), 150)
  }

  return {
    open,
    items,
    activeIndex,
    position,
    insertToken,
    selectVariable,
    onInput,
    onKeydown,
    onBlur,
  }
}
