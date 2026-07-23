import type { Prospect } from '~/types'

/**
 * JSON import/export helpers for prospects (client side only — the JSON file
 * is the exchange format between DevLeadHunter and the outside world).
 */

/** Shape of one prospect inside an import/export JSON file. */
export type ProspectJsonItem = {
  name: string
  address?: string
  city?: string
  phone?: string
  email?: string
  website?: string
  category?: string
}

/** Result of parsing an import file: valid rows + human-readable row errors. */
export type ProspectJsonParseResult = {
  valid: ProspectJsonItem[]
  errors: string[]
}

/**
 * Trigger a browser download of the given content as a file.
 * @param filename - Suggested file name.
 * @param content - Text content of the file.
 */
function downloadFile(filename: string, content: string): void {
  const blob: Blob = new Blob([content], { type: 'application/json;charset=utf-8' })
  const url: string = URL.createObjectURL(blob)
  const anchor: HTMLAnchorElement = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

/**
 * Download the selected prospects as a JSON file (import-compatible shape).
 * @param prospects - Prospects to export.
 */
export function downloadProspectsJson(prospects: Prospect[]): void {
  const items: ProspectJsonItem[] = prospects.map((prospect: Prospect): ProspectJsonItem => {
    return {
      name: prospect.name,
      address: prospect.address ?? '',
      city: prospect.city ?? '',
      phone: prospect.phone ?? '',
      email: prospect.email ?? '',
      website: prospect.website ?? '',
      category: prospect.category,
    }
  })
  const date: string = new Date().toISOString().slice(0, 10)
  downloadFile(`prospects-${date}.json`, JSON.stringify(items, null, 2))
}

/**
 * Download an empty, documented JSON template for manual prospect imports.
 * The first row is a filled example; duplicate/replace it for each prospect.
 */
export function downloadProspectTemplateJson(): void {
  const template: ProspectJsonItem[] = [
    {
      name: 'Plomberie Dupont (exemple — remplacez et dupliquez cette ligne)',
      address: '12 rue des Artisans',
      city: 'Lyon',
      phone: '04 72 00 00 00',
      email: 'contact@plomberie-dupont.fr',
      website: '',
      category: 'plombier',
    },
    {
      name: '',
      address: '',
      city: '',
      phone: '',
      email: '',
      website: '',
      category: '',
    },
  ]
  downloadFile('modele-prospects.json', JSON.stringify(template, null, 2))
}

/**
 * Return the value as a trimmed string ('' when absent or not a string).
 * @param value - Raw JSON value.
 * @returns Trimmed string.
 */
function cleanString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

/**
 * Parse and validate the content of an import JSON file.
 * Accepted shape: an array of objects with at least a non-empty `name`
 * (`category` falls back to « Entreprise » when missing). Rows failing
 * validation are reported, valid rows are returned normalised.
 * @param text - Raw file content.
 * @returns Valid items + per-row error messages.
 * @throws {Error} When the file is not valid JSON or not an array.
 */
export function parseProspectsJson(text: string): ProspectJsonParseResult {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    throw new Error('Fichier invalide — ce n’est pas du JSON.')
  }
  if (!Array.isArray(raw)) {
    throw new Error('Le JSON doit être un tableau de prospects (utilisez le modèle).')
  }

  const valid: ProspectJsonItem[] = []
  const errors: string[] = []

  raw.forEach((entry: unknown, index: number): void => {
    if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) {
      errors.push(`Ligne ${index + 1} : entrée ignorée (objet attendu).`)
      return
    }
    const record = entry as Record<string, unknown>
    const name: string = cleanString(record.name)
    if (!name || name.startsWith('Plomberie Dupont (exemple')) {
      // Empty rows and the untouched template example are silently skipped.
      if (Object.values(record).some((value: unknown): boolean => cleanString(value) !== '')) {
        errors.push(`Ligne ${index + 1} : « name » est requis — entrée ignorée.`)
      }
      return
    }
    valid.push({
      name,
      address: cleanString(record.address),
      city: cleanString(record.city),
      phone: cleanString(record.phone),
      email: cleanString(record.email),
      website: cleanString(record.website),
      category: cleanString(record.category) || 'Entreprise',
    })
  })

  return { valid, errors }
}
