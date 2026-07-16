/** One day of Gmail Postmaster domain reputation. */
export interface ReputationTimelineDay {
  date: string
  /** Postmaster value: HIGH | MEDIUM | LOW | BAD (null = no data that day). */
  reputation: string | null
}

/** Props of the reputation timeline (one colored square per day). */
export interface EmailHealthReputationTimelineProps {
  days: ReputationTimelineDay[]
}
