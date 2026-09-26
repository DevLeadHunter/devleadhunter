export type AssistantActionsCardProps = {
  status: string
  isRegenerating: boolean
  isSendingClientLink: boolean
  isMarkingSold: boolean
  isDeleting: boolean
}

export type AssistantActionsCardEmits = {
  regenerate: []
  'send-client-space': []
  'mark-sold': []
  remove: []
}
