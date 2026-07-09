<template>
  <div class="mb-10">
    <div class="flex items-center justify-between gap-4">
      <div v-for="(step, index) in steps" :key="step.id" class="flex flex-1 items-center">
        <div class="flex flex-col items-center gap-2">
          <div
            :class="[
              'flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-all duration-300',
              currentStep > step.id
                ? 'bg-[var(--app-green)] text-white'
                : currentStep === step.id
                  ? 'bg-[var(--app-ink)] text-[var(--app-bg)] shadow-lg shadow-white/10'
                  : 'border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)]',
            ]"
          >
            <i v-if="currentStep > step.id" class="fa-solid fa-check text-xs"></i>
            <span v-else>{{ step.id }}</span>
          </div>
          <span
            :class="[
              'hidden text-center text-xs font-medium sm:block',
              currentStep >= step.id ? 'text-[var(--app-ink)]' : 'text-[var(--app-ink-soft)]',
            ]"
          >
            {{ step.label }}
          </span>
        </div>
        <div
          v-if="index < steps.length - 1"
          :class="[
            'mx-2 hidden h-0.5 flex-1 rounded-full transition-colors duration-500 sm:block',
            currentStep > step.id ? 'bg-[var(--app-green)]' : 'bg-[var(--app-surface-2)]',
          ]"
        ></div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
defineProps<{
  steps: Array<{ id: number; label: string }>
  currentStep: number
}>()
</script>
