import type { SendPolicy } from '~/types/Automation'

export type UiSendPolicyFieldsProps = {
  modelValue: SendPolicy
}

export type UiSendPolicyFieldsEmits = {
  'update:modelValue': [policy: SendPolicy]
}
