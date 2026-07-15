export default defineAppConfig({
  ui: {
    colors: {
      primary: 'neutral',
      neutral: 'zinc',
    },
    button: {
      slots: {
        base: 'inline-flex items-center justify-center gap-2 font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50',
      },
      variants: {
        size: {
          md: {
            base: 'h-10 px-4 text-sm',
          },
          lg: {
            base: 'h-12 px-6 text-base',
          },
        },
      },
      compoundVariants: [
        {
          color: 'primary',
          variant: 'solid',
          class:
            'rounded-full bg-[var(--app-btn-bg)] text-[var(--app-btn-text)] shadow-sm hover:opacity-90 hover:shadow-md',
        },
        {
          color: 'neutral',
          variant: 'outline',
          class:
            'rounded-full border border-[var(--app-line)] bg-transparent text-[var(--app-ink)] hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]',
        },
        {
          color: 'error',
          variant: 'solid',
          class: 'rounded-full bg-[var(--app-red)] text-[var(--app-surface)] hover:opacity-90',
        },
      ],
      defaultVariants: {
        size: 'lg',
      },
    },
    input: {
      slots: {
        root: 'w-full',
        base: 'h-9 w-full rounded-lg px-3 text-sm transition-all',
      },
    },
    textarea: {
      slots: {
        root: 'w-full',
        base: 'w-full rounded-lg px-3 py-2 text-sm transition-all',
      },
    },
    selectMenu: {
      slots: {
        root: 'relative inline-flex w-full items-center',
        base: 'h-9 w-full cursor-pointer rounded-lg px-3 text-sm transition-all',
        placeholder: 'text-[var(--app-faint)]',
        content: 'rounded-lg shadow-[var(--app-shadow-soft)]',
        // Barre de recherche intégrée : pas de cadre propre, juste un filet bas.
        input: 'h-9 border-0 border-b border-[var(--app-line)] text-sm focus:ring-0 focus:outline-none',
        item: 'cursor-pointer text-sm',
        trailingIcon: 'text-[var(--app-ink-soft)]',
      },
    },
    inputMenu: {
      slots: {
        root: 'relative inline-flex h-9 w-full items-center rounded-lg',
        base: 'h-full w-full px-3 text-sm',
        placeholder: 'text-[var(--app-faint)]',
        content: 'rounded-lg shadow-[var(--app-shadow-soft)]',
        item: 'cursor-pointer text-sm',
        itemDescription: 'text-xs text-[var(--app-ink-soft)]',
        trailingIcon: 'text-[var(--app-ink-soft)]',
      },
    },
    modal: {
      slots: {
        overlay: 'bg-[var(--app-overlay)]',
        content: 'rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] shadow-xl',
        header: 'border-b border-[var(--app-line)]',
        body: 'text-[var(--app-ink)]',
        footer: 'border-t border-[var(--app-line)]',
      },
    },
    card: {
      slots: {
        root: 'rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] shadow-none',
        header: 'border-b border-[var(--app-line)]',
        body: 'text-[var(--app-ink)]',
        footer: 'border-t border-[var(--app-line)]',
      },
    },
    formField: {
      slots: {
        label: 'text-xs font-medium text-[var(--app-ink-soft)]',
        error: 'text-xs text-[var(--app-red)]',
        hint: 'text-xs text-[var(--app-ink-soft)]',
      },
    },
    badge: {
      slots: {
        base: 'rounded-full px-2 py-0.5 text-xs font-medium',
      },
      compoundVariants: [
        {
          color: 'neutral',
          variant: 'subtle',
          class: 'border border-[var(--app-line)] bg-[var(--app-surface-2)] text-[var(--app-ink)]',
        },
      ],
    },
    checkbox: {
      slots: {
        root: 'items-center',
        base: 'size-4 cursor-pointer rounded border border-[var(--app-line)] bg-[var(--app-surface)] ring-0 transition-colors hover:border-[var(--app-ink-soft)] focus-visible:outline-none focus-visible:border-[var(--app-ink)] data-[state=checked]:border-[var(--app-ink)] data-[state=checked]:bg-[var(--app-ink)]',
        indicator: 'text-[var(--app-bg)]',
        icon: 'size-3',
        label: 'text-sm font-normal text-[var(--app-ink-soft)] cursor-pointer select-none',
        wrapper: 'ms-2.5',
      },
      defaultVariants: {
        color: 'neutral',
        size: 'md',
        variant: 'list',
        indicator: 'start',
      },
    },
  },
})
