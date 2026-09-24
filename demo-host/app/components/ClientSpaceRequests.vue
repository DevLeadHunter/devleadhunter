<template>
  <section class="cs-section">
    <header class="cs-section__head">
      <h2 class="cs-section__title">Demandes</h2>
      <span class="cs-section__meta">{{ pendingLabel }}</span>
    </header>
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
          <span class="csr__type" :class="{ 'csr__type--urgent': item.type === 'urgent' }">
            {{ TYPE_LABELS[item.type] }}
          </span>
          <span v-if="item.received_outside_hours" class="csr__flag">hors horaires</span>
          <span class="csr__date">{{ item.received_label }}</span>
        </div>
        <p class="csr__who">
          <strong>{{ item.name }}</strong>
          <span aria-hidden="true"> · </span>
          <a v-if="contactHref(item.contact)" :href="contactHref(item.contact) ?? undefined" class="csr__contact">
            {{ item.contact }}
          </a>
          <span v-else>{{ item.contact }}</span>
        </p>
        <p v-if="item.summary" class="csr__summary">{{ item.summary }}</p>
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
            v-if="item.status === 'new'"
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
  </section>
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

const EMAIL_PATTERN: RegExp = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const PHONE_PATTERN: RegExp = /^\+?[\d\s.()-]{6,}$/

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
})

const emit: EmitFn<ClientSpaceRequestsEmits> = defineEmits<ClientSpaceRequestsEmits>()

const pendingLabel: ComputedRef<string> = computed((): string => {
  if (props.pendingCount === 0) return 'Tout est traité'
  return props.pendingCount === 1 ? '1 à traiter' : `${props.pendingCount} à traiter`
})

/**
 * A tap-to-call or tap-to-mail link for a visitor's contact, when it reads as one.
 * @param contact The contact the visitor left.
 * @returns The `tel:` / `mailto:` href, or null for anything else.
 */
function contactHref(contact: string): string | null {
  const cleaned: string = contact.trim()
  if (EMAIL_PATTERN.test(cleaned)) return `mailto:${cleaned}`
  if (PHONE_PATTERN.test(cleaned)) return `tel:${cleaned.replace(/[^\d+]/g, '')}`
  return null
}
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

.csr__type {
  border-radius: 999px;
  padding: 2px 10px;
  font-weight: 600;
  color: var(--cs-ink);
  background: color-mix(in srgb, var(--a-accent) 16%, #fff);
}

.csr__type--urgent {
  color: #fff;
  background: #9f3a2f;
}

.csr__flag {
  border: 1px solid var(--cs-line);
  border-radius: 999px;
  padding: 1px 8px;
  color: var(--cs-ink-dim);
}

.csr__date {
  margin-left: auto;
  color: var(--cs-ink-dim);
}

.csr__who {
  margin: 10px 0 0;
  font-size: 15px;
}

.csr__contact {
  color: var(--cs-ink);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.csr__summary {
  margin: 6px 0 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--cs-ink-dim);
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
