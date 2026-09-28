/** Copies text to the clipboard and says whether it worked, including a text still being fetched (Safari, iPhone). */
export class ClipboardCopy {
  /**
   * Copy a text still being fetched; call it before any await of the click, whose permission Safari keeps for it.
   * @param pendingText - The text, once the network answers.
   * @returns Whether the clipboard received the text.
   */
  static async copyWhenReady(pendingText: Promise<string>): Promise<boolean> {
    if (typeof navigator === 'undefined' || !navigator.clipboard) return false
    if (typeof ClipboardItem === 'undefined' || typeof navigator.clipboard.write !== 'function') {
      try {
        return await ClipboardCopy.copyText(await pendingText)
      } catch {
        return false
      }
    }
    const clipboardItem: ClipboardItem = new ClipboardItem({
      'text/plain': pendingText.then((text: string): Blob => new Blob([text], { type: 'text/plain' })),
    })
    try {
      await navigator.clipboard.write([clipboardItem])
      return true
    } catch {
      return false
    }
  }

  /**
   * Copy a text already known, from the click that asked for it.
   * @param text - The text to copy.
   * @returns Whether the clipboard received the text.
   */
  static async copyText(text: string): Promise<boolean> {
    if (typeof navigator === 'undefined' || !navigator.clipboard) return false
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      return false
    }
  }
}
