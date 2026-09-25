import type { AiAssistantClientRequest } from '~/types/AiAssistantClientSpace'

/** Props of the client-space request list; `readOnly` in the example space (nothing to mark). */
export type ClientSpaceRequestsProps = {
  requests: AiAssistantClientRequest[]
  pendingCount: number
  busyRequestId: number | null
  readOnly: boolean
}

/** Events of the ClientSpaceRequests component. */
export type ClientSpaceRequestsEmits = {
  handled: [requestId: number]
}
