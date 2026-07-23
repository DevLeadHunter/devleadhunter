import { ref, type Ref } from 'vue'
import { useRuntimeConfig } from '#app'
import type { Prospect } from '~/types'

export type ScrapingJobProgressState = {
  current: number
  total: number
  percentage: number
  current_prospect: string | null
  estimated_time_remaining: number | null
}

export type ScrapingJobStreamEvent =
  | { type: 'log'; message: string }
  | { type: 'prospect'; prospect: Prospect }
  | ({
      type: 'progress'
    } & ScrapingJobProgressState)
  | { type: 'duplicate_skipped'; name: string }
  | {
      type: 'done'
      summary: { added: number; skipped_duplicates: number; status: string }
    }
  | { type: 'cancelled'; summary: { added: number; skipped_duplicates: number } }
  | { type: 'error'; message: string }

export type ScrapingJobStreamHandlers = {
  onDone?: (summary: { added: number; skipped_duplicates: number; status: string }) => void
  onCancelled?: (summary: { added: number; skipped_duplicates: number }) => void
  onError?: (message: string) => void
}

const defaultProgress = (): ScrapingJobProgressState => ({
  current: 0,
  total: 0,
  percentage: 0,
  current_prospect: null,
  estimated_time_remaining: null,
})

/**
 *
 */
export function useScrapingJobStream() {
  const logs: Ref<string[]> = ref([])
  const prospects: Ref<Prospect[]> = ref([])
  const progress: Ref<ScrapingJobProgressState> = ref(defaultProgress())
  const isConnected = ref(false)
  const skippedDuplicates = ref(0)

  let websocket: WebSocket | null = null
  let handlers: ScrapingJobStreamHandlers = {}

  /**
   *
   */
  function appendLog(message: string): void {
    if (logs.value.includes(message)) {
      return
    }
    logs.value.push(message)
  }

  /**
   *
   */
  function appendProspect(prospect: Prospect): void {
    if (prospects.value.some((item) => item.id === prospect.id)) {
      return
    }
    prospects.value.push(prospect)
  }

  /**
   *
   */
  function handleEvent(event: ScrapingJobStreamEvent): void {
    switch (event.type) {
      case 'log':
        appendLog(event.message)
        break
      case 'prospect':
        appendProspect(event.prospect)
        break
      case 'progress':
        progress.value = {
          current: event.current,
          total: event.total,
          percentage: event.percentage,
          current_prospect: event.current_prospect,
          estimated_time_remaining: event.estimated_time_remaining,
        }
        break
      case 'duplicate_skipped':
        skippedDuplicates.value += 1
        break
      case 'done':
        handlers.onDone?.(event.summary)
        break
      case 'cancelled':
        handlers.onCancelled?.(event.summary)
        break
      case 'error':
        handlers.onError?.(event.message)
        break
      default:
        break
    }
  }

  /**
   *
   */
  function hydrateFromJob(job: {
    logs?: string[]
    live_prospects?: Prospect[]
    progress?: ScrapingJobProgressState
    skipped_duplicates?: number
  }): void {
    logs.value = [...(job.logs ?? [])]
    prospects.value = [...(job.live_prospects ?? [])]
    progress.value = job.progress ? { ...job.progress } : defaultProgress()
    skippedDuplicates.value = job.skipped_duplicates ?? 0
  }

  /**
   *
   */
  function reset(): void {
    logs.value = []
    prospects.value = []
    progress.value = defaultProgress()
    skippedDuplicates.value = 0
  }

  /**
   *
   */
  function connect(jobId: string, token: string, streamHandlers: ScrapingJobStreamHandlers = {}): void {
    disconnect()
    handlers = streamHandlers

    const config = useRuntimeConfig()
    try {
      const apiUrl = new URL(config.public.apiBase)
      apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
      const basePath = apiUrl.pathname.replace(/\/$/, '')
      apiUrl.pathname = `${basePath}/api/v1/scraping-jobs/${jobId}/ws`
      apiUrl.searchParams.set('token', token)

      const ws = new WebSocket(apiUrl.toString())
      websocket = ws

      ws.onopen = () => {
        isConnected.value = true
      }

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as ScrapingJobStreamEvent
          handleEvent(payload)
        } catch (error) {
          console.warn('Invalid scraping job websocket event', error)
        }
      }

      ws.onclose = () => {
        isConnected.value = false
        websocket = null
      }

      ws.onerror = () => {
        isConnected.value = false
      }
    } catch (error) {
      console.error('Failed to connect scraping job websocket', error)
      isConnected.value = false
    }
  }

  /**
   *
   */
  function disconnect(): void {
    if (websocket) {
      websocket.close()
      websocket = null
    }
    isConnected.value = false
    handlers = {}
  }

  return {
    logs,
    prospects,
    progress,
    skippedDuplicates,
    isConnected,
    connect,
    disconnect,
    hydrateFromJob,
    reset,
  }
}
