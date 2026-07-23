import type { DirectiveBinding } from 'vue'

/**
 * Per-element reveal options accepted by the `v-reveal` directive.
 */
type RevealOptions = {
  delay?: number
}

/** Map each observed element to its IntersectionObserver so we can disconnect on unmount. */
const observers: WeakMap<HTMLElement, IntersectionObserver> = new WeakMap()

/**
 * Resolve the reveal delay (ms) from a directive binding value.
 * @param binding - Directive binding (`v-reveal="{ delay: 120 }"` or `v-reveal`).
 * @returns Delay in milliseconds, defaulting to 0.
 */
function resolveDelay(binding: DirectiveBinding<RevealOptions | number | undefined>): number {
  const value: RevealOptions | number | undefined = binding.value
  if (typeof value === 'number') return value
  if (value && typeof value.delay === 'number') return value.delay
  return 0
}

/**
 * Nuxt plugin registering the `v-reveal` directive.
 *
 * Elements fade/translate in once they scroll into view. The directive is
 * registered universally so SSR doesn't warn about an unresolved directive,
 * but its logic only runs client-side (the `mounted` hook never fires on the
 * server). When the user prefers reduced motion, it is a no-op.
 */
// defineNuxtPlugin fournit déjà le type de `nuxtApp` ; le réécrire boucle sur lui-même.
// eslint-disable-next-line @typescript-eslint/typedef
export default defineNuxtPlugin((nuxtApp): void => {
  nuxtApp.vueApp.directive('reveal', {
    /**
     * Arm the reveal effect once the element is mounted (client-side only).
     * @param el - The element the directive is bound to.
     * @param binding - Directive binding carrying the optional delay.
     */
    mounted(el: HTMLElement, binding: DirectiveBinding<RevealOptions | number | undefined>): void {
      const prefersReducedMotion: boolean = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (prefersReducedMotion || typeof IntersectionObserver === 'undefined') {
        return
      }

      const delay: number = resolveDelay(binding)
      if (delay > 0) {
        el.style.transitionDelay = `${delay}ms`
      }
      el.classList.add('reveal')

      const observer: IntersectionObserver = new IntersectionObserver(
        (entries: IntersectionObserverEntry[]): void => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              el.classList.add('is-visible')
              observer.unobserve(el)
            }
          }
        },
        { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
      )

      observer.observe(el)
      observers.set(el, observer)
    },
    /**
     * Disconnect the IntersectionObserver when the element is removed.
     * @param el - The element the directive was bound to.
     */
    unmounted(el: HTMLElement): void {
      const observer: IntersectionObserver | undefined = observers.get(el)
      if (observer) {
        observer.disconnect()
        observers.delete(el)
      }
    },
  })
})
