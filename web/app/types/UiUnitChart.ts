export type UiUnitChartTone = 'ink' | 'green' | 'blue' | 'violet' | 'red' | 'neutral' | 'outline' | 'dashed'

export type UiUnitChartUnit = {
  key: number
  group: string
  tone: UiUnitChartTone
  title: string
  details: string[]
}

export type UiUnitChartProps = {
  units: UiUnitChartUnit[]
  label: string
  unitSize?: number
  isWrapping?: boolean
}

export type UiUnitChartEmits = {
  select: [key: number]
}
