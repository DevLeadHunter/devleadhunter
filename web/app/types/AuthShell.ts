export type AuthShellMode = 'login' | 'signup'

/** Props for the AuthShell split-screen component. */
export type AuthShellProps = {
  /** Auth page hosted in the left column. */
  mode: AuthShellMode
}
