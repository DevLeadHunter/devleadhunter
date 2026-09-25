export type AssistantActionsCardProps = {
  status: string
  isRegenerating: boolean
  isSendingClientLink: boolean
  isDeleting: boolean
}

export type AssistantActionsCardEmits = {
  regenerate: []
  'send-client-space': []
  remove: []
}
