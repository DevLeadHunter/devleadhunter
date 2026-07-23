/**
 * Props for the reusable `UiSendPolicyFields` component.
 * @module types/UiSendPolicyFields
 */
import type { SendPolicy } from '~/types/Automation'

/** Props of the `UiSendPolicyFields` component. */
export type UiSendPolicyFieldsProps = {
  /** The edited sending cadence (v-model). */
  modelValue: SendPolicy
}
