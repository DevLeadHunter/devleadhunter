<template>
  <div
    class="min-w-0 border-t border-[#e3dccd] pt-10 sm:rounded-2xl sm:border sm:bg-[#fcfaf5] sm:p-8 sm:shadow-[0_24px_48px_-32px_rgba(27,24,19,0.25)] lg:self-start lg:p-10"
  >
    <div v-if="sentMessage" class="grid justify-items-start gap-4">
      <span class="grid h-12 w-12 place-items-center rounded-full bg-[#2f7d4e]/10 text-[#2f7d4e]">
        <UIcon name="i-lucide-check" class="h-6 w-6" aria-hidden="true" />
      </span>
      <h2
        ref="confirmationHeading"
        tabindex="-1"
        class="font-display text-2xl font-semibold text-[#1b1813] focus:outline-none"
      >
        {{ $t('contact.form.sent.title') }}
      </h2>
      <p class="text-base leading-relaxed text-[#6b6355]">
        {{ $t('contact.form.sent.body', { name: sentMessage.firstName, email: sentMessage.email }) }}
      </p>
      <button type="button" class="landing-link text-sm" @click="startNewMessage">
        {{ $t('contact.form.sent.again') }}
      </button>
    </div>

    <form v-else class="grid gap-6" novalidate @submit.prevent="submitMessage">
      <div class="grid gap-1.5">
        <h2 class="font-display text-2xl font-semibold text-[#1b1813]">{{ $t('contact.form.title') }}</h2>
        <p class="text-[0.95rem] text-[#6b6355]">{{ $t('contact.form.required') }}</p>
      </div>

      <fieldset class="min-w-0">
        <legend class="mb-3 text-sm font-semibold text-[#1b1813]">{{ $t('contact.form.topicLegend') }}</legend>
        <div class="flex flex-wrap gap-2">
          <label
            v-for="topic in SITE_CONTACT_TOPICS"
            :key="topic"
            class="cursor-pointer rounded-full border border-[#e3dccd] bg-[#f6f3ec] px-4 py-2 text-sm font-medium text-[#6b6355] transition-colors hover:border-[#cfc6b4] has-checked:border-[#1b1813] has-checked:bg-[#1b1813] has-checked:text-[#fcfaf5] has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-[#1b1813]"
          >
            <input v-model="selectedTopic" type="radio" name="topic" :value="topic" class="sr-only" />
            {{ $t(`contact.form.topics.${topic}`) }}
          </label>
        </div>
      </fieldset>

      <div class="grid gap-6 sm:grid-cols-2 sm:gap-4">
        <div class="grid min-w-0 content-start gap-2">
          <label for="contact-name" class="text-sm font-semibold text-[#1b1813]">{{ $t('contact.form.name') }}</label>
          <input
            id="contact-name"
            ref="nameInput"
            v-model="visitorName"
            type="text"
            name="name"
            autocomplete="name"
            maxlength="120"
            :placeholder="$t('contact.form.namePlaceholder')"
            class="landing-input landing-input--large"
            :class="isNameMissing ? 'landing-input--error' : ''"
            :aria-invalid="isNameMissing"
            :aria-describedby="isNameMissing ? 'contact-name-error' : undefined"
          />
          <p v-if="isNameMissing" id="contact-name-error" class="text-sm text-[#b3462e]">
            {{ $t('contact.form.errors.name') }}
          </p>
        </div>

        <div class="grid min-w-0 content-start gap-2">
          <label for="contact-email" class="text-sm font-semibold text-[#1b1813]">{{ $t('contact.form.email') }}</label>
          <input
            id="contact-email"
            ref="emailInput"
            v-model="visitorEmail"
            type="email"
            name="email"
            inputmode="email"
            autocomplete="email"
            maxlength="254"
            :placeholder="$t('contact.form.emailPlaceholder')"
            class="landing-input landing-input--large"
            :class="isEmailInvalid ? 'landing-input--error' : ''"
            :aria-invalid="isEmailInvalid"
            :aria-describedby="isEmailInvalid ? 'contact-email-error' : undefined"
          />
          <p v-if="isEmailInvalid" id="contact-email-error" class="text-sm text-[#b3462e]">
            {{ $t('contact.form.errors.email') }}
          </p>
        </div>
      </div>

      <div class="grid gap-2">
        <label for="contact-phone" class="text-sm font-semibold text-[#1b1813]">
          {{ $t('contact.form.phone') }}
          <span class="font-normal text-[#6b6355]">{{ $t('contact.form.optional') }}</span>
        </label>
        <input
          id="contact-phone"
          v-model="visitorPhone"
          type="tel"
          name="phone"
          autocomplete="tel"
          maxlength="40"
          :placeholder="$t('contact.form.phonePlaceholder')"
          class="landing-input landing-input--large"
          aria-describedby="contact-phone-hint"
        />
        <p id="contact-phone-hint" class="text-sm text-[#6b6355]">{{ $t('contact.form.phoneHint') }}</p>
      </div>

      <div class="grid gap-2">
        <label for="contact-message" class="text-sm font-semibold text-[#1b1813]">
          {{ $t('contact.form.message') }}
        </label>
        <textarea
          id="contact-message"
          ref="messageInput"
          v-model="visitorMessage"
          name="message"
          rows="6"
          maxlength="5000"
          :placeholder="$t(`contact.form.placeholders.${selectedTopic}`)"
          class="landing-input landing-input--large resize-y"
          :class="isMessageMissing ? 'landing-input--error' : ''"
          :aria-invalid="isMessageMissing"
          :aria-describedby="isMessageMissing ? 'contact-message-error' : undefined"
        ></textarea>
        <p v-if="isMessageMissing" id="contact-message-error" class="text-sm text-[#b3462e]">
          {{ $t('contact.form.errors.message') }}
        </p>
      </div>

      <div class="absolute -left-[10000px] h-px w-px overflow-hidden" aria-hidden="true">
        <input
          id="contact-website"
          v-model="honeypotValue"
          type="text"
          name="website"
          tabindex="-1"
          autocomplete="off"
        />
      </div>

      <p
        v-if="hasSendingFailed"
        role="alert"
        class="rounded-xl border border-[#b3462e]/25 bg-[#b3462e]/[0.06] px-4 py-3 text-sm leading-relaxed text-[#b3462e]"
      >
        {{ $t('contact.form.errors.sending', { phone: $t('publisher.phone') }) }}
      </p>

      <div class="grid gap-4">
        <button type="submit" class="landing-btn-primary w-full disabled:opacity-70" :disabled="isSending">
          {{ isSending ? $t('contact.form.submitting') : $t('contact.form.submit') }}
          <UIcon v-if="!isSending" name="i-lucide-arrow-right" class="h-4 w-4" aria-hidden="true" />
        </button>
        <p class="text-[0.82rem] leading-relaxed text-[#6b6355]">
          {{ $t('contact.form.privacyNote') }}
          <NuxtLink :to="localePath('/privacy')" class="landing-link">{{ $t('contact.form.privacyLink') }}</NuxtLink>
        </p>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { LandingContactSentMessage } from '~/types/LandingContactForm'
