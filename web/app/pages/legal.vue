<template>
  <LandingLegalDocument document-id="notice" title-key="legal.notice.title" intro-key="legal.notice.intro">
    <LandingLegalSection title-key="legal.notice.publisher.title">
      <LandingLegalDetails :rows="publisherRows" />
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.notice.director.title">
      <p>{{ PUBLISHER_LEGAL_IDENTITY.fullName }}</p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.notice.hosting.title">
      <p>{{ $t('legal.notice.hosting.intro') }}</p>
      <LandingLegalDetails :rows="hostingRows" />
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.notice.intellectualProperty.title">
      <p>{{ $t('legal.notice.intellectualProperty.ownership', { name: PUBLISHER_LEGAL_IDENTITY.fullName }) }}</p>
      <p>{{ $t('legal.notice.intellectualProperty.fonts') }}</p>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.notice.personalData.title">
      <I18nT keypath="legal.notice.personalData.body" tag="p" scope="global">
        <template #privacyLink>
          <NuxtLink :to="localePath('/privacy')" class="landing-link">
            {{ $t('legal.notice.personalData.privacyLink') }}
          </NuxtLink>
        </template>
      </I18nT>
    </LandingLegalSection>

    <LandingLegalSection title-key="legal.notice.report.title">
      <p>{{ $t('legal.notice.report.body', { email: PUBLISHER_CONTACT.email, phone: $t('publisher.phone') }) }}</p>
    </LandingLegalSection>
  </LandingLegalDocument>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { LegalDetailRow } from '~/types/LandingLegalDetails'
import { PUBLISHER_CONTACT, PUBLISHER_LEGAL_IDENTITY } from '~/constants/publisher'

definePageMeta({
  layout: 'marketing',
})

const { t }: { t: (key: string, params?: Record<string, unknown>) => string } = useI18n()
const localePath: ReturnType<typeof useLocalePath> = useLocalePath()

const publisherRows: ComputedRef<LegalDetailRow[]> = computed((): LegalDetailRow[] => [
  { label: t('legal.notice.publisher.rows.name'), value: PUBLISHER_LEGAL_IDENTITY.fullName },
  { label: t('legal.notice.publisher.rows.status'), value: t('legal.notice.publisher.rows.statusValue') },
  { label: t('legal.notice.publisher.rows.address'), value: PUBLISHER_LEGAL_IDENTITY.address },
  { label: t('legal.notice.publisher.rows.siret'), value: PUBLISHER_LEGAL_IDENTITY.siret },
  {
    label: t('legal.notice.publisher.rows.vat'),
    value: PUBLISHER_LEGAL_IDENTITY.vatNumber,
    note: t('legal.notice.publisher.rows.vatNote'),
  },
  { label: t('legal.notice.publisher.rows.phone'), value: t('publisher.phone') },
  { label: t('legal.notice.publisher.rows.email'), value: PUBLISHER_CONTACT.email },
])

const hostingRows: ComputedRef<LegalDetailRow[]> = computed((): LegalDetailRow[] => [
  { label: t('legal.notice.hosting.rows.host'), value: PUBLISHER_LEGAL_IDENTITY.hostName },
  { label: t('legal.notice.hosting.rows.address'), value: PUBLISHER_LEGAL_IDENTITY.hostAddress },
  { label: t('legal.notice.hosting.rows.phone'), value: PUBLISHER_LEGAL_IDENTITY.hostPhone },
  { label: t('legal.notice.hosting.rows.website'), value: PUBLISHER_LEGAL_IDENTITY.hostWebsite },
])

useHead(() => ({
  title: `${t('legal.notice.title')} — DevLeadHunter`,
  meta: [{ name: 'description', content: t('legal.notice.intro') }],
}))
</script>
