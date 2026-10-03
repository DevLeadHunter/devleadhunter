<template>
  <div
    role="img"
    :aria-label="props.label"
    class="flex gap-[3px]"
    :class="props.isWrapping ? 'flex-wrap' : 'flex-nowrap'"
    @pointerleave="hoveredUnit = null"
  >
    <span
      v-for="(unit, index) in props.units"
      :key="unit.key"
      aria-hidden="true"
      class="shrink-0 cursor-pointer rounded-[3px] transition-opacity duration-150"
      :class="[
        UNIT_CHART_TONE_CLASSES[unit.tone],
        hoveredUnit && hoveredUnit.key !== unit.key ? 'opacity-50' : 'opacity-100',
        index > 0 && unit.group !== props.units[index - 1]?.group ? 'ml-[5px]' : '',
      ]"
      :style="{ width: `${props.unitSize}px`, height: `${props.unitSize}px` }"
      @pointermove="showUnit(unit, $event)"
      @click="emit('select', unit.key)"
    ></span>

    <UiPointerTooltip :is-open="hoveredUnit !== null" :pointer-x="pointerX" :pointer-y="pointerY">
      <template v-if="hoveredUnit">
        <p class="font-medium text-[var(--app-ink)]">{{ hoveredUnit.title }}</p>
        <p v-for="detail in hoveredUnit.details" :key="detail">{{ detail }}</p>
      </template>
    </UiPointerTooltip>
  </div>
</template>

<script lang="ts" setup>
import type { EmitFn, PropType, Ref } from 'vue'
import type { UiUnitChartEmits, UiUnitChartProps, UiUnitChartUnit } from '~/types/UiUnitChart'
import { ref } from 'vue'
import { UNIT_CHART_TONE_CLASSES } from '~/constants/unitChartTones'

const props: UiUnitChartProps = defineProps({
  units: {
    type: Array as PropType<UiUnitChartUnit[]>,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  unitSize: {
    type: Number,
    default: 16,
  },
  isWrapping: {
    type: Boolean,
    default: true,
  },
})

const emit: EmitFn<UiUnitChartEmits> = defineEmits<UiUnitChartEmits>()

const hoveredUnit: Ref<UiUnitChartUnit | null> = ref(null)
const pointerX: Ref<number> = ref(0)
const pointerY: Ref<number> = ref(0)

/**
 * Show a unit's tooltip under a mouse; a finger opens the unit instead.
 * @param unit - The unit under the pointer.
 * @param event - The pointer move.
 */
function showUnit(unit: UiUnitChartUnit, event: PointerEvent): void {
  if (event.pointerType !== 'mouse') return
  hoveredUnit.value = unit
  pointerX.value = event.clientX
  pointerY.value = event.clientY
}
</script>
