/**
 * A form brought up to date with its record: the fields the record changed take their new value, the others keep what
 * was typed, so a refresh of the record never wipes an edit in progress.
 * @param form - The form, possibly edited.
 * @param previous - The form values of the record before it changed.
 * @param next - The form values of the record now.
 * @returns The form with the record's changes.
 */
export function withRecordChanges<T extends Record<string, unknown>>(form: T, previous: T, next: T): T {
  const synced: T = { ...form }
  for (const key in next) {
    if (JSON.stringify(next[key]) !== JSON.stringify(previous[key])) synced[key] = next[key]
  }
  return synced
}
