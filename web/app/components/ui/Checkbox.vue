<template>
  <label class="group flex cursor-pointer items-center">
    <div class="relative">
      <input
        :id="id"
        type="checkbox"
        :checked="modelValue"
        class="peer sr-only"
        @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
      />
      <div
        class="h-4 w-4 rounded border border-[#30363d] bg-[#050505] transition-all group-hover:border-[#8b949e] peer-checked:border-[#f9f9f9] peer-checked:bg-[#f9f9f9]"
      >
        <svg
          v-if="modelValue"
          class="absolute left-0.5 top-0.5 h-3 w-3 text-[#050505]"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    </div>
    <span v-if="label" class="text-muted ml-2 select-none text-xs transition-colors group-hover:text-[#f9f9f9]">
      {{ label }}
    </span>
  </label>
</template>

<script setup lang="ts">
defineProps<{
  id?: string
  modelValue: boolean
  label?: string
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>
