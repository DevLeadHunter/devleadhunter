import type { Order } from '~/services/ordersService'

/**
 * Props du composant UiOrderDrawer.
 */
export interface UiOrderDrawerProps {
  /** Indique si le drawer est visible. */
  open: boolean
  /** Commande à afficher — `null` masque le contenu. */
  order: Order | null
}
