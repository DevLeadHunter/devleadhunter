<template>
  <section id="contact" class="bg-white px-6 py-20">
    <div class="mx-auto max-w-6xl">
      <div class="overflow-hidden rounded-3xl shadow-2xl" :style="{ background: contactGradient }">
        <div class="grid md:grid-cols-2">
          <div class="p-10 text-white md:p-14">
            <h2 class="text-3xl font-bold">{{ contact.heading || 'Contactez-nous' }}</h2>
            <p v-if="contact.subheading" class="mt-4 text-white/80">{{ contact.subheading }}</p>
            <dl class="mt-8 space-y-4">
              <div v-if="contact.phone" class="flex items-center gap-3">
                <span class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">📞</span>
                <div>
                  <dt class="text-xs uppercase tracking-wide text-white/60">Téléphone</dt>
                  <dd class="font-semibold">{{ contact.phone }}</dd>
                </div>
              </div>
              <div v-if="contact.email" class="flex items-center gap-3">
                <span class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">✉️</span>
                <div>
                  <dt class="text-xs uppercase tracking-wide text-white/60">Email</dt>
                  <dd class="font-semibold">{{ contact.email }}</dd>
                </div>
              </div>
              <div v-if="contact.city" class="flex items-center gap-3">
                <span class="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">📍</span>
                <div>
                  <dt class="text-xs uppercase tracking-wide text-white/60">Zone</dt>
                  <dd class="font-semibold">{{ contact.city }}</dd>
                </div>
              </div>
            </dl>
          </div>
          <div class="flex flex-col justify-center bg-white p-10 md:p-14">
            <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Devis gratuit</p>
            <p class="mt-2 text-2xl font-bold text-slate-900">Réponse sous 2 heures</p>
            <p class="mt-4 text-slate-600">Décrivez votre besoin — nous vous rappelons rapidement avec un devis transparent.</p>
            <a
              v-if="contact.phone"
              :href="`tel:${contact.phone}`"
              class="mt-8 inline-flex w-fit items-center justify-center rounded-xl px-8 py-4 font-bold text-white transition hover:scale-[1.02]"
              :style="{ backgroundColor: theme.primary }"
            >
              Appeler maintenant
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ContactBlock, Theme } from '../types'

const props = defineProps<{
  contact: ContactBlock
  theme: Theme
}>()

const contactGradient = computed(() =>
  `linear-gradient(135deg, ${props.theme.primary} 0%, ${props.theme.secondary} 100%)`,
)
</script>
