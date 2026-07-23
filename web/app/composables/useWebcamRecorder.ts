/**
 * Composable wrapping the webcam capture used to record the presenter clip.
 * @module composables/useWebcamRecorder
 */

import type { Ref } from 'vue'
import { onBeforeUnmount, ref } from 'vue'

/** A camera or microphone the user can pick. */
export type RecorderDevice = {
  deviceId: string
  label: string
}

/** One finished take, kept in memory until the three are sent. */
export type RecordedTake = {
  blob: Blob
  url: string
  durationSeconds: number
  extension: string
}

/**
 * Containers we try, best first. Chromium (so WebView2, so the desktop app)
 * can record H.264 in MP4 on recent versions; that dodges the WebM whose
 * header carries no duration. WebM stays the fallback — the API measures it
 * by decoding, so both work.
 */
const CANDIDATE_MIME_TYPES: readonly string[] = [
  'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
  'video/mp4',
  'video/webm;codecs=vp9,opus',
  'video/webm;codecs=vp8,opus',
  'video/webm',
]

/** Target capture size — matches the 720p canvas the final montage renders to. */
const CAPTURE_WIDTH: number = 1280
const CAPTURE_HEIGHT: number = 720

/** Bitrate cap: ~40 s of 720p stays a handful of megabytes. */
const VIDEO_BITS_PER_SECOND: number = 2_500_000

/** How often the recorder flushes a chunk, in ms. */
const CHUNK_INTERVAL_MS: number = 250

/**
 * Turn a raw ``getUserMedia`` rejection into something a non-technical user
 * can act on. The Windows cases matter most: the OS-level privacy switch and
 * a camera held by another app both surface as generic DOM exceptions.
 *
 * @param error - Whatever the media API rejected with.
 * @returns A French sentence naming the fix.
 */
function describeMediaError(error: unknown): string {
  const name: string = error instanceof DOMException ? error.name : ''
  switch (name) {
    case 'NotAllowedError':
    case 'PermissionDeniedError':
      return (
        "L'accès à la caméra a été refusé. Autorisez-le dans la fenêtre qui s'affiche, et vérifiez " +
        'que Windows autorise les applications de bureau à utiliser la caméra ' +
        '(Paramètres → Confidentialité et sécurité → Caméra).'
      )
    case 'NotFoundError':
    case 'DevicesNotFoundError':
      return 'Aucune caméra ou aucun micro détecté. Branchez-les puis réessayez.'
    case 'NotReadableError':
    case 'TrackStartError':
      return 'La caméra est déjà utilisée par une autre application (Teams, Zoom, OBS…). Fermez-la puis réessayez.'
    case 'OverconstrainedError':
      return 'La caméra sélectionnée ne peut pas filmer dans ce format. Choisissez-en une autre.'
    case 'SecurityError':
      return "L'accès à la caméra nécessite une connexion sécurisée (HTTPS)."
    default:
      return error instanceof Error && error.message
        ? `Impossible d'accéder à la caméra : ${error.message}`
        : "Impossible d'accéder à la caméra."
  }
}

/**
 * Pick the best container this browser can actually record.
 * @returns A supported MIME type, or an empty string to let the browser choose.
 */
function resolveMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  return CANDIDATE_MIME_TYPES.find((candidate: string): boolean => MediaRecorder.isTypeSupported(candidate)) ?? ''
}

/**
 * Map a recording MIME type to the file extension the API expects.
 * @param mimeType - MIME type the recorder actually used.
 * @returns ``mp4`` or ``webm``.
 */
function extensionForMimeType(mimeType: string): string {
  return mimeType.includes('mp4') ? 'mp4' : 'webm'
}

/**
 * Webcam capture for the presenter clip: permission, device choice, live audio
 * level and take-by-take recording.
 *
 * Everything is torn down on unmount — a forgotten ``MediaStream`` keeps the
 * camera light on, which reads as the app spying on the user.
 *
 * @returns Reactive capture state and its controls.
 */
