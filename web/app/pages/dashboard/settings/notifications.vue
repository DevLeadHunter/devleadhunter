<template>
  <div class="max-w-3xl space-y-6">
    <header>
      <p class="app-label">Réglages</p>
      <h1 class="app-page-title">Notifications</h1>
      <p class="text-muted mt-1 text-sm">
        Reçois sur ton téléphone tout ce qui se passe : ouvertures d'email, clics, visites de démo, ventes.
      </p>
    </header>

    <section>
      <div class="app-card p-5">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Notifications push</h2>
            <p class="mt-1 text-xs text-[var(--app-ink-soft)]">{{ hint }}</p>
          </div>

          <div v-if="supported" class="flex shrink-0 items-center gap-3">
            <button v-if="subscribed" type="button" class="app-btn-secondary" :disabled="testing" @click="test">
              {{ testing ? 'Envoi…' : 'Tester' }}
            </button>
            <UiSwitch :model-value="subscribed" :disabled="busy" @update:model-value="toggle" />
          </div>
          <span v-else class="shrink-0 text-xs text-[var(--app-ink-soft)]">Indisponible sur cet appareil</span>
        </div>
      </div>
    </section>

    <UiNotificationList />

    <section v-if="supported && !standalone">
      <div class="app-card p-5">
        <h2 class="text-sm font-semibold text-[var(--app-ink)]">📱 Sur iPhone</h2>
        <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
          Pour recevoir les notifications sur iPhone, ajoute d'abord DevLeadHunter à ton écran d'accueil : bouton
          <strong>Partager</strong>
          <UIcon name="i-lucide-arrow-right" class="inline-block h-[1em] w-[1em] align-[-0.125em]" />
          <strong>« Sur l'écran d'accueil »</strong>, puis rouvre l'app depuis l'icône et active le bouton ci-dessus.
        </p>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { TestNotificationResult } from '~/services/notificationsService'
import type { UseWebPush } from '~/composables/useWebPush'
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import { useToast } from '~/composables/useToast'
import { computed, ref } from 'vue'

definePageMeta({ layout: 'dashboard', middleware: ['auth'] })

const toast: UseToastReturn = useToast()
const { supported, standalone, subscribed, busy, error, toggle, sendTest }: UseWebPush = useWebPush()

const testing: Ref<boolean> = ref(false)

const hint: ComputedRef<string> = computed((): string => {
  if (!supported.value) {
    return 'Ton navigateur ne supporte pas les notifications push.'
  }
  if (error.value === 'permission') {
    return 'Permission refusée. Autorise les notifications dans les réglages de ton navigateur.'
  }
  if (error.value === 'not-configured') {
    return "Le serveur de notifications n'est pas encore configuré (clés VAPID)."
  }
  if (error.value) {
    return 'Une erreur est survenue. Réessaie.'
  }
  if (!standalone.value) {
    return "Active pour recevoir les alertes en temps réel. Sur iPhone, installe d'abord l'app (voir ci-dessous)."
  }
  return subscribed.value ? 'Activé — tu reçois les alertes sur cet appareil.' : 'Désactivé sur cet appareil.'
})

/**
 * Send a test notification and surface the outcome as a toast.
 * @returns Nothing.
 */
async function test(): Promise<void> {
  testing.value = true
  try {
    const result: TestNotificationResult = await sendTest()
    if (result.subscriptions === 0) {
      toast.warning('Aucun appareil abonné sur ce compte.')
    } else if (result.failed > 0) {
      toast.error(result.detail ?? "Le service push a rejeté l'envoi.")
    } else {
      toast.success(`Notification test envoyée (${result.delivered}).`)
    }
  } catch {
    toast.error("Échec de l'envoi du test.")
  } finally {
    testing.value = false
  }
}
</script>
