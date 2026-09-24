<template>
  <ClientSpaceSection title="Prochains rendez-vous" :meta="countLabel">
    <ul class="csa__list">
      <li v-for="item in appointments" :key="item.id" class="csa__item">
        <span class="csa__when">{{ item.start_label }}</span>
        <span class="csa__who">
          <ClientSpaceContact :name="item.name" :contact="item.contact" />
        </span>
        <ClientSpaceBadge v-if="item.type_label" class="csa__kind">{{ item.type_label }}</ClientSpaceBadge>
      </li>
    </ul>
  </ClientSpaceSection>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import { computed } from 'vue'
import type { AiAssistantClientAppointment } from '~/types/AiAssistantClientSpace'
import type { ClientSpaceAppointmentsProps } from '~/types/ClientSpaceAppointments'

/**
 * The next appointments the assistant booked in the client's agenda, soonest first.
 * @param appointments The upcoming appointments (tests excluded).
 */
const props: ClientSpaceAppointmentsProps = defineProps({
  appointments: { type: Array as PropType<AiAssistantClientAppointment[]>, required: true },
})

const countLabel: ComputedRef<string> = computed((): string =>
  props.appointments.length === 1 ? '1 à venir' : `${props.appointments.length} à venir`,
)
</script>

<style scoped>
.csa__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.csa__item {
  display: grid;
  gap: 4px;
  border: 1px solid var(--cs-line);
  border-radius: 14px;
  background: var(--cs-card);
  padding: 12px 16px;
  font-size: 14px;
}

.csa__when {
  font-weight: 600;
}

.csa__kind {
  justify-self: start;
}
</style>
