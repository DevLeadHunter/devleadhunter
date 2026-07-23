/** A row of the « c'est prêt » recap. */
export type ConfigurationRecapRow = {
  label: string
  value: string
  done: boolean
}

/** A row of the welcome screen checklist. */
export type ConfigurationChecklistRow = {
  icon: string
  title: string
  detail: string
  required: boolean
}
