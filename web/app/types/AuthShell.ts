/**
 * Which auth page the shell hosts — drives the right-panel pitch copy
 * (signup sells the product, login welcomes back).
 */
export type AuthShellMode = 'login' | 'signup'

/** Props for the AuthShell split-screen component. */
export interface AuthShellProps {
  /** Auth page hosted in the left column. */
  mode: AuthShellMode
}