export function useWebcamRecorder(): {
  stream: Ref<MediaStream | null>
  isReady: Ref<boolean>
  isRequesting: Ref<boolean>
  isRecording: Ref<boolean>
  error: Ref<string | null>
  cameras: Ref<RecorderDevice[]>
  microphones: Ref<RecorderDevice[]>
  selectedCameraId: Ref<string>
  selectedMicrophoneId: Ref<string>
  audioLevel: Ref<number>
  elapsedSeconds: Ref<number>
  isRecordingSupported: () => boolean
  requestAccess: () => Promise<boolean>
  switchDevices: (cameraId: string, microphoneId: string) => Promise<void>
  startRecording: () => boolean
  stopRecording: () => Promise<RecordedTake | null>
  releaseTake: (take: RecordedTake) => void
  stopEverything: () => void
} {
  const stream: Ref<MediaStream | null> = ref(null)
  const isReady: Ref<boolean> = ref(false)
  const isRequesting: Ref<boolean> = ref(false)
  const isRecording: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)
  const cameras: Ref<RecorderDevice[]> = ref([])
  const microphones: Ref<RecorderDevice[]> = ref([])
  const selectedCameraId: Ref<string> = ref('')
  const selectedMicrophoneId: Ref<string> = ref('')
  const audioLevel: Ref<number> = ref(0)
  const elapsedSeconds: Ref<number> = ref(0)

  // Plumbing kept out of the reactive surface — none of it belongs in a template.
  let recorder: MediaRecorder | null = null
  let chunks: Blob[] = []
  let audioContext: AudioContext | null = null
  let analyser: AnalyserNode | null = null
  let levelFrame: number | null = null
  let timerHandle: ReturnType<typeof setInterval> | null = null
  let startedAt: number = 0

  /**
   * Whether this browser can record at all.
   * @returns True when both capture and recording APIs exist.
   */
  function isRecordingSupported(): boolean {
    return (
      typeof navigator !== 'undefined' &&
      Boolean(navigator.mediaDevices?.getUserMedia) &&
      typeof MediaRecorder !== 'undefined'
    )
  }

  /** Stop the running audio-level meter and release its graph. */
  function stopLevelMeter(): void {
    if (levelFrame !== null) {
      cancelAnimationFrame(levelFrame)
      levelFrame = null
    }
    analyser = null
    if (audioContext) {
      void audioContext.close().catch((): void => undefined)
      audioContext = null
    }
    audioLevel.value = 0
  }

  /**
   * Drive {@link audioLevel} from the live microphone track.
   *
   * This is the cheapest insurance in the whole flow: it is what stops someone
   * from recording three takes into a muted microphone.
   *
   * @param source - The stream to listen to.
   */
  function startLevelMeter(source: MediaStream): void {
    stopLevelMeter()
    if (source.getAudioTracks().length === 0) return
    try {
      audioContext = new AudioContext()
      // Un contexte créé hors interaction démarre « suspended » : le VU-mètre resterait à zéro.
      if (audioContext.state === 'suspended') void audioContext.resume().catch((): void => undefined)
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 512
      audioContext.createMediaStreamSource(source).connect(analyser)
      const samples: Uint8Array<ArrayBuffer> = new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount))

      const tick: () => void = (): void => {
        if (!analyser) return
        analyser.getByteTimeDomainData(samples)
        let peak: number = 0
        for (const sample of samples) peak = Math.max(peak, Math.abs(sample - 128) / 128)
        // Ease downward so the meter reads as a level, not a strobe.
        audioLevel.value = Math.max(peak, audioLevel.value * 0.82)
        levelFrame = requestAnimationFrame(tick)
      }
      levelFrame = requestAnimationFrame(tick)
    } catch {
      // A missing AudioContext only costs the meter, never the recording.
      stopLevelMeter()
    }
  }

  /** Stop every track of the current stream and clear it. */
  function releaseStream(): void {
    stopLevelMeter()
    stream.value?.getTracks().forEach((track: MediaStreamTrack): void => {
      track.stop()
    })
    stream.value = null
    isReady.value = false
  }

  /**
   * List the cameras and microphones, keeping the current selection when valid.
   *
   * Labels stay empty until permission is granted, so this only runs once a
   * stream exists — otherwise the picker would show « Caméra 1, Caméra 2 ».
   */
  async function refreshDevices(): Promise<void> {
    try {
      const devices: MediaDeviceInfo[] = await navigator.mediaDevices.enumerateDevices()
      cameras.value = devices
        .filter((device: MediaDeviceInfo): boolean => device.kind === 'videoinput')
        .map(
          (device: MediaDeviceInfo, index: number): RecorderDevice => ({
            deviceId: device.deviceId,
            label: device.label || `Caméra ${index + 1}`,
          }),
        )
      microphones.value = devices
        .filter((device: MediaDeviceInfo): boolean => device.kind === 'audioinput')
        .map(
          (device: MediaDeviceInfo, index: number): RecorderDevice => ({
            deviceId: device.deviceId,
            label: device.label || `Micro ${index + 1}`,
          }),
        )
    } catch {
      // Not fatal: the user keeps the default devices.
    }
  }

  /**
   * Open a stream for the given devices and wire the level meter to it.
   * @param cameraId - Camera device ID, or an empty string for the default.
   * @param microphoneId - Microphone device ID, or an empty string for the default.
   * @throws With a user-facing message when capture is refused.
   */
  async function openStream(cameraId: string, microphoneId: string): Promise<void> {
    const constraints: MediaStreamConstraints = {
      video: {
        width: { ideal: CAPTURE_WIDTH },
        height: { ideal: CAPTURE_HEIGHT },
        frameRate: { ideal: 30 },
        ...(cameraId ? { deviceId: { exact: cameraId } } : {}),
      },
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        ...(microphoneId ? { deviceId: { exact: microphoneId } } : {}),
      },
    }

    const opened: MediaStream = await navigator.mediaDevices.getUserMedia(constraints)
    releaseStream()
    stream.value = opened
    isReady.value = true

    const videoTrack: MediaStreamTrack | undefined = opened.getVideoTracks()[0]
    const audioTrack: MediaStreamTrack | undefined = opened.getAudioTracks()[0]
    selectedCameraId.value = videoTrack?.getSettings().deviceId ?? cameraId
    selectedMicrophoneId.value = audioTrack?.getSettings().deviceId ?? microphoneId

    startLevelMeter(opened)
  }

  /**
   * Ask for camera + microphone access and prepare the preview.
   * @returns True once the preview is live, false when access was refused.
   */
  async function requestAccess(): Promise<boolean> {
    if (!isRecordingSupported()) {
      error.value = 'Ce navigateur ne sait pas enregistrer de vidéo. Importez plutôt un fichier.'
      return false
    }
    isRequesting.value = true
    error.value = null
    try {
      await openStream(selectedCameraId.value, selectedMicrophoneId.value)
      await refreshDevices()
      return true
    } catch (err: unknown) {
      error.value = describeMediaError(err)
      return false
    } finally {
      isRequesting.value = false
    }
  }

  /**
   * Switch camera and/or microphone, reopening the stream.
   * @param cameraId - Camera to use.
   * @param microphoneId - Microphone to use.
   */
  async function switchDevices(cameraId: string, microphoneId: string): Promise<void> {
    if (isRecording.value) return
    error.value = null
    try {
      await openStream(cameraId, microphoneId)
    } catch (err: unknown) {
      error.value = describeMediaError(err)
    }
  }

  /**
   * Start recording the live stream.
   * @returns True when the recorder actually started.
   */
  function startRecording(): boolean {
    const source: MediaStream | null = stream.value
    if (!source || isRecording.value) return false

    const mimeType: string = resolveMimeType()
    try {
      recorder = new MediaRecorder(source, {
        ...(mimeType ? { mimeType } : {}),
        videoBitsPerSecond: VIDEO_BITS_PER_SECOND,
      })
    } catch (err: unknown) {
      error.value = describeMediaError(err)
      return false
    }

    chunks = []
    recorder.ondataavailable = (event: BlobEvent): void => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.start(CHUNK_INTERVAL_MS)

    isRecording.value = true
    startedAt = performance.now()
    elapsedSeconds.value = 0
    timerHandle = setInterval((): void => {
      elapsedSeconds.value = (performance.now() - startedAt) / 1000
    }, 100)
    return true
  }

  /**
   * Stop the current take and hand it back.
   * @returns The finished take, or null when nothing was being recorded.
   */
  function stopRecording(): Promise<RecordedTake | null> {
    const active: MediaRecorder | null = recorder
    if (!active || !isRecording.value) return Promise.resolve(null)

    return new Promise<RecordedTake | null>((resolve: (take: RecordedTake | null) => void): void => {
      active.onstop = (): void => {
        if (timerHandle !== null) {
          clearInterval(timerHandle)
          timerHandle = null
        }
        const durationSeconds: number = (performance.now() - startedAt) / 1000
        const mimeType: string = active.mimeType || resolveMimeType() || 'video/webm'
        const blob: Blob = new Blob(chunks, { type: mimeType })
        chunks = []
        recorder = null
        isRecording.value = false
        elapsedSeconds.value = durationSeconds
        resolve({
          blob,
          url: URL.createObjectURL(blob),
          durationSeconds,
          extension: extensionForMimeType(mimeType),
        })
      }
      active.stop()
    })
  }

  /**
   * Release a take's object URL.
   * @param take - The take to forget.
   */
  function releaseTake(take: RecordedTake): void {
    URL.revokeObjectURL(take.url)
  }

  /** Stop recording and close the camera. */
  function stopEverything(): void {
    if (recorder && isRecording.value) {
      try {
        recorder.stop()
      } catch {
        // Already stopped — nothing to clean beyond the stream itself.
      }
    }
    recorder = null
    chunks = []
    isRecording.value = false
    if (timerHandle !== null) {
      clearInterval(timerHandle)
      timerHandle = null
    }
    releaseStream()
  }

  onBeforeUnmount((): void => {
    stopEverything()
  })

  return {
    stream,
    isReady,
    isRequesting,
    isRecording,
    error,
    cameras,
    microphones,
    selectedCameraId,
    selectedMicrophoneId,
    audioLevel,
    elapsedSeconds,
    isRecordingSupported,
    requestAccess,
    switchDevices,
    startRecording,
    stopRecording,
    releaseTake,
    stopEverything,
  }
}