import type { SiteContactTopic } from '~/types/SiteContact'
import { SITE_CONTACT_TOPICS } from '~/constants/siteContactTopics'
import { SiteContactService } from '~/services/siteContactService'
import { FieldsValidation } from '~/utils/fieldsValidation'

const { locale }: { locale: Ref<string> } = useI18n()
const localePath: ReturnType<typeof useLocalePath> = useLocalePath()
const { track }: { track: (event: string, properties?: Record<string, unknown> | undefined) => void } =
  useSiteTracking()

const selectedTopic: Ref<SiteContactTopic> = ref('discover')
const visitorName: Ref<string> = ref('')
const visitorEmail: Ref<string> = ref('')
const visitorPhone: Ref<string> = ref('')
const visitorMessage: Ref<string> = ref('')
const honeypotValue: Ref<string> = ref('')
const hasTriedToSubmit: Ref<boolean> = ref(false)
const isSending: Ref<boolean> = ref(false)
const hasSendingFailed: Ref<boolean> = ref(false)
const sentMessage: Ref<LandingContactSentMessage | null> = ref(null)
const nameInput: Ref<HTMLInputElement | null> = ref(null)
const emailInput: Ref<HTMLInputElement | null> = ref(null)
const messageInput: Ref<HTMLTextAreaElement | null> = ref(null)
const confirmationHeading: Ref<HTMLHeadingElement | null> = ref(null)

const isNameMissing: ComputedRef<boolean> = computed(
  (): boolean => hasTriedToSubmit.value && !FieldsValidation.isFilled(visitorName.value),
)
const isEmailInvalid: ComputedRef<boolean> = computed(
  (): boolean => hasTriedToSubmit.value && !FieldsValidation.isEmail(visitorEmail.value),
)
const isMessageMissing: ComputedRef<boolean> = computed(
  (): boolean => hasTriedToSubmit.value && !FieldsValidation.isFilled(visitorMessage.value),
)
const hasInvalidField: ComputedRef<boolean> = computed(
  (): boolean => isNameMissing.value || isEmailInvalid.value || isMessageMissing.value,
)

/**
 * Find the first field the visitor still has to fix, in reading order.
 * @returns The field, or null when every field is valid.
 */
function findFirstInvalidField(): HTMLInputElement | HTMLTextAreaElement | null {
  if (isNameMissing.value) return nameInput.value
  if (isEmailInvalid.value) return emailInput.value
  if (isMessageMissing.value) return messageInput.value
  return null
}

/**
 * Validate the form, send the message, then show the confirmation or the error.
 */
async function submitMessage(): Promise<void> {
  hasTriedToSubmit.value = true
  hasSendingFailed.value = false
  if (hasInvalidField.value) {
    findFirstInvalidField()?.focus()
    return
  }
  const trimmedName: string = visitorName.value.trim()
  const trimmedEmail: string = visitorEmail.value.trim()
  const trimmedPhone: string = visitorPhone.value.trim()
  isSending.value = true
  try {
    await SiteContactService.send({
      topic: selectedTopic.value,
      name: trimmedName,
      email: trimmedEmail,
      phone: trimmedPhone || null,
      message: visitorMessage.value.trim(),
      locale: locale.value,
      website: honeypotValue.value,
    })
    track('site_contact_submitted', { topic: selectedTopic.value, has_phone: trimmedPhone !== '' })
    sentMessage.value = { firstName: trimmedName.split(/\s+/)[0] ?? trimmedName, email: trimmedEmail }
    await nextTick()
    confirmationHeading.value?.focus()
  } catch {
    hasSendingFailed.value = true
    track('site_contact_failed', { topic: selectedTopic.value })
  } finally {
    isSending.value = false
  }
}

/**
 * Show the form again for another message, keeping who the visitor is.
 */
function startNewMessage(): void {
  visitorMessage.value = ''
  hasTriedToSubmit.value = false
  sentMessage.value = null
}
</script>
