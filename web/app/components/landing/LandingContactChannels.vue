<template>
  <div class="min-w-0">
    <div class="flex items-center gap-4 border-b border-[#e3dccd] pb-7">
      <img
        :src="PUBLISHER_CONTACT.portraitSrc"
        :alt="$t('contact.person.portraitAlt')"
        width="64"
        height="64"
        class="h-16 w-16 shrink-0 rounded-full bg-[#1b1813] object-cover"
      />
      <div class="min-w-0">
        <p class="font-display text-lg leading-tight font-semibold text-[#1b1813]">
          {{ PUBLISHER_LEGAL_IDENTITY.fullName }}
        </p>
        <p class="mt-0.5 text-sm text-[#6b6355]">{{ $t('contact.person.role') }}</p>
        <a
          :href="PUBLISHER_CONTACT.websiteUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="landing-link mt-1 inline-flex items-center gap-1 text-sm"
        >
          {{ PUBLISHER_CONTACT.websiteLabel }}
          <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>
    </div>

    <div class="border-b border-[#e3dccd] py-7">
      <p class="font-label text-[0.68rem] font-medium tracking-[0.16em] text-[#6b6355] uppercase">
        {{ $t('contact.phone.label') }}
      </p>
      <a
        :href="PUBLISHER_CONTACT.phoneHref"
        class="font-display mt-2 block text-[2.35rem] leading-tight font-semibold tracking-[-0.015em] text-[#1b1813] tabular-nums md:text-[2.75rem]"
        @click="trackPhoneClick"
      >
        {{ $t('publisher.phone') }}
      </a>
      <p class="mt-2 text-[0.95rem] leading-relaxed text-[#6b6355]">{{ $t('contact.phone.hours') }}</p>
      <div class="mt-5 flex flex-wrap items-center gap-3">
        <a
          :href="PUBLISHER_CONTACT.phoneHref"
          class="landing-btn-primary landing-btn--compact w-full sm:w-auto"
          @click="trackPhoneClick"
        >
          <UIcon name="i-lucide-phone" class="h-4 w-4" aria-hidden="true" />
          {{ $t('contact.phone.call') }}
        </a>
        <LandingCopyButton
          :value="$t('publisher.phone')"
          :label="$t('contact.phone.copy')"
          @copied="track('site_contact_copy', { channel: 'phone' })"
        />
      </div>
    </div>

    <div class="border-b border-[#e3dccd] py-7">
      <p class="font-label text-[0.68rem] font-medium tracking-[0.16em] text-[#6b6355] uppercase">
        {{ $t('contact.email.label') }}
      </p>
      <a
        :href="PUBLISHER_CONTACT.emailHref"
        class="font-display mt-2 block text-[1.45rem] leading-tight font-semibold tracking-[-0.01em] break-words text-[#1b1813]"
        @click="trackEmailClick"
      >
        {{ PUBLISHER_CONTACT.email }}
      </a>
      <p class="mt-2 text-[0.95rem] leading-relaxed text-[#6b6355]">{{ $t('contact.email.delay') }}</p>
      <div class="mt-5 flex flex-wrap items-center gap-3">
        <a :href="PUBLISHER_CONTACT.emailHref" class="landing-btn-ghost landing-btn--compact" @click="trackEmailClick">
          <UIcon name="i-lucide-mail" class="h-4 w-4" aria-hidden="true" />
          {{ $t('contact.email.write') }}
        </a>
        <LandingCopyButton
          :value="PUBLISHER_CONTACT.email"
          :label="$t('contact.email.copy')"
          @copied="track('site_contact_copy', { channel: 'email' })"
        />
      </div>
    </div>

    <div class="pt-7">
      <p class="font-label text-[0.68rem] font-medium tracking-[0.16em] text-[#6b6355] uppercase">
        {{ $t('contact.place.label') }}
      </p>
      <p class="font-display mt-2 text-xl leading-snug font-medium text-[#1b1813]">{{ $t('contact.place.city') }}</p>
      <p class="mt-2 text-[0.95rem] leading-relaxed text-[#6b6355]">
        {{ $t('contact.place.publisher') }}
        <NuxtLink :to="localePath('/legal')" class="landing-link">{{ $t('contact.place.legalLink') }}</NuxtLink>
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { PUBLISHER_CONTACT, PUBLISHER_LEGAL_IDENTITY } from '~/constants/publisher'

const localePath: ReturnType<typeof useLocalePath> = useLocalePath()
const { track }: { track: (event: string, properties?: Record<string, unknown> | undefined) => void } =
  useSiteTracking()

/**
 * Record a tap on the phone number or the « Appeler » button.
 */
function trackPhoneClick(): void {
  track('site_contact_phone_click', { location: 'contact_page' })
}

/**
 * Record a tap on the email address or the « Écrire un e-mail » button.
 */
function trackEmailClick(): void {
  track('site_contact_email_click', { location: 'contact_page' })
}
</script>
