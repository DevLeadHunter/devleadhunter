<template>
  <strong>{{ name }}</strong>
  <span aria-hidden="true"> · </span>
  <a v-if="href" :href="href" class="cs-contact__link">{{ contact }}</a>
  <span v-else>{{ contact }}</span>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import { computed } from 'vue'
import type { ClientSpaceContactProps } from '~/types/ClientSpaceContact'
import { ContactLinkUtils } from '~/utils/ContactLinkUtils'

/**
 * A visitor's name and contact, the contact as a tap-to-call or tap-to-mail link when it reads as one.
 * Rendered without a wrapper: the parent's element lays it out.
 * @param name The visitor's name.
 * @param contact The phone or email the visitor left.
 */
const props: ClientSpaceContactProps = defineProps({
  name: { type: String, required: true },
  contact: { type: String, required: true },
})

const href: ComputedRef<string | null> = computed((): string | null => ContactLinkUtils.href(props.contact))
</script>

<style scoped>
.cs-contact__link {
  color: var(--cs-ink);
  text-decoration: underline;
  text-underline-offset: 3px;
}
</style>
