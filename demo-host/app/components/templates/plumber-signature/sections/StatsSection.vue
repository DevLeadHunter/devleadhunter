<template>
  <section class="stats">
    <div
      v-for="(s, i) in trustItems"
      :key="i"
      class="stat reveal"
      data-reveal
      :style="{ '--d': `${i * 70}ms` }"
    >
      <span class="stat-val">{{ s.value }}</span>
      <span class="stat-label">{{ s.label }}</span>
    </div>
  </section>
</template>

<script lang="ts" setup>
defineProps<{
  trustItems: { value?: string; label?: string }[]
}>()
</script>

<style scoped>
/* ════════════ Stats ════════════ */
.stats {
  width: min(1180px, 100% - 3rem);
  margin: clamp(2.5rem, 5vw, 3.5rem) auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1px;
  background: var(--hair);
  border: 1px solid var(--hair);
  border-radius: 18px;
  overflow: hidden;
}
.stat {
  background: var(--paper);
  padding: 1.7rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  align-items: center;
  text-align: center;
}
.stat-val {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700;
  font-size: clamp(1.9rem, 3.4vw, 2.7rem);
  line-height: 1;
  letter-spacing: -0.03em;
  color: var(--brand);
  font-variant-numeric: tabular-nums;
}
.stat-label {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}
</style>
