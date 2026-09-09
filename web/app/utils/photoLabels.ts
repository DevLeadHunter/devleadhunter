/**
 * Human labels of the vision photo kinds (what a prospect photo shows), as chips in the UI.
 */
export class PhotoLabels {
  private static readonly KIND_LABELS: Record<string, string> = {
    dish: 'Plat',
    drink: 'Boisson',
    truck: 'Camion',
    menu_board: 'Menu',
    interior: 'Intérieur',
    people: 'Équipe',
    event: 'Événement',
    logo_or_flyer: 'Flyer',
    other: 'Autre',
    unknown: 'Non analysée',
  }

  /**
   * Chip label for a photo kind, falling back to the raw kind for an unknown value.
   * @param kind - The vision kind (`dish`, `truck`, `menu_board`…) or `unknown`.
   * @returns The French label shown to the operator.
   */
  static label(kind: string | null | undefined): string {
    const key: string = (kind ?? 'unknown').trim() || 'unknown'
    return PhotoLabels.KIND_LABELS[key] ?? key
  }
}
