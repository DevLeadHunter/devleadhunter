export type AssistantActionsCardProps = {
  status: string
  isRegenerating: boolean
  isSendingClientLink: boolean
  isRevokingClientLinks: boolean
  clientSpaceLinkToCopy: string | null
  isMarkingSold: boolean
  isDeleting: boolean
}

export type AssistantActionsCardEmits = {
  regenerate: []
  'send-client-space': []
  'revoke-client-links': []
  'mark-sold': []
  remove: []
}
