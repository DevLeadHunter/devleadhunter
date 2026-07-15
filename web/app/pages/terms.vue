<template>
  <LandingLegalArticle title-key="legal.terms.title" intro-key="legal.terms.intro" :section-keys="sectionKeys" />
</template>

<script setup lang="ts">
/**
 * Terms of service page — light editorial layout on the marketing theme.
 */
definePageMeta({
  layout: 'marketing',
})

const { t } = useI18n()

/** Base i18n keys of the terms sections. */
const sectionKeys: string[] = Array.from(
  { length: 8 },
  (_: unknown, index: number): string => `legal.terms.s${index + 1}`,
)

useHead(() => ({
  title: `${t('legal.terms.title')} — DevLeadHunter`,
  meta: [{ name: 'description', content: t('legal.terms.intro') }],
}))
</script>
