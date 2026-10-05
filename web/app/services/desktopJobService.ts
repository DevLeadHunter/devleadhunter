/**
 * Desktop jobs: work a device without the desktop app leaves for the owner's computer, which does it in the
 * background (reading a prospect's pages with the computer's Chrome, for a start).
 *
 * @module services/desktopJobService
 */
import { ApiClient } from '~/services/api'

const BASE_URL: string = '/api/v1/desktop-jobs'

/** What the desktop app has to do. */
export type DesktopJobKind = 'prospect_enrichment'

/** Lifecycle of a desktop job. */
export type DesktopJobStatus = 'waiting' | 'running' | 'done' | 'failed' | 'cancelled'

/** A desktop job as the dashboard and the desktop app read it. */
export type DesktopJob = {
  id: number
  kind: DesktopJobKind
  subject_id: number | null
  payload: Record<string, unknown> | null
  status: DesktopJobStatus
  error_message: string | null
  requested_at: string
  claimed_at: string | null
  finished_at: string | null
}

export class DesktopJobService {
  /**
   * Leave work for the owner's desktop app; the same work asked twice is one job.
   * @param kind - What the desktop app has to do.
   * @param subjectId - The record the work is about.
   * @returns The job, waiting for the desktop app or already taken by it.
   * @throws Error carrying the API message when the record is unknown.
   */
  static async request(kind: DesktopJobKind, subjectId: number): Promise<DesktopJob> {
    return ApiClient.post<DesktopJob>(BASE_URL, { kind, subject_id: subjectId })
  }

  /**
   * The user's jobs still waiting for a computer or being done.
   * @param kind - Only this kind of work.
   * @param subjectId - Only the work about this record.
   * @returns The waiting and running jobs, oldest first.
   */
  static async listActive(kind?: DesktopJobKind, subjectId?: number): Promise<DesktopJob[]> {
    return ApiClient.get<DesktopJob[]>(BASE_URL, { params: { kind, subject_id: subjectId } })
  }

  /**
   * The jobs this desktop app must take, oldest first. Only the desktop app calls this: it marks the PC on.
   * @returns The jobs no computer is doing.
   */
  static async listWaiting(): Promise<DesktopJob[]> {
    return ApiClient.get<DesktopJob[]>(`${BASE_URL}/waiting`)
  }

  /**
   * Tell the server this desktop app starts a job, so nothing else takes it.
   * @param jobId - The job.
   * @returns The job, running.
   * @throws Error when the job was withdrawn or another computer already does it.
   */
  static async claim(jobId: number): Promise<DesktopJob> {
    return ApiClient.post<DesktopJob>(`${BASE_URL}/${jobId}/claim`, {})
  }

  /**
   * Close a job whose result this desktop app saved through the usual routes.
   * @param jobId - The job.
   * @returns The job, done.
   */
  static async complete(jobId: number): Promise<DesktopJob> {
    return ApiClient.post<DesktopJob>(`${BASE_URL}/${jobId}/done`, {})
  }

  /**
   * Close a job this desktop app could not do, with the reason the dashboard shows.
   * @param jobId - The job.
   * @param message - Why the work was given up.
   * @returns The job, failed.
   */
  static async fail(jobId: number, message: string): Promise<DesktopJob> {
    return ApiClient.post<DesktopJob>(`${BASE_URL}/${jobId}/fail`, { message })
  }

  /**
   * Withdraw a job before a computer takes it.
   * @param jobId - The job.
   * @returns The job, cancelled.
   * @throws Error when the desktop app is already doing it.
   */
  static async cancel(jobId: number): Promise<DesktopJob> {
    return ApiClient.delete<DesktopJob>(`${BASE_URL}/${jobId}`)
  }
}
