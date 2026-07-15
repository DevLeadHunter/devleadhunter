<template>
  <LandingLegalArticle title-key="legal.privacy.title" intro-key="legal.privacy.intro" :section-keys="sectionKeys" />
</template>

<script setup lang="ts">
/**
 * Privacy policy page — light editorial layout on the marketing theme.
 */
definePageMeta({
  layout: 'marketing',
})

const { t } = useI18n()

/** Base i18n keys of the privacy policy sections. */
const sectionKeys: string[] = Array.from(
  { length: 7 },
  (_: unknown, index: number): string => `legal.privacy.s${index + 1}`,
)

useHead(() => ({
  title: `${t('legal.privacy.title')} — DevLeadHunter`,
  meta: [{ name: 'description', content: t('legal.privacy.intro') }],
}))
</script>
