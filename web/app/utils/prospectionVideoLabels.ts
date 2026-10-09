import type { ProspectionVideoStatusTone, ProspectionVideoSubject } from '~/types/ProspectionVideo'

const FAILED_GENERATION_MESSAGE: string = 'La génération a échoué.'

/** Where a prospection video stands, in the same words on the demo site and receptionist pages. */
export class ProspectionVideoLabels {
  private constructor() {}

  /**
   * Whether the video waits for the owner's PC, or is being built by it.
   * @param subject - The demo site or receptionist.
   * @returns True while a request is left for the PC.
   */
  static isWaitingForDesktop(subject: ProspectionVideoSubject): boolean {
    return Boolean(subject.video_desktop_requested_at)
  }

  /**
   * The badge of the video: « En attente » until the PC takes it, « En cours » while it builds, then its status.
   * @param subject - The demo site or receptionist.
   * @returns The badge text, or null when no video was asked yet.
   */
  static statusLabel(subject: ProspectionVideoSubject): string | null {
    if (ProspectionVideoLabels.isWaitingForDesktop(subject)) {
      return subject.is_video_desktop_build_started ? 'En cours' : 'En attente'
    }
    if (subject.video_status === 'ready') {
      return 'Prête'
    }
    if (subject.video_status === 'failed') {
      return 'Échec'
    }
    return null
  }

  /**
   * The tone of that badge, which each page colours its own way.
   * @param subject - The demo site or receptionist.
   * @returns `waiting` while the PC has the video, else its status; null when no video was asked yet.
   */
  static statusTone(subject: ProspectionVideoSubject): ProspectionVideoStatusTone | null {
    if (ProspectionVideoLabels.isWaitingForDesktop(subject)) {
      return 'waiting'
    }
    if (subject.video_status === 'ready') {
      return 'ready'
    }
    if (subject.video_status === 'failed') {
      return 'failed'
    }
    return null
  }

  /**
   * Why the last generation failed, saying that a video already published stays online.
   * @param subject - The demo site or receptionist.
   * @returns The message, or null when the last generation did not fail.
   */
  static failureMessage(subject: ProspectionVideoSubject): string | null {
    if (subject.video_status === 'failed') {
      return subject.video_error || FAILED_GENERATION_MESSAGE
    }
    if (subject.video_status === 'ready' && subject.video_error) {
      return `La nouvelle génération a échoué, la vidéo actuelle reste en ligne. ${subject.video_error}`
    }
    return null
  }
}
