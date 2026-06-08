/* ── Icônes line, jeu cohérent (stroke, sans fill) ── */
export const ICONS: Record<string, string> = {
  phone: '<path d="M3 5a2 2 0 0 1 2-2h2.4a1 1 0 0 1 1 .8l.9 4a1 1 0 0 1-.5 1.1L7.5 10a11 11 0 0 0 5.5 5.5l1.1-1.3a1 1 0 0 1 1.1-.5l4 .9a1 1 0 0 1 .8 1V18a2 2 0 0 1-2 2A15 15 0 0 1 3 5Z"/>',
  emergency: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M9 3h6"/>',
  leak: '<path d="M12 3c3 4 5 6.5 5 9a5 5 0 0 1-10 0c0-2.5 2-5 5-9Z"/><path d="M12 14a2 2 0 0 0 2-2"/>',
  bath: '<path d="M4 12h16v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-3Z"/><path d="M6 12V6a2 2 0 0 1 2-2 2 2 0 0 1 2 2"/><path d="M9 7h2"/>',
  heater: '<rect x="6" y="3" width="12" height="18" rx="3"/><path d="M9 8h6M12 12c1.5 1.2 1.5 2.8 0 4-1.5-1.2-1.5-2.8 0-4Z"/>',
  drain: '<circle cx="12" cy="12" r="8"/><path d="M12 8a4 4 0 0 1 0 8 2.5 2.5 0 0 1 0-5"/>',
  install: '<path d="M14 7a4 4 0 0 1-5.4 3.7L5 14.3a2 2 0 1 0 2.8 2.8l3.6-3.6A4 4 0 0 0 17 9.5l-2.3 2.3-2.2-.5-.5-2.2L14.2 7Z"/>',
  pipe: '<path d="M4 9h9a3 3 0 0 1 3 3v8M4 6v6M2 9h4M14 20h4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.4-3.4"/>',
  doc: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M10 13h5M10 16.5h5"/>',
  shield: '<path d="M12 3 5 6v5c0 4 3 6.6 7 8 4-1.4 7-4 7-8V6Z"/><path d="m9 12 2 2 4-4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  pin: '<path d="M12 21s7-5.5 7-11a7 7 0 0 0-14 0c0 5.5 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
  check: '<path d="m5 13 4 4L19 7"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  hand: '<path d="M7 11V6a1.5 1.5 0 0 1 3 0v4m0 0V4.5a1.5 1.5 0 0 1 3 0V10m0 0V6a1.5 1.5 0 0 1 3 0v7a6 6 0 0 1-6 6h-1a5 5 0 0 1-4-2l-2.5-3a1.6 1.6 0 0 1 2.3-2.2L7 12"/>',
  euro: '<circle cx="12" cy="12" r="9"/><path d="M15 8.5a4 4 0 1 0 0 7M8 11h5M8 13.5h5"/>',
  star: '<path d="m12 3 2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8L3.5 9.7l5.9-.9z"/>',
}
export function icon(name?: string): string {
  return ICONS[name ?? ''] ?? ICONS.pipe
}

/** Image Unsplash dimensionnée à la demande (ou passe-plat si déjà une URL complète paramétrée). */
export function img(url?: string, w = 1000, h = 0): string {
  if (!url) return ''
  if (!url.includes('images.unsplash.com')) return url
  const base = url.split('?')[0]
  const params = h ? `auto=format&fit=crop&w=${w}&h=${h}&q=80` : `auto=format&fit=crop&w=${w}&q=80`
  return `${base}?${params}`
}

export function initials(name?: string): string {
  if (!name) return '—'
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join('')
}
