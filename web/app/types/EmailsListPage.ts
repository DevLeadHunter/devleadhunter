/** A single engagement signal (delivered / opened / clicked) for the table. */
export type EngagementStep = {
  key: string
  label: string
  icon: string
  ts: string | null | undefined
  color: string
}
