<template>
  <LandingLegalDocument document-id="privacy" title-key="legal.privacy.title" intro-key="legal.privacy.intro">
    <LandingLegalSection title-key="legal.privacy.controller.title">
      <p>
        {{
          $t('legal.privacy.controller.body', {
            name: PUBLISHER_LEGAL_IDENTITY.fullName,
            address: PUBLISHER_LEGAL_IDENTITY.address,
            email: PUBLISHER_CONTACT.email,
          })
        }}
      </p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.collected.title">
      <LandingLegalList base-key="legal.privacy.collected" :item-keys="COLLECTED_DATA_KEYS" />
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.analytics.title">
      <p>{{ $t('legal.privacy.analytics.body') }}</p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.purposes.title">
      <LandingLegalList base-key="legal.privacy.purposes" :item-keys="PURPOSE_KEYS" is-term-after-text />
      <p>{{ $t('legal.privacy.purposes.noSale') }}</p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.recipients.title">
      <p>{{ $t('legal.privacy.recipients.intro') }}</p>
      <LandingLegalList base-key="legal.privacy.recipients" :item-keys="RECIPIENT_KEYS" />
      <p>{{ $t('legal.privacy.recipients.transfers') }}</p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.retention.title">
      <LandingLegalList base-key="legal.privacy.retention" :item-keys="RETENTION_KEYS" />
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.rights.title">
      <p>{{ $t('legal.privacy.rights.body', { email: PUBLISHER_CONTACT.email }) }}</p>
      <p>{{ $t('legal.privacy.rights.complaint') }}</p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.privacy.cookies.title">
      <p>{{ $t('legal.privacy.cookies.body') }}</p>
    </LandingLegalSection>
  </LandingLegalDocument>
</template>

<script lang="ts" setup>
import { PUBLISHER_CONTACT, PUBLISHER_LEGAL_IDENTITY } from '~/constants/publisher'

/**
 * Privacy policy page — light editorial layout on the marketing theme.
 */
definePageMeta({
  layout: 'marketing',
})

const { t }: { t: (key: string, params?: Record<string, unknown>) => string } = useI18n()

const COLLECTED_DATA_KEYS: string[] = ['account', 'usage', 'payment', 'contactForm']
const PURPOSE_KEYS: string[] = ['contract', 'legalObligation', 'legitimateInterest', 'consent']
const RECIPIENT_KEYS: string[] = ['hosting', 'payment', 'emails', 'audience']
const RETENTION_KEYS: string[] = ['account', 'messages', 'invoices']

useHead(() => ({
  title: `${t('legal.privacy.title')} — DevLeadHunter`,
  meta: [{ name: 'description', content: t('legal.privacy.intro') }],
}))
</script>
