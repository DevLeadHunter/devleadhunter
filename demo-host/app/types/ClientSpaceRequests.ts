import type { AiAssistantClientRequest } from '~/types/AiAssistantClientSpace'

/** Props of the client-space request list. */
export type ClientSpaceRequestsProps = {
  requests: AiAssistantClientRequest[]
  pendingCount: number
  busyRequestId: number | null
}

/** Events of the ClientSpaceRequests component. */
export type ClientSpaceRequestsEmits = {
  handled: [requestId: number]
}
