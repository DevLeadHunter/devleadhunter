const SIREN_DIGIT_COUNT: number = 9
export const SIRET_DIGIT_COUNT: number = 14

/**
 * Normalize a French SIREN/SIRET input to digits only.
 * @param rawValue - User input or stored value.
 * @returns Digits without separators.
 */
export function normalizeTaxIdDigits(rawValue: string): string {
  return rawValue.replace(/\D/g, '')
}

/**
 * Format a compact tax id for display (SIREN 3-3-3, SIRET 3-3-3-5).
 * @param compactTaxId - Digits only, up to 14 characters.
 * @returns A spaced display value.
 */
export function formatTaxIdForDisplay(compactTaxId: string): string {
  const digits: string = compactTaxId.slice(0, SIRET_DIGIT_COUNT)
  const groups: string[] = []

  if (digits.length > 0) {
    groups.push(digits.slice(0, Math.min(3, digits.length)))
  }
  if (digits.length > 3) {
    groups.push(digits.slice(3, Math.min(6, digits.length)))
  }
  if (digits.length > 6) {
    groups.push(digits.slice(6, Math.min(9, digits.length)))
  }
  if (digits.length > 9) {
    groups.push(digits.slice(9, SIRET_DIGIT_COUNT))
  }

  return groups.join(' ')
}

/**
 * Whether the value is a complete SIREN or SIRET length.
 * @param compactTaxId - Digits only.
 * @returns True when 9 or 14 digits long.
 */
export function isCompleteTaxId(compactTaxId: string): boolean {
  return compactTaxId.length === SIREN_DIGIT_COUNT || compactTaxId.length === SIRET_DIGIT_COUNT
}

/**
 * Whether the user started typing without reaching a valid length yet.
 * @param compactTaxId - Digits only.
 * @returns True between 1 and 13 digits, excluding 9.
 */
export function isIncompleteTaxId(compactTaxId: string): boolean {
  if (compactTaxId.length === 0 || isCompleteTaxId(compactTaxId)) {
    return false
  }
  return compactTaxId.length < SIRET_DIGIT_COUNT
}

/**
 * Validate the Luhn checksum of a complete SIREN or SIRET.
 * @param compactTaxId - Nine or fourteen digits.
 * @returns True when the checksum is valid.
 */
export function hasValidTaxIdChecksum(compactTaxId: string): boolean {
  if (!isCompleteTaxId(compactTaxId) || !/^\d+$/.test(compactTaxId)) {
    return false
  }

  const digits: number[] = compactTaxId.split('').map((character: string): number => Number(character))
  let checksumTotal: number = 0

  for (let positionFromRight: number = 0; positionFromRight < digits.length; positionFromRight += 1) {
    const digitIndexFromLeft: number = digits.length - 1 - positionFromRight
    let currentDigit: number = digits[digitIndexFromLeft] as number

    if (positionFromRight % 2 === 1) {
      currentDigit *= 2
      if (currentDigit > 9) {
        currentDigit -= 9
      }
    }

    checksumTotal += currentDigit
  }

  return checksumTotal % 10 === 0
}

/**
 * Extract the nine-digit SIREN from a SIREN or SIRET value.
 * @param compactTaxId - Digits only.
 * @returns The SIREN prefix.
 */
export function extractSiren(compactTaxId: string): string {
  return compactTaxId.slice(0, SIREN_DIGIT_COUNT)
}
