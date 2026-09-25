<template>
  <ClientSpaceSection title="Demandes" :meta="pendingLabel">
    <p v-if="requests.length === 0" class="cs-muted">
      Aucune demande pour l’instant : elles arrivent ici dès qu’un visiteur laisse ses coordonnées.
    </p>
    <ul v-else class="csr__list">
      <li
        v-for="item in requests"
        :key="item.id"
        class="csr__item"
        :class="{ 'csr__item--done': item.status !== 'new' }"
      >
        <div class="csr__top">
          <ClientSpaceBadge :tone="item.type === 'urgent' ? 'danger' : 'accent'">
            {{ TYPE_LABELS[item.type] }}
          </ClientSpaceBadge>
          <ClientSpaceBadge v-if="item.received_outside_hours" tone="outline">hors horaires</ClientSpaceBadge>
          <span class="csr__date">{{ item.received_label }}</span>
        </div>
        <p class="csr__who">
          <ClientSpaceContact :name="item.name" :contact="item.contact" />
        </p>
        <p v-if="item.summary" class="csr__summary">{{ item.summary }}</p>
        <p v-if="item.appointment_booked" class="csr__slots">
          Rendez-vous réservé dans votre agenda : <strong>{{ item.appointment_booked }}</strong>
        </p>
        <p v-else-if="item.appointment_slots.length > 0" class="csr__slots">
          Créneaux souhaités, à confirmer : <strong>{{ item.appointment_slots.join(' ou ') }}</strong>
        </p>
        <div v-if="item.photo_urls.length > 0" class="csr__photos">
          <a
            v-for="(url, index) in item.photo_urls"
            :key="url"
            :href="url"
            target="_blank"
            rel="noopener noreferrer"
            referrerpolicy="no-referrer"
            class="csr__photo"
          >
            <img :src="url" :alt="`Photo ${index + 1}`" loading="lazy" referrerpolicy="no-referrer" />
          </a>
        </div>
        <div class="csr__actions">
          <button
            v-if="item.status === 'new' && !props.readOnly"
            type="button"
            class="cs-button cs-button--outline"
            :disabled="busyRequestId === item.id"
            @click="emit('handled', item.id)"
          >
            {{ busyRequestId === item.id ? 'Un instant…' : 'Marquer traitée' }}
          </button>
          <span v-else class="csr__status">{{ STATUS_LABELS[item.status] }}</span>
        </div>
      </li>
    </ul>
  </ClientSpaceSection>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import { computed } from 'vue'
import type {
  AiAssistantClientRequest,
  AiAssistantClientRequestStatus,
  AiAssistantClientRequestType,
} from '~/types/AiAssistantClientSpace'
import type { ClientSpaceRequestsEmits, ClientSpaceRequestsProps } from '~/types/ClientSpaceRequests'

const TYPE_LABELS: Record<AiAssistantClientRequestType, string> = {
  question: 'Question',
  quote: 'Devis',
  appointment: 'Rendez-vous',
  urgent: 'Urgence',
  other: 'Demande',
}

const STATUS_LABELS: Record<AiAssistantClientRequestStatus, string> = {
  new: 'À traiter',
  handled: 'Traitée',
  dropped: 'Sans suite',
}

/**
 * The requests of the client's assistant, newest first, each with its contact and a « traitée » button.
 * @param requests The latest requests (tests excluded), newest first.
 * @param pendingCount How many requests still wait, over the whole history.
 * @param busyRequestId The request being marked handled, if any.
 */
const props: ClientSpaceRequestsProps = defineProps({
  requests: { type: Array as PropType<AiAssistantClientRequest[]>, required: true },
  pendingCount: { type: Number, required: true },
  busyRequestId: { type: Number as PropType<number | null>, default: null },
  readOnly: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<ClientSpaceRequestsEmits> = defineEmits<ClientSpaceRequestsEmits>()

const pendingLabel: ComputedRef<string> = computed((): string => {
  if (props.pendingCount === 0) return 'Tout est traité'
  return props.pendingCount === 1 ? '1 à traiter' : `${props.pendingCount} à traiter`
})
</script>

<style scoped>
.csr__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.csr__item {
  border: 1px solid var(--cs-line);
  border-radius: 14px;
  background: var(--cs-card);
  padding: 14px 16px;
}

.csr__item--done {
  opacity: 0.72;
}

.csr__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.csr__date {
  margin-left: auto;
  color: var(--cs-ink-dim);
}

.csr__who {
  margin: 10px 0 0;
  font-size: 15px;
}

.csr__summary {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--cs-ink-dim);
}

.csr__slots {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--cs-ink);
}

.csr__photos {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.csr__photo img {
  display: block;
  width: 72px;
  height: 72px;
  border-radius: 10px;
  object-fit: cover;
  border: 1px solid var(--cs-line);
}

.csr__actions {
  margin-top: 12px;
}

.csr__status {
  font-size: 13px;
  font-weight: 500;
  color: var(--cs-ink-dim);
}
</style>
