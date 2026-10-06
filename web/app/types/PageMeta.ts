declare module '#app' {
  /**
   * Options a page gives the dashboard layout. `shouldFillDashboardViewport`: the page fills the content area
   * itself, so the layout drops its padding, stops scrolling `<main>` and hides the bottom tab bar.
   */
  interface PageMeta {
    shouldFillDashboardViewport?: boolean
  }
}

export {}
