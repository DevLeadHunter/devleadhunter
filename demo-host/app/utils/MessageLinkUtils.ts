import type { AssistantMessagePart } from '~/types/AssistantMessage'

// An http(s) address, up to the first space or closing quote; trailing punctuation is trimmed below.
const URL_PATTERN: RegExp = /https?:\/\/[^\s<>"«»*]+/g
const TRAILING_PUNCTUATION: RegExp = /[.,;:!?)\]}'’…]+$/
// Markdown bold (« **https://…** »): the widget shows plain text, so the marks are dropped.
const BOLD_MARKS: RegExp = /\*\*/g

/**
 * Cuts an assistant reply into text and links, so the widget can show the site's pages as links without HTML.
 */
export class MessageLinkUtils {
  /**
   * The parts of a message: plain text, and the http(s) addresses it contains.
   * @param message - The message as written by the assistant (Markdown bold marks are dropped).
   * @returns The parts in order; a message without an address is one text part.
   */
  static parts(message: string): AssistantMessagePart[] {
    const content: string = message.replace(BOLD_MARKS, '')
    const parts: AssistantMessagePart[] = []
    let last: number = 0
    for (const match of content.matchAll(URL_PATTERN)) {
      const start: number = match.index ?? 0
      const url: string = match[0].replace(TRAILING_PUNCTUATION, '')
      if (start > last) parts.push({ kind: 'text', value: content.slice(last, start) })
      parts.push({ kind: 'link', value: url })
      last = start + url.length
    }
    if (last < content.length) parts.push({ kind: 'text', value: content.slice(last) })
    return parts
  }
}
