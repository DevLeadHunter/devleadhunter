import type {
  SupportTicketSummary,
  SupportTicketDetail,
  SupportTopicOption,
  SupportTicketStatus,
  SupportTicketTopic,
  SupportMessage,
} from '~/types'
import { ApiClient } from './api'

type TicketFilters = {
  scope?: 'mine' | 'all'
  status?: SupportTicketStatus
  includeClosed?: boolean
}

type CreateTicketPayload = {
  subject: string
  topic: SupportTicketTopic
  message: string
  attachments?: File[]
}

type PostMessagePayload = {
  message: string
  attachments?: File[]
}

const SUPPORT_BASE_URL: string = '/api/v1/support'

/** Resolve the API base URL from runtime config. */
function getApiUrl(): string {
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
  return config.public.apiBase
}

/** Build auth headers for raw `fetch` calls (multipart uploads). */
function getAuthHeaders(): HeadersInit {
  const userStore: ReturnType<typeof useUserStore> = useUserStore()
  const headers: HeadersInit = {}
  if (userStore.token) {
    headers.Authorization = `Bearer ${userStore.token}`
  }
  return headers
}

/**
 * POST/PATCH multipart form data outside the shared JSON `api` client.
 * @param endpoint - API path (e.g. `/api/v1/support/tickets`).
 * @param formData - Multipart body.
 * @param method - HTTP verb (defaults to POST).
 * @returns Parsed JSON response.
 */
async function fetchForm<T>(endpoint: string, formData: FormData, method: string = 'POST'): Promise<T> {
  const response: Response = await fetch(`${getApiUrl()}${endpoint}`, {
    method,
    headers: {
      ...getAuthHeaders(),
    },
    body: formData,
  })

  if (!response.ok) {
    const errorText: string = await response.text().catch(() => '')
    throw new Error(errorText || `API request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

/**
 * PATCH/POST JSON outside the shared `api` client when custom headers are needed.
 * @param endpoint - API path.
 * @param data - JSON-serializable body.
 * @param method - HTTP verb (defaults to PATCH).
 * @returns Parsed JSON response.
 */
async function fetchJson<T>(endpoint: string, data: unknown, method: string = 'PATCH'): Promise<T> {
  const response: Response = await fetch(`${getApiUrl()}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const errorText: string = await response.text().catch(() => '')
    throw new Error(errorText || `API request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

export class SupportService {
  /** List support topics for the ticket creation form. */
  static async getTopics(): Promise<SupportTopicOption[]> {
    return ApiClient.get<SupportTopicOption[]>(`${SUPPORT_BASE_URL}/topics`)
  }

  /**
   * List support tickets for the current user or the whole org (admin).
   * @param filters - Scope, status and closed-ticket flags.
   * @returns Ticket summaries.
   */
  static async getTickets(filters: TicketFilters = {}): Promise<SupportTicketSummary[]> {
    const params: URLSearchParams = new URLSearchParams()
    params.set('scope', filters.scope || 'mine')
    if (filters.status) {
      params.set('status', filters.status)
    }
    if (filters.includeClosed) {
      params.set('include_closed', 'true')
    }

    return ApiClient.get<SupportTicketSummary[]>(`${SUPPORT_BASE_URL}/tickets?${params.toString()}`)
  }

  /**
   * Open a new support ticket with an initial message and optional attachments.
   * @param payload - Subject, topic, message and files.
   * @returns The created ticket thread.
   */
  static async createTicket(payload: CreateTicketPayload): Promise<SupportTicketDetail> {
    const formData: FormData = new FormData()
    formData.append('subject', payload.subject)
    formData.append('topic', payload.topic)
    formData.append('message', payload.message)

    payload.attachments?.forEach((file: File) => {
      formData.append('attachments', file)
    })

    return fetchForm<SupportTicketDetail>(`${SUPPORT_BASE_URL}/tickets`, formData, 'POST')
  }

  /**
   * Load one ticket thread (messages + metadata).
   * @param ticketId - Ticket identifier.
   * @returns Full ticket detail.
   */
  static async getTicket(ticketId: number): Promise<SupportTicketDetail> {
    return ApiClient.get<SupportTicketDetail>(`${SUPPORT_BASE_URL}/tickets/${ticketId}`)
  }

  /**
   * Post a reply on an existing ticket (multipart when attachments are present).
   * @param ticketId - Ticket identifier.
   * @param payload - Message body and optional files.
   * @returns The persisted message.
   */
  static async postMessage(ticketId: number, payload: PostMessagePayload): Promise<SupportMessage> {
    const formData: FormData = new FormData()
    formData.append('message', payload.message)

    payload.attachments?.forEach((file: File) => {
      formData.append('attachments', file)
    })

    return fetchForm<SupportMessage>(`${SUPPORT_BASE_URL}/tickets/${ticketId}/messages`, formData, 'POST')
  }

  /**
   * Update a ticket status (e.g. close/reopen).
   * @param ticketId - Ticket identifier.
   * @param status - New status value.
   * @returns Updated ticket summary.
   */
  static async updateTicketStatus(ticketId: number, status: SupportTicketStatus): Promise<SupportTicketSummary> {
    return fetchJson<SupportTicketSummary>(`${SUPPORT_BASE_URL}/tickets/${ticketId}/status`, { status }, 'PATCH')
  }
}
