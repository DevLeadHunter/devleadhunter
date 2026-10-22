<template>
  <main class="flex min-h-dvh items-center justify-center bg-stone-50 px-4 py-6 text-stone-900">
    <section
      v-if="props.withdrawnDemo"
      class="flex w-full max-w-md flex-col gap-3.5 rounded-2xl border border-stone-200 bg-white px-6 py-7 shadow-xl shadow-stone-900/5"
      aria-labelledby="demo-offline-title"
    >
      <p class="font-mono text-xs tracking-widest wrap-anywhere text-stone-500 uppercase">
        Votre démo · {{ businessName }}
      </p>
      <h1 id="demo-offline-title" class="text-2xl font-semibold tracking-tight">Ce site n'est plus en ligne</h1>
      <p class="text-base leading-relaxed text-stone-700">{{ withdrawalSentence }}</p>
      <p class="text-base leading-relaxed text-stone-700">{{ revivalOfferSentence }}</p>
      <button
        type="button"
        class="mt-1 h-12 cursor-pointer rounded-xl bg-stone-900 text-base font-semibold text-stone-50 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-stone-900 disabled:cursor-default disabled:opacity-60"
        :disabled="revivalState === 'reviving'"
        @click="reviveDemo"
      >
        {{ revivalState === 'reviving' ? 'Remise en ligne…' : 'Remettre le site en ligne' }}
      </button>
      <p v-if="revivalState === 'failed'" class="text-sm text-red-700" role="alert">{{ revivalFailureSentence }}</p>
      <p class="text-sm text-stone-500">{{ priceAndRefusalSentence }}</p>

      <div v-if="ownerName" class="mt-1 flex items-center gap-3 border-t border-stone-200 pt-5">
        <img
          v-if="ownerPhotoUrl"
          class="size-12 shrink-0 rounded-full border-2 border-white bg-stone-200 object-cover ring-1 ring-stone-200"
          :src="ownerPhotoUrl"
          alt=""
        />
        <div>
          <p class="text-base leading-tight font-semibold">{{ ownerName }}</p>
          <p class="mt-1 text-sm wrap-anywhere text-stone-500">{{ ownerRoleLabel }}</p>
        </div>
      </div>
      <div v-if="ownerPhoneHref || ownerEmailHref" class="flex flex-wrap gap-2">
        <a
          v-if="ownerPhoneHref"
          class="inline-flex min-h-10 min-w-36 flex-auto items-center justify-center rounded-xl border border-stone-200 px-3 py-2 text-center text-sm font-medium wrap-anywhere hover:bg-stone-100"
          :href="ownerPhoneHref"
          @click="trackOwnerContactClick('phone')"
          >{{ ownerPhone }}</a
        >
        <a
          v-if="ownerEmailHref"
          class="inline-flex min-h-10 min-w-36 flex-auto items-center justify-center rounded-xl border border-stone-200 px-3 py-2 text-center text-sm font-medium wrap-anywhere hover:bg-stone-100"
          :href="ownerEmailHref"
          @click="trackOwnerContactClick('email')"
          >{{ ownerEmail }}</a
        >
      </div>
    </section>

    <section
      v-else
      class="w-full max-w-md rounded-2xl border border-stone-200 bg-white px-6 py-7 shadow-xl shadow-stone-900/5"
      aria-labelledby="demo-offline-title"
    >
      <h1 id="demo-offline-title" class="text-2xl font-semibold tracking-tight">Ce lien n'est plus actif</h1>
    </section>
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { DemoOfflinePageProps, DemoOwnerContactChannel, DemoRevivalState } from '~/types/DemoOfflinePage'
import type { DemoSiteWithdrawn } from '~/types/demoSite'
import { captureDemoEvent } from '~/composables/useDemoTracking'
import { DEMO_OWNER_ROLE_LABEL } from '~/constants/DemoOwnerLabels'
import { ApiRefusalUtils } from '~/utils/ApiRefusalUtils'
import { ContactLinkUtils } from '~/utils/ContactLinkUtils'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

const props: DemoOfflinePageProps = defineProps({
  slug: { type: String, required: true },
  withdrawnDemo: { type: Object as PropType<DemoSiteWithdrawn | null>, default: null },
})

const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const route: ReturnType<typeof useRoute> = useRoute()
const { initForWithdrawnDemo }: ReturnType<typeof useDemoTracking> = useDemoTracking()

const revivalState: Ref<DemoRevivalState> = ref('idle')

const apiBase: ComputedRef<string> = computed((): string => String(config.public.apiBase ?? ''))

const businessName: ComputedRef<string> = computed(
  (): string => props.withdrawnDemo?.business_name || 'votre entreprise',
)

const withdrawalSentence: ComputedRef<string> = computed((): string => {
  const withdrawnOn: string | null | undefined = props.withdrawnDemo?.withdrawn_on_label

  if (!withdrawnOn) {
    return `J'ai créé ce site pour ${businessName.value} et je l'ai retiré à la date prévue.`
  }
  return `J'ai créé ce site pour ${businessName.value} et je l'ai retiré le ${keepOnOneLine(withdrawnOn)}, comme prévu.`
})

