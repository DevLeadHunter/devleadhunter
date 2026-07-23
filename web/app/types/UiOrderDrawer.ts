import type { Order } from '~/services/ordersService'

export type UiOrderDrawerProps = {
  open: boolean
  order: Order | null
}
