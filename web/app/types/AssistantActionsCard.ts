export type AssistantActionsCardProps = {
  status: string
  isRegenerating: boolean
  isSendingClientLink: boolean
  isRevokingClientLinks: boolean
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
