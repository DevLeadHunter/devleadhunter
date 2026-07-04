<template>
  <section v-if="safety.items.length" id="securite" ref="sectionRef" class="lumen-section" aria-label="Sécurité et normes">
    <div class="lumen-container lumen-safety__inner">
      <div class="lumen-safety__copy" data-lumen-reveal>
        <p class="lumen-kicker">{{ safety.kicker }}</p>
        <h2 class="lumen-heading">{{ safety.heading }}</h2>
        <p v-if="safety.text" class="lumen-safety__text">{{ safety.text }}</p>
        <p class="lumen-safety__note">
          <LumenIcon name="check" class="lumen-safety__note-icon" />
          Contrôle systématique en fin d'intervention
        </p>
      </div>

      <div class="lumen-safety__board" data-lumen-reveal :style="{ '--lumen-reveal-delay': '140ms' }">
        <p class="lumen-safety__board-title" aria-hidden="true">
          Tableau — protections
          <span class="lumen-safety__board-leds">
            <span></span><span></span><span></span>
          </span>
        </p>

        <ul class="lumen-safety__modules">
          <li v-for="(item, index) in safety.items" :key="item.code" class="lumen-safety__module" :class="{ 'is-on': litCount > index }">
            <button
              type="button"
              class="lumen-safety__switch"
              :aria-pressed="litCount > index"
              :aria-label="`Protection ${item.code}`"
              @click="toggleModule(index)"
            >
              <span class="lumen-safety__lever" aria-hidden="true"></span>
            </button>
            <p class="lumen-safety__code">{{ item.code }}</p>
            <p class="lumen-safety__label">{{ item.label }}</p>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * Section « Sécurité & normes » : les normes (NF C 15-100, Consuel, 30 mA, terre)
 * sont présentées comme les modules d'un tableau électrique. Quand la section
 * entre à l'écran, les disjoncteurs s'enclenchent un par un — cliquables ensuite.
 */
import type { Ref } from 'vue'
import LumenIcon from './LumenIcon.vue'
import type { LumenSafetyContent } from '../types'

const props = defineProps<{
  safety: LumenSafetyContent
}>()

const sectionRef: Ref<HTMLElement | null> = ref(null)
const litCount: Ref<number> = ref(0)
const timers: number[] = []

/**
 * Enclenche les modules un par un (stagger), déclenché à l'entrée à l'écran.
 * @returns void
 */
function powerOnModules(): void {
  props.safety.items.forEach((_, index: number): void => {
    timers.push(
      window.setTimeout((): void => {
        litCount.value = Math.max(litCount.value, index + 1)
      }, 240 * index),
    )
  })
}

/**
 * Permet de « jouer » avec un disjoncteur : coupe/réenclenche le module cliqué.
 * @param index Index du module cliqué.
 * @returns void
 */
function toggleModule(index: number): void {
  litCount.value = litCount.value > index ? index : index + 1
}

onMounted((): void => {
  const reducedMotion: boolean = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reducedMotion) {
    litCount.value = props.safety.items.length
    return
  }
  const observer = new IntersectionObserver(
    (entries: IntersectionObserverEntry[]): void => {
      if (entries.some((entry: IntersectionObserverEntry): boolean => entry.isIntersecting)) {
        powerOnModules()
        observer.disconnect()
      }
    },
    { threshold: 0.35 },
  )
  if (sectionRef.value) {
    observer.observe(sectionRef.value)
  }
  onUnmounted((): void => {
    observer.disconnect()
    timers.forEach((timer: number): void => window.clearTimeout(timer))
  })
})
</script>

<style scoped>
.lumen-safety__inner {
  display: grid;
  gap: 3rem;
  align-items: center;
}

@media (min-width: 1024px) {
  .lumen-safety__inner {
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    gap: 4.5rem;
  }
}

.lumen-safety__text {
  margin-top: 1.2rem;
  line-height: 1.7;
  color: var(--lumen-muted);
}

.lumen-safety__note {
  margin-top: 1.6rem;
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-family: var(--lumen-font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--lumen-yellow);
}

.lumen-safety__note-icon {
  width: 15px;
  height: 15px;
}

/* ---- Le tableau ---- */

.lumen-safety__board {
  padding: 1.5rem;
  background: var(--lumen-raised);
  border: 1px solid color-mix(in srgb, white 14%, transparent);
  clip-path: polygon(18px 0, 100% 0, 100% calc(100% - 18px), calc(100% - 18px) 100%, 0 100%, 0 18px);
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 8%, transparent);
}

.lumen-safety__board-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--lumen-font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--lumen-muted);
  padding: 0 0.2rem 1.1rem;
  border-bottom: 1px solid var(--lumen-line);
}

.lumen-safety__board-leds {
  display: inline-flex;
  gap: 0.4rem;
}

.lumen-safety__board-leds span {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: color-mix(in srgb, white 18%, transparent);
}

.lumen-safety__board-leds span:first-child {
  background: var(--lumen-yellow);
  box-shadow: 0 0 7px color-mix(in srgb, var(--lumen-yellow) 70%, transparent);
}

.lumen-safety__modules {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
  list-style: none;
  padding: 1.2rem 0 0;
  margin: 0;
}

@media (min-width: 640px) and (max-width: 1023px) {
  .lumen-safety__modules {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.lumen-safety__module {
  padding: 1.1rem 1rem 1.2rem;
  background: var(--lumen-night);
  border: 1px solid var(--lumen-line);
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
  transition: border-color 0.3s ease;
}

.lumen-safety__module.is-on {
  border-color: color-mix(in srgb, var(--lumen-yellow) 38%, transparent);
}

.lumen-safety__switch {
  display: inline-flex;
  align-items: flex-end;
  width: 26px;
  height: 44px;
  padding: 3px;
  background: var(--lumen-raised);
  border: 1px solid color-mix(in srgb, white 16%, transparent);
  border-radius: 6px;
  cursor: pointer;
}

.lumen-safety__switch:focus-visible {
  outline: 2px solid var(--lumen-yellow);
  outline-offset: 2px;
}

.lumen-safety__lever {
  width: 100%;
  height: 17px;
  border-radius: 4px;
  background: color-mix(in srgb, white 26%, transparent);
  transform: translateY(0);
  transition:
    transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1),
    background-color 0.28s ease,
    box-shadow 0.28s ease;
}

.lumen-safety__module.is-on .lumen-safety__lever {
  transform: translateY(-19px);
  background: var(--lumen-yellow);
  box-shadow: 0 0 12px color-mix(in srgb, var(--lumen-yellow) 65%, transparent);
}

.lumen-safety__code {
  margin-top: 0.85rem;
  font-family: var(--lumen-font-mono);
  font-weight: 600;
  font-size: 0.92rem;
  letter-spacing: 0.05em;
  color: color-mix(in srgb, var(--lumen-muted) 75%, transparent);
  transition: color 0.3s ease, text-shadow 0.3s ease;
}

.lumen-safety__module.is-on .lumen-safety__code {
  color: var(--lumen-yellow);
  text-shadow: 0 0 16px color-mix(in srgb, var(--lumen-yellow) 45%, transparent);
}

.lumen-safety__label {
  margin-top: 0.45rem;
  font-size: 0.8rem;
  line-height: 1.55;
  color: var(--lumen-muted);
}

@media (prefers-reduced-motion: reduce) {
  .lumen-safety__lever {
    transition: none;
  }
}
</style>
