/**
 * Pixel position of the caret inside a textarea / input.
 *
 * Uses the well-known "mirror div" technique: a hidden div is styled exactly
 * like the field, filled with the text up to the caret, and the caret marker's
 * offset is measured. Used to anchor the `{`-variable autocomplete dropdown.
 * @module utils/textareaCaret
 */

/** Caret offset within the field's content box. */
export interface CaretCoordinates {
  /** Distance from the field's top (px), before scroll compensation. */
  top: number
  /** Distance from the field's left (px). */
  left: number
  /** Line height at the caret (px). */
  height: number
}

/** CSS properties mirrored from the field onto the measuring div. */
const MIRRORED_PROPERTIES: string[] = [
  'boxSizing',
  'width',
  'height',
  'overflowX',
  'overflowY',
  'borderTopWidth',
  'borderRightWidth',
  'borderBottomWidth',
  'borderLeftWidth',
  'borderStyle',
  'paddingTop',
  'paddingRight',
  'paddingBottom',
  'paddingLeft',
  'fontStyle',
  'fontVariant',
  'fontWeight',
  'fontStretch',
  'fontSize',
  'fontSizeAdjust',
  'lineHeight',
  'fontFamily',
  'textAlign',
  'textTransform',
  'textIndent',
  'textDecoration',
  'letterSpacing',
  'wordSpacing',
  'tabSize',
  'whiteSpace',
  'wordWrap',
  'wordBreak',
]

/**
 * Compute the caret coordinates within a textarea/input.
 * @param element - The field being measured.
 * @param position - Caret index (typically `selectionEnd`).
 * @returns The caret offset (top/left/height) inside the field's content box.
 */
export function getCaretCoordinates(
  element: HTMLTextAreaElement | HTMLInputElement,
  position: number,
): CaretCoordinates {
  const doc: Document = element.ownerDocument
  const mirror: HTMLDivElement = doc.createElement('div')
  doc.body.appendChild(mirror)

  const style: CSSStyleDeclaration = mirror.style
  const computed: CSSStyleDeclaration = window.getComputedStyle(element)
  const isInput: boolean = element.nodeName === 'INPUT'

  style.position = 'absolute'
  style.visibility = 'hidden'
  style.whiteSpace = isInput ? 'nowrap' : 'pre-wrap'
  if (!isInput) style.wordWrap = 'break-word'

  for (const prop of MIRRORED_PROPERTIES) {
    // Inputs are single-line: force their box height to be intrinsic.
    if (isInput && prop === 'lineHeight') {
      style.lineHeight = computed.height
    } else {
      // Index via a loose cast — CSSStyleDeclaration has no string index signature.
      ;(style as unknown as Record<string, string>)[prop] = (computed as unknown as Record<string, string>)[prop]
    }
  }

  mirror.textContent = element.value.substring(0, position)
  if (isInput) mirror.textContent = mirror.textContent.replace(/\s/g, ' ')

  const marker: HTMLSpanElement = doc.createElement('span')
  // A non-empty character so the span has a measurable box at the caret.
  marker.textContent = element.value.substring(position) || '.'
  mirror.appendChild(marker)

  const coordinates: CaretCoordinates = {
    top: marker.offsetTop + parseInt(computed.borderTopWidth || '0', 10),
    left: marker.offsetLeft + parseInt(computed.borderLeftWidth || '0', 10),
    height: parseInt(computed.lineHeight || '0', 10) || marker.offsetHeight,
  }

  doc.body.removeChild(mirror)
  return coordinates
}
