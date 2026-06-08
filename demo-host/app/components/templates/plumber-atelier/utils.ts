/** Pictos line « plan technique », cohérents entre eux (stroke, sans fill). */
export const ICONS: Record<string, string> = {
  emergency:
    '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M9 3h6"/>',
  install:
    '<path d="M14 7a4 4 0 0 1-5.4 3.7L5 14.3a2 2 0 1 0 2.8 2.8l3.6-3.6A4 4 0 0 0 17 9.5l-2.3 2.3-2.2-.5-.5-2.2L14.2 7Z"/>',
  heater:
    '<rect x="6" y="3" width="12" height="18" rx="3"/><path d="M9 8h6M12 12c1.5 1.2 1.5 2.8 0 4-1.5-1.2-1.5-2.8 0-4Z"/>',
  leak:
    '<path d="M12 3c3 4 5 6.5 5 9a5 5 0 0 1-10 0c0-2.5 2-5 5-9Z"/><path d="M12 14a2 2 0 0 0 2-2"/>',
  drain:
    '<circle cx="12" cy="12" r="8"/><path d="M12 8a4 4 0 0 1 0 8 2.5 2.5 0 0 1 0-5"/>',
  bath:
    '<path d="M4 12h16v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-3Z"/><path d="M6 12V6a2 2 0 0 1 2-2 2 2 0 0 1 2 2"/><path d="M9 7h2"/>',
  pipe:
    '<path d="M4 9h9a3 3 0 0 1 3 3v8M4 6v6M2 9h4M14 20h4"/>',
}

export function serviceIcon(icon?: string): string {
  const inner = ICONS[icon ?? ''] ?? ICONS.pipe
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${inner}</svg>`
}
