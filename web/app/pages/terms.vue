<template>
  <LandingLegalDocument document-id="terms" title-key="legal.terms.title" intro-key="legal.terms.intro">
    <LandingLegalSection title-key="legal.terms.publisher.title">
      <I18nT keypath="legal.terms.publisher.body" tag="p" scope="global">
        <template #name>{{ PUBLISHER_LEGAL_IDENTITY.fullName }}</template>
        <template #siret>{{ PUBLISHER_LEGAL_IDENTITY.siret }}</template>
        <template #address>{{ PUBLISHER_LEGAL_IDENTITY.address }}</template>
        <template #email>{{ PUBLISHER_CONTACT.email }}</template>
        <template #phone>{{ $t('publisher.phone') }}</template>
        <template #noticeLink>
          <NuxtLink :to="localePath('/legal')" class="landing-link">{{
            $t('legal.terms.publisher.noticeLink')
          }}</NuxtLink>
        </template>
      </I18nT>
    </LandingLegalSection>

    <LandingLegalSection
      v-for="sectionKey in SECTION_KEYS"
      :key="sectionKey"
      :title-key="`legal.terms.${sectionKey}.title`"
    >
      <p>{{ $t(`legal.terms.${sectionKey}.body`) }}</p>
    </LandingLegalSection>
  </LandingLegalDocument>
</template>

<script lang="ts" setup>
import { PUBLISHER_CONTACT, PUBLISHER_LEGAL_IDENTITY } from '~/constants/publisher'

/**
 * Terms of service page — light editorial layout on the marketing theme.
 */
definePageMeta({
  layout: 'marketing',
})

const { t }: { t: (key: string, params?: Record<string, unknown>) => string } = useI18n()
const localePath: ReturnType<typeof useLocalePath> = useLocalePath()

const SECTION_KEYS: string[] = ['service', 'account', 'credits', 'use', 'liability', 'termination', 'law']

useHead(() => ({
  title: `${t('legal.terms.title')} — DevLeadHunter`,
  meta: [{ name: 'description', content: t('legal.terms.intro') }],
}))
</script>
