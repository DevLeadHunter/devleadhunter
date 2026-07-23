/** Per-stage visual configuration for the timeline indicator + connector. */
export type EmailStageIndicatorStyle = {
  indicator: string
  separator: string
}

/** A single definition for one possible email event stage. */
export type EmailDeliveryStage = {
  key: string
  label: string
  icon: string
  timestamp: string | null | undefined
  style: EmailStageIndicatorStyle
  alwaysShow: boolean
}

/** Shape of a Nuxt UI timeline item with per-item style overrides. */
export type EmailTimelineEntry = {
  value: string
  title: string
  description?: string
  icon: string
  ui: {
    indicator: string
    title: string
    description: string
    separator: string
  }
}
