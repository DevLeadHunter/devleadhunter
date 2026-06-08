<template>
  <section class="ba">
    <div class="section-head">
      <p class="kicker">Avant / après</p>
      <h2 class="section-title reveal" data-reveal>{{ beforeAfter.heading || 'Le résultat parle de lui-même' }}</h2>
      <p v-if="beforeAfter.subheading" class="section-lede reveal" data-reveal style="--d: 80ms">
        {{ beforeAfter.subheading }}
      </p>
    </div>
    <div class="ba-wrap reveal" data-reveal>
      <div
        ref="baRef"
        class="ba-stage"
        @pointerdown="baDown"
      >
        <img :src="img(beforeAfter.after_image as string, 1400, 900)" class="ba-img" alt="Après travaux" draggable="false" loading="lazy" />
        <div class="ba-before" :style="{ width: baPos + '%' }">
          <img
            :src="img(beforeAfter.before_image as string, 1400, 900)"
            class="ba-img ba-img-before"
            :style="{ width: baStageWidthPx }"
            alt="Avant travaux"
            draggable="false"
            loading="lazy"
          />
          <span class="ba-tag ba-tag-before">{{ beforeAfter.before_label || 'Avant' }}</span>
        </div>
        <span class="ba-tag ba-tag-after">{{ beforeAfter.after_label || 'Après' }}</span>
        <button
          ref="baHandle"
          class="ba-handle"
          :style="{ left: baPos + '%' }"
          role="slider"
          aria-label="Comparer avant et après"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="Math.round(baPos)"
          tabindex="0"
          @keydown="baKey"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6 4 12l5 6M15 6l5 6-5 6" /></svg>
        </button>
      </div>
      <p v-if="beforeAfter.caption" class="ba-caption">{{ beforeAfter.caption }}</p>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { BeforeAfterBlock } from '../types'
import { img } from '../utils'

defineProps<{
  beforeAfter: BeforeAfterBlock
}>()

/* ── Comparateur avant/après ── */
const baRef = ref<HTMLElement | null>(null)
const baHandle = ref<HTMLElement | null>(null)
const baPos = ref<number>(58)
const baStageWidthPx = ref<string>('100%')
let baDragging = false

function baFromClientX(clientX: number): void {
  const el = baRef.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const p = ((clientX - r.left) / r.width) * 100
  baPos.value = Math.max(0, Math.min(100, p))
}
function baDown(e: PointerEvent): void {
  baDragging = true
  baFromClientX(e.clientX)
  baHandle.value?.focus()
}
function baMove(e: PointerEvent): void {
  if (!baDragging) return
  baFromClientX(e.clientX)
}
function baUp(): void {
  baDragging = false
}
function baKey(e: KeyboardEvent): void {
  if (e.key === 'ArrowLeft') {
    baPos.value = Math.max(0, baPos.value - 4)
    e.preventDefault()
  } else if (e.key === 'ArrowRight') {
    baPos.value = Math.min(100, baPos.value + 4)
    e.preventDefault()
  }
}
function syncBaWidth(): void {
  const el = baRef.value
  if (el) baStageWidthPx.value = `${el.getBoundingClientRect().width}px`
}

let cleanup: Array<() => void> = []

onMounted((): void => {
  if (!import.meta.client) return

  syncBaWidth()
  const onResize = (): void => syncBaWidth()
  window.addEventListener('resize', onResize)
  window.addEventListener('pointermove', baMove)
  window.addEventListener('pointerup', baUp)
  cleanup.push(() => window.removeEventListener('resize', onResize))
  cleanup.push(() => window.removeEventListener('pointermove', baMove))
  cleanup.push(() => window.removeEventListener('pointerup', baUp))
})

onBeforeUnmount((): void => {
  cleanup.forEach((fn) => fn())
  cleanup = []
})
</script>

<style scoped>
/* ════════════ Avant / après ════════════ */
.ba {
  padding: clamp(3rem, 6vw, 5rem) 0;
  background: var(--mist);
  border-top: 1px solid var(--hair);
  border-bottom: 1px solid var(--hair);
}
.ba-wrap {
  max-width: 1100px;
  margin: clamp(2rem, 4vw, 3rem) auto 0;
  padding: 0 1.5rem;
}
.ba-stage {
  position: relative;
  border-radius: 18px;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  cursor: ew-resize;
  user-select: none;
  touch-action: none;
  box-shadow: 0 30px 60px -34px color-mix(in srgb, var(--ink) 55%, transparent);
}
.ba-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.ba-before {
  position: absolute;
  inset: 0;
  width: 58%;
  overflow: hidden;
  border-right: 3px solid #fff;
}
.ba-img-before {
  max-width: none;
  height: 100%;
  /* rendu "ancien" pour le côté avant — remplaçable par une vraie photo avant */
  filter: grayscale(0.62) sepia(0.28) brightness(0.82) contrast(0.95);
}
.ba-tag {
  position: absolute;
  top: 0.9rem;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 0.32rem 0.7rem;
  border-radius: 999px;
  color: #fff;
}
.ba-tag-before {
  right: 0.9rem;
  background: color-mix(in srgb, var(--ink) 78%, transparent);
}
.ba-tag-after {
  right: 0.9rem;
  background: var(--brand);
  top: auto;
  bottom: 0.9rem;
}
.ba-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 44px;
  margin-left: -22px;
  background: transparent;
  border: 0;
  cursor: ew-resize;
  display: grid;
  place-items: center;
  padding: 0;
}
.ba-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 3px;
  margin-left: -1.5px;
  background: #fff;
}
.ba-handle svg {
  position: relative;
  width: 38px;
  height: 38px;
  padding: 8px;
  border-radius: 50%;
  background: #fff;
  color: var(--ink);
  box-shadow: 0 4px 14px -2px color-mix(in srgb, var(--ink) 55%, transparent);
  stroke-width: 2;
}
.ba-handle:focus-visible {
  outline: none;
}
.ba-handle:focus-visible svg {
  box-shadow: 0 0 0 3px var(--signal);
}
.ba-caption {
  margin-top: 1.1rem;
  text-align: center;
  color: var(--ink-soft);
  font-size: 0.95rem;
}
</style>
