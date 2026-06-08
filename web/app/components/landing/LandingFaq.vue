<template>
  <section id="faq" class="scroll-mt-20 bg-[#0d1117] py-24 md:py-32">
    <div class="container mx-auto px-4 md:px-6 lg:px-8">
      <div class="mx-auto max-w-3xl">
        <div class="mb-14 text-center">
          <h2 v-reveal class="mb-5 text-3xl font-bold tracking-tight text-[#f9f9f9] md:text-4xl">
            {{ $t('pricing.faq.title') }}
          </h2>
        </div>

        <div class="space-y-3">
          <div
            v-for="(faq, index) in faqs"
            :key="index"
            v-reveal="{ delay: index * 40 }"
            class="overflow-hidden rounded-2xl border border-[#30363d] bg-[#161b22] transition-colors hover:border-[#484f58]"
          >
            <button
              type="button"
              class="flex w-full cursor-pointer items-center justify-between gap-4 px-6 py-5 text-left"
              :aria-expanded="openFaqs.has(index)"
              @click="toggleFaq(index)"
            >
              <span class="text-base font-semibold text-[#f9f9f9] md:text-lg">{{ faq.question }}</span>
              <span
                class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#21262d] transition-transform duration-300"
                :class="openFaqs.has(index) ? 'rotate-180' : ''"
              >
                <i class="fa-solid fa-chevron-down text-xs text-[#8b949e]"></i>
              </span>
            </button>
            <Transition @enter="onEnter" @after-enter="onAfterEnter" @before-leave="onBeforeLeave" @leave="onLeave">
              <div v-show="openFaqs.has(index)" class="overflow-hidden">
                <p class="px-6 pb-5 text-[15px] leading-relaxed text-[#8b949e]">{{ faq.answer }}</p>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'

/** A single FAQ entry. */
interface FaqItem {
  question: string
  answer: string
}

const { t } = useI18n()

/** Indices of currently expanded FAQ items (first one open by default). */
const openFaqs: Ref<Set<number>> = ref<Set<number>>(new Set<number>([0]))

/**
 * The FAQ entries, sourced from i18n.
 */
const faqs: ComputedRef<FaqItem[]> = computed((): FaqItem[] => [
  { question: t('pricing.faq.q1'), answer: t('pricing.faq.a1') },
  { question: t('pricing.faq.q2'), answer: t('pricing.faq.a2') },
  { question: t('pricing.faq.q3'), answer: t('pricing.faq.a3') },
  { question: t('pricing.faq.q4'), answer: t('pricing.faq.a4') },
  { question: t('pricing.faq.q5'), answer: t('pricing.faq.a5') },
  { question: t('pricing.faq.q6'), answer: t('pricing.faq.a6') },
])

/**
 * Toggle a FAQ item open/closed.
 * @param index - Index of the FAQ item to toggle.
 */
function toggleFaq(index: number): void {
  if (openFaqs.value.has(index)) {
    openFaqs.value.delete(index)
  } else {
    openFaqs.value.add(index)
  }
  // Reassign to trigger reactivity on the Set.
  openFaqs.value = new Set<number>(openFaqs.value)
}

/**
 * Expand transition: animate height from 0 to content height.
 * @param el - The transitioning element.
 */
function onEnter(el: Element): void {
  const node: HTMLElement = el as HTMLElement
  node.style.height = '0'
  void node.offsetHeight
  node.style.transition = 'height 0.3s ease'
  node.style.height = `${node.scrollHeight}px`
}

/**
 * Clean up inline styles after the expand transition.
 * @param el - The transitioning element.
 */
function onAfterEnter(el: Element): void {
  const node: HTMLElement = el as HTMLElement
  node.style.height = ''
  node.style.transition = ''
}

/**
 * Collapse transition: fix the current height before animating to 0.
 * @param el - The transitioning element.
 */
function onBeforeLeave(el: Element): void {
  const node: HTMLElement = el as HTMLElement
  node.style.height = `${node.scrollHeight}px`
}

/**
 * Collapse transition: animate height to 0.
 * @param el - The transitioning element.
 */
function onLeave(el: Element): void {
  const node: HTMLElement = el as HTMLElement
  void node.offsetHeight
  node.style.transition = 'height 0.3s ease'
  node.style.height = '0'
}
</script>
