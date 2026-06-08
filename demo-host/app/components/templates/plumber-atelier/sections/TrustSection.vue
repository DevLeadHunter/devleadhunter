<template>
  <section class="ledger">
    <div
      v-for="(item, i) in items"
      :key="i"
      class="ledger-cell reveal"
      data-reveal
      :style="{ '--d': `${i * 80}ms` }"
    >
      <span class="ledger-value">{{ item.value }}</span>
      <span class="ledger-label">{{ item.label }}</span>
    </div>
  </section>
</template>

<script lang="ts" setup>
defineProps<{
  items: Array<{ value?: string; label?: string }>
}>()
</script>

<style scoped>
.ledger {
  max-width: 1200px;
  margin: clamp(1.5rem, 4vw, 3rem) auto 0;
  padding: 0 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  border-top: 1px solid var(--ink);
  border-bottom: 1px solid var(--ink);
}
.ledger-cell {
  padding: 1.6rem 1.4rem;
  border-left: 1px solid var(--hair);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.ledger-cell:first-child {
  border-left: 0;
}
.ledger-value {
  font-family: 'Fraunces', serif;
  font-weight: 600;
  font-size: clamp(2rem, 3.5vw, 2.8rem);
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--brass);
  font-variant-numeric: tabular-nums;
}
.ledger-label {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ink-soft);
}
</style>
