import type {
  SupportTicketSummary,
  SupportTicketDetail,
  SupportTopicOption,
  SupportTicketStatus,
  SupportTicketTopic,
  SupportMessage,
} from '~/types'
import { api } from './api'

interface TicketFilters {
  scope?: 'mine' | 'all'
  status?: SupportTicketStatus
  includeClosed?: boolean
}

interface CreateTicketPayload {
  subject: string
  topic: SupportTicketTopic
  message: string
  attachments?: File[]
}

interface PostMessagePayload {
  message: string
  attachments?: File[]
}

const SUPPORT_BASE_URL = '/api/v1/support'

/**
 *
 */
function getApiUrl(): string {
  const config = useRuntimeConfig()
  return config.public.apiBase
}

/**
 *
 */
function getAuthHeaders(): HeadersInit {
  const userStore = useUserStore()
  const headers: HeadersInit = {}
  if (userStore.token) {
    headers.Authorization = `Bearer ${userStore.token}`
  }
  return headers
}

/**
 *
 */
async function fetchForm<T>(endpoint: string, formData: FormData, method: string = 'POST'): Promise<T> {
  const response = await fetch(`${getApiUrl()}${endpoint}`, {
    method,
    headers: {
      ...getAuthHeaders(),
    },
    body: formData,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    throw new Error(errorText || `API request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

/**
 *
 */
async function fetchJson<T>(endpoint: string, data: unknown, method: string = 'PATCH'): Promise<T> {
  const response = await fetch(`${getApiUrl()}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    throw new Error(errorText || `API request failed (${response.status})`)
  }

  return response.json() as Promise<T>
}

/**
 *
 */
export async function getTopics(): Promise<SupportTopicOption[]> {
  return api.get<SupportTopicOption[]>(`${SUPPORT_BASE_URL}/topics`)
}

/**
 *
 */
export async function getTickets(filters: TicketFilters = {}): Promise<SupportTicketSummary[]> {
  const params = new URLSearchParams()
  params.set('scope', filters.scope || 'mine')
  if (filters.status) {
    params.set('status', filters.status)
  }
  if (filters.includeClosed) {
    params.set('include_closed', 'true')
  }

  return api.get<SupportTicketSummary[]>(`${SUPPORT_BASE_URL}/tickets?${params.toString()}`)
}

/**
 *
 */
export async function createTicket(payload: CreateTicketPayload): Promise<SupportTicketDetail> {
  const formData = new FormData()
  formData.append('subject', payload.subject)
  formData.append('topic', payload.topic)
  formData.append('message', payload.message)

  payload.attachments?.forEach((file) => {
    formData.append('attachments', file)
  })

  return fetchForm<SupportTicketDetail>(`${SUPPORT_BASE_URL}/tickets`, formData, 'POST')
}

/**
 *
 */
export async function getTicket(ticketId: number): Promise<SupportTicketDetail> {
  return api.get<SupportTicketDetail>(`${SUPPORT_BASE_URL}/tickets/${ticketId}`)
}

/**
 *
 */
export async function postMessage(ticketId: number, payload: PostMessagePayload): Promise<SupportMessage> {
  const formData = new FormData()
  formData.append('message', payload.message)

  payload.attachments?.forEach((file) => {
    formData.append('attachments', file)
  })

  return fetchForm<SupportMessage>(`${SUPPORT_BASE_URL}/tickets/${ticketId}/messages`, formData, 'POST')
}

/**
 *
 */
export async function updateTicketStatus(ticketId: number, status: SupportTicketStatus): Promise<SupportTicketSummary> {
  return fetchJson<SupportTicketSummary>(`${SUPPORT_BASE_URL}/tickets/${ticketId}/status`, { status }, 'PATCH')
}
