/** Round trip between the plain text typed in a reply box and the HTML body sent by email. */
export class ReplyBodyFormat {
  /**
   * Turn typed text into email HTML: blank lines split paragraphs, single line breaks become `<br />`.
   * @param text - The typed text.
   * @returns The escaped HTML body.
   */
  static toHtml(text: string): string {
    return text
      .trim()
      .split(/\n{2,}/)
      .map((paragraph: string): string => `<p>${ReplyBodyFormat.escape(paragraph).replace(/\n/g, '<br />')}</p>`)
      .join('')
  }

  /**
   * Turn an HTML body written in the app back into editable text.
   * @param html - The HTML body.
   * @returns The plain text, paragraphs separated by a blank line.
   */
  static toText(html: string): string {
    const text: string = html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>\s*<p[^>]*>/gi, '\n\n')
      .replace(/<(?:\/p|\/div)[^>]*>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .trim()
    if (typeof document === 'undefined') return text
    const decoder: HTMLTextAreaElement = document.createElement('textarea')
    decoder.innerHTML = text
    return decoder.value
  }

  /**
   * Escape user text for safe HTML embedding.
   * @param text - Raw text.
   * @returns The escaped text.
   */
  private static escape(text: string): string {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
}
