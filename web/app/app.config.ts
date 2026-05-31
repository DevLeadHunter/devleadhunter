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
          class: 'rounded-lg bg-[#f9f9f9] text-[#050505] shadow-sm hover:bg-[#e4e4e4] hover:shadow-md',
        },
        {
          color: 'neutral',
          variant: 'outline',
          class:
            'rounded-lg border border-[#30363d]/50 bg-transparent text-[#f9f9f9] hover:border-[#30363d] hover:bg-[#1a1a1a]',
        },
        {
          color: 'error',
          variant: 'solid',
          class: 'rounded bg-[#da3633] text-[#f9f9f9] hover:bg-[#DC4747]',
        },
      ],
      defaultVariants: {
        size: 'lg',
      },
    },
    input: {
      slots: {
        root: 'w-full',
        base: 'h-10 w-full rounded border border-[#30363d] bg-[#050505] px-3 text-sm text-[#f9f9f9] placeholder-[#8b949e] transition-all focus:border-[#f9f9f9] focus:ring-0 focus:outline-none',
      },
    },
    textarea: {
      slots: {
        root: 'w-full',
        base: 'w-full rounded border border-[#30363d] bg-[#050505] px-3 py-2 text-sm text-[#f9f9f9] placeholder-[#8b949e] transition-all focus:border-[#f9f9f9] focus:ring-0 focus:outline-none',
      },
    },
    selectMenu: {
      slots: {
        root: 'relative inline-flex w-full items-center',
        base: 'h-10 w-full rounded border border-[#30363d] bg-[#050505] px-3 text-sm text-[#f9f9f9] transition-all focus:border-[#f9f9f9] focus:ring-0 focus:outline-none',
        placeholder: 'text-[#8b949e]',
        content: 'rounded-lg border border-[#30363d] bg-[#1a1a1a] shadow-lg',
        item: 'text-sm text-[#f9f9f9] data-[highlighted]:bg-[#30363d] data-[state=checked]:bg-[#30363d]/70',
        trailingIcon: 'text-[#8b949e]',
      },
    },
    inputMenu: {
      slots: {
        root: 'relative inline-flex w-full items-center h-10 rounded border border-[#30363d] bg-[#050505] ring-0 shadow-none',
        base: 'h-full w-full border-0 bg-transparent px-3 text-sm text-[#f9f9f9] placeholder-[#8b949e] focus:outline-none focus:ring-0',
        placeholder: 'text-[#8b949e]',
        content: 'rounded-lg border border-[#30363d] bg-[#1a1a1a] shadow-lg',
        item: 'text-sm text-[#f9f9f9] data-[highlighted]:bg-[#30363d] data-[state=checked]:bg-[#30363d]/70',
        itemDescription: 'text-xs text-[#8b949e]',
        trailingIcon: 'text-[#8b949e]',
      },
    },
    modal: {
      slots: {
        overlay: 'bg-black/70',
        content: 'rounded-lg border border-[#30363d] bg-[#1a1a1a] shadow-xl',
        header: 'border-b border-[#30363d]',
        body: 'text-[#f9f9f9]',
        footer: 'border-t border-[#30363d]',
      },
    },
    card: {
      slots: {
        root: 'rounded-lg border border-[#30363d] bg-[#1a1a1a] shadow-sm',
        header: 'border-b border-[#30363d]',
        body: 'text-[#f9f9f9]',
        footer: 'border-t border-[#30363d]',
      },
    },
    formField: {
      slots: {
        label: 'text-xs font-medium text-[#8b949e]',
        error: 'text-xs text-[#DC4747]',
        hint: 'text-xs text-[#8b949e]',
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
          class: 'border border-[#30363d] bg-[#050505] text-[#f9f9f9]',
        },
      ],
    },
    checkbox: {
      slots: {
        root: 'items-center',
        base: 'size-4 rounded border border-[#30363d] bg-[#050505] ring-0 transition-colors hover:border-[#8b949e] focus-visible:outline-none focus-visible:border-[#f9f9f9] data-[state=checked]:border-[#f9f9f9] data-[state=checked]:bg-[#f9f9f9]',
        indicator: 'text-[#050505]',
        icon: 'size-3',
        label: 'text-sm font-normal text-[#8b949e] cursor-pointer select-none',
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
