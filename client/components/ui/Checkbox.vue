<template>
  <label class="flex items-center cursor-pointer group">
    <div class="relative">
      <input
        :id="id"
        type="checkbox"
        :checked="modelValue"
        @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
        class="sr-only peer"
      />
      <div
        class="w-4 h-4 bg-[#050505] border border-[#30363d] rounded peer-checked:bg-[#f9f9f9] peer-checked:border-[#f9f9f9] transition-all group-hover:border-[#8b949e]"
      >
        <svg
          v-if="modelValue"
          class="w-3 h-3 text-[#050505] absolute top-0.5 left-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="3"
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>
    </div>
    <span v-if="label" class="ml-2 text-xs text-muted group-hover:text-[#f9f9f9] transition-colors select-none">
      {{ label }}
    </span>
  </label>
</template>

<script setup lang="ts">
defineProps<{
  id?: string;
  modelValue: boolean;
  label?: string;
}>();

defineEmits<{
  'update:modelValue': [value: boolean];
}>();
</script>

