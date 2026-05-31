<template>
  <div class="mb-10">
    <div class="flex items-center justify-between gap-4">
      <div v-for="(step, index) in steps" :key="step.id" class="flex flex-1 items-center">
        <div class="flex flex-col items-center gap-2">
          <div
            :class="[
              'flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-all duration-300',
              currentStep > step.id
                ? 'bg-[#2BAD5F] text-white'
                : currentStep === step.id
                  ? 'bg-[#f9f9f9] text-[#050505] shadow-lg shadow-white/10'
                  : 'border border-[#30363d] bg-[#1a1a1a] text-[#8b949e]',
            ]"
          >
            <i v-if="currentStep > step.id" class="fa-solid fa-check text-xs"></i>
            <span v-else>{{ step.id }}</span>
          </div>
          <span
            :class="[
              'hidden text-center text-xs font-medium sm:block',
              currentStep >= step.id ? 'text-[#f9f9f9]' : 'text-[#8b949e]',
            ]"
          >
            {{ step.label }}
          </span>
        </div>
        <div
          v-if="index < steps.length - 1"
          :class="[
            'mx-2 hidden h-0.5 flex-1 rounded-full transition-colors duration-500 sm:block',
            currentStep > step.id ? 'bg-[#2BAD5F]' : 'bg-[#30363d]',
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