const revivalOfferSentence: ComputedRef<string> = computed((): string => {
  const revivedUntil: string = keepOnOneLine(props.withdrawnDemo?.revived_until_label ?? '')
  return `Vous voulez le revoir ? Je le remets en ligne tout de suite, jusqu'au ${revivedUntil}, sans engagement.`
})

const priceAndRefusalSentence: ComputedRef<string> = computed((): string => {
  const salePrice: string | null | undefined = props.withdrawnDemo?.sale_price_label
  const refusal: string = 'Sinon, rien à faire : il reste hors ligne.'

  if (!salePrice) {
    return refusal
  }
  return `S'il vous plaît, il est à vous pour ${keepOnOneLine(salePrice)}. ${refusal}`
})

const ownerName: ComputedRef<string> = computed((): string => (props.withdrawnDemo?.owner_name ?? '').trim())

const ownerPhotoUrl: ComputedRef<string> = computed((): string =>
  (props.withdrawnDemo?.owner_profile_photo_url ?? '').trim(),
)

const ownerPhone: ComputedRef<string> = computed((): string => (props.withdrawnDemo?.owner_contact_phone ?? '').trim())

const ownerEmail: ComputedRef<string> = computed((): string => (props.withdrawnDemo?.owner_contact_email ?? '').trim())

const ownerPhoneHref: ComputedRef<string | null> = computed((): string | null =>
  ownerPhone.value ? ContactLinkUtils.href(ownerPhone.value) : null,
)

const ownerEmailHref: ComputedRef<string | null> = computed((): string | null =>
  ownerEmail.value ? ContactLinkUtils.href(ownerEmail.value) : null,
)

const ownerRoleLabel: ComputedRef<string> = computed((): string => {
  const websiteDomain: string = ContactLinkUtils.websiteDomain(props.withdrawnDemo?.owner_company_website_url)
  return websiteDomain ? `${DEMO_OWNER_ROLE_LABEL} · ${websiteDomain}` : DEMO_OWNER_ROLE_LABEL
})

const revivalFailureSentence: ComputedRef<string> = computed((): string =>
  ownerPhone.value
    ? `La remise en ligne n'a pas marché. Réessayez dans un instant ou appelez-moi au ${keepOnOneLine(ownerPhone.value)}.`
    : "La remise en ligne n'a pas marché. Réessayez dans un instant.",
)

/**
 * Keep a short label on one line, so « 21 octobre », « 500 € » or a phone number never breaks.
 * @param label - The label as written, with plain spaces.
 * @returns The label with non-breaking spaces.
 */
function keepOnOneLine(label: string): string {
  return label.replaceAll(' ', ' ')
}

/**
 * Whether the visit is the prospect's own: never the owner's tagged visit nor the dashboard's embedded preview.
 * @returns True when the visit may notify the owner.
 */
function isProspectVisit(): boolean {
  return !DemoBeaconUtils.isInternalVisit() && window.self === window.top
}

/**
 * Bring the demo back online, then reload so the live demo renders with its own full tracking.
 */
async function reviveDemo(): Promise<void> {
  if (revivalState.value === 'reviving') {
    return
  }

  revivalState.value = 'reviving'
  captureDemoEvent('demo_withdrawn_revive_click')
  try {
    await $fetch(`${apiBase.value}/api/v1/demo-sites/public/${props.slug}/revive`, { method: 'POST' })
  } catch (error: unknown) {
    revivalState.value = 'failed'
    captureDemoEvent('demo_withdrawn_revive_failed', { status: ApiRefusalUtils.status(error) ?? null })
    return
  }

  captureDemoEvent('demo_withdrawn_revived')
  if (isProspectVisit()) {
    DemoBeaconUtils.send(apiBase.value, props.slug, 'demo_withdrawn_revived')
  }
  window.location.reload()
}

/**
 * Report a tap on the owner's phone or email, the way the live demo reports its contact clicks.
 * @param contactChannel - The contact the prospect tapped.
 */
function trackOwnerContactClick(contactChannel: DemoOwnerContactChannel): void {
  captureDemoEvent('demo_withdrawn_contact_click', { contact_channel: contactChannel })
  if (isProspectVisit()) {
    DemoBeaconUtils.send(
      apiBase.value,
      props.slug,
      contactChannel === 'phone' ? 'demo_phone_click' : 'demo_contact_click',
    )
  }
}

onMounted(async (): Promise<void> => {
  if (!props.withdrawnDemo) {
    return
  }

  await initForWithdrawnDemo(
    props.slug,
    DemoBeaconUtils.variantFromQuery(route.query.v),
    DemoBeaconUtils.channelFromQuery(route.query.src),
  )
  captureDemoEvent('demo_withdrawn_view')
  if (isProspectVisit()) {
    DemoBeaconUtils.send(apiBase.value, props.slug, 'demo_withdrawn_view')
  }
})
</script>
