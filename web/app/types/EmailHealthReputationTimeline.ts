/** One day of Gmail Postmaster domain reputation. */
export type ReputationTimelineDay = {
  date: string
  reputation: string | null
}

/** Props of the reputation timeline (one colored square per day). */
export type EmailHealthReputationTimelineProps = {
  days: ReputationTimelineDay[]
}
