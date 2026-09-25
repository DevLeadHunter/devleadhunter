<template>
  <div
    class="listing"
    role="img"
    :aria-label="`Votre fiche Google Maps, avec les boutons Site web et Prendre rendez-vous qui ouvrent ${props.assistantName}`"
  >
    <div class="listing__top">
      <div>
        <div class="listing__name">{{ props.businessName }}</div>
        <div class="listing__meta">
          <b v-if="props.ratingLabel">{{ props.ratingLabel }}</b>
          <template v-if="props.ratingLabel"> · </template>{{ props.tradeLabel
          }}<template v-if="props.city"> · {{ props.city }}</template>
        </div>
      </div>
      <span class="listing__closed">Fermé ce soir</span>
    </div>
    <div class="listing__actions">
      <span class="listing__btn">Itinéraire</span>
      <span class="listing__btn">Appeler</span>
      <span class="listing__btn listing__btn--assistant"
        >Site web <small>→ {{ props.assistantName }}</small></span
      >
      <span class="listing__btn listing__btn--assistant">
        Prendre rendez-vous <small>→ {{ props.assistantName }}</small>
      </span>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { AssistantDemoGoogleListingProps } from '~/types/AssistantDemoGoogleListing'

const props: AssistantDemoGoogleListingProps = defineProps({
  businessName: {
    type: String,
    required: true,
  },
  ratingLabel: {
    type: String,
    default: '',
  },
  tradeLabel: {
    type: String,
    required: true,
  },
  city: {
    type: String,
    default: '',
  },
  assistantName: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.listing {
  border: 1px solid var(--ia-line);
  border-radius: 16px;
  background: var(--ia-card);
  padding: 16px 18px;
  display: grid;
  gap: 12px;
  box-shadow: 0 18px 40px -30px rgba(23, 19, 13, 0.4);
}
.listing__top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.listing__name {
  font-family: var(--ia-font-d);
  font-weight: 600;
  font-size: 20px;
  line-height: 1.1;
}
.listing__meta {
  font-size: 13px;
  color: var(--ia-ink-dim);
  margin-top: 3px;
}
.listing__meta b {
  color: #c98a1a;
  font-weight: 600;
}
.listing__closed {
  font-size: 12.5px;
  color: var(--ia-urgent);
  white-space: nowrap;
}
.listing__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.listing__btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 13px;
  border-radius: 999px;
  border: 1px solid var(--ia-line);
  font-size: 13px;
  font-weight: 500;
  color: var(--ia-ink);
  background: var(--ia-paper-2);
}
.listing__btn--assistant {
  border-color: var(--a-accent);
  color: var(--a-accent-text);
  background: color-mix(in srgb, var(--a-accent) 10%, var(--ia-card));
}
.listing__btn--assistant small {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
}
</style>
