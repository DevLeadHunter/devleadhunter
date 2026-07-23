/** One day of Gmail Postmaster domain reputation. */
export type ReputationTimelineDay = {
  date: string
  /** Postmaster value: HIGH | MEDIUM | LOW | BAD (null = no data that day). */
  reputation: string | null
}

/** Props of the reputation timeline (one colored square per day). */
export type EmailHealthReputationTimelineProps = {
  days: ReputationTimelineDay[]
}
