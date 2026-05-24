<template>
  <div>
    <header class="bg-sky-700 px-6 py-16 text-white">
      <div class="mx-auto max-w-3xl">
        <p class="text-sm uppercase tracking-wide text-sky-100">Demo website</p>
        <h1 class="mt-2 text-4xl font-bold">{{ hero.title || businessName }}</h1>
        <p class="mt-4 text-lg text-sky-50">{{ hero.subtitle }}</p>
        <a
          v-if="hero.phone"
          :href="`tel:${hero.phone}`"
          class="mt-6 inline-block rounded bg-white px-5 py-3 font-semibold text-sky-800"
        >
          {{ hero.cta_label || 'Call now' }} — {{ hero.phone }}
        </a>
      </div>
    </header>

    <section class="mx-auto max-w-3xl px-6 py-12">
      <h2 class="text-2xl font-semibold">{{ services.heading || 'Our services' }}</h2>
      <ul class="mt-4 space-y-2">
        <li v-for="(item, index) in serviceItems" :key="index" class="rounded border border-slate-200 px-4 py-3">
          {{ item.label }}
        </li>
      </ul>
    </section>

    <section class="bg-slate-50 px-6 py-12">
      <div class="mx-auto max-w-3xl">
        <h2 class="text-2xl font-semibold">{{ contact.heading || 'Contact us' }}</h2>
        <dl class="mt-4 space-y-2 text-slate-700">
          <div v-if="contact.phone"><dt class="inline font-medium">Phone: </dt><dd class="inline">{{ contact.phone }}</dd></div>
          <div v-if="contact.email"><dt class="inline font-medium">Email: </dt><dd class="inline">{{ contact.email }}</dd></div>
          <div v-if="contact.city"><dt class="inline font-medium">City: </dt><dd class="inline">{{ contact.city }}</dd></div>
        </dl>
      </div>
    </section>

    <footer class="px-6 py-6 text-center text-xs text-slate-500">
      Powered by DevLeadHunter · Demo expires automatically after 14 days
    </footer>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'

const props = defineProps<{
  content: Record<string, unknown>
  businessName: string
}>()

type Block = Record<string, unknown>

const blocks: ComputedRef<Block[]> = computed((): Block[] => {
  const body = props.content.body
  return Array.isArray(body) ? (body as Block[]) : []
})

const hero: ComputedRef<Block> = computed((): Block => {
  return blocks.value.find((b: Block): boolean => b.component === 'hero') ?? {}
})

const services: ComputedRef<Block> = computed((): Block => {
  return blocks.value.find((b: Block): boolean => b.component === 'services') ?? {}
})

const contact: ComputedRef<Block> = computed((): Block => {
  return blocks.value.find((b: Block): boolean => b.component === 'contact') ?? {}
})

const serviceItems: ComputedRef<Array<{ label?: string }>> = computed((): Array<{ label?: string }> => {
  const items = services.value.items
  return Array.isArray(items) ? (items as Array<{ label?: string }>) : []
})
</script>
