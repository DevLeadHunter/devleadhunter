<template>
  <div class="max-w-3xl space-y-6">
    <header>
      <p class="app-label">Réglages</p>
      <h1 class="app-page-title">Relance SMS</h1>
      <p class="text-muted mt-1 text-sm">
        Relancez par SMS les prospects qui n'ont pas répondu à votre email — un rappel vers leur site de démonstration.
        L'envoi respecte les horaires légaux (lun–ven 8h–20h, sam 10h–19h, jamais dimanche ni jour férié), n'inclut que
        les mobiles 06/07, et porte toujours la mention STOP.
      </p>
    </header>

    <section class="app-card p-5">
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Votre expéditeur</h2>
      <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
        Le nom affiché sur le téléphone du prospect (3 à 11 caractères, lettres et chiffres). Renseigner un expéditeur
        active le canal SMS. Les prospects ne peuvent pas répondre à un SMS : ils reviennent vers vous depuis le bandeau
        de leur site de démonstration.
      </p>

      <div
        v-if="!config?.provider_ready"
        class="mt-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3 text-xs text-[var(--app-ink-soft)]"
      >
        Le canal SMS n'est pas encore activé côté serveur (clé smsmode manquante). Vous pouvez déjà régler votre
        expéditeur ; les envois seront possibles une fois la clé configurée.
      </div>

      <div class="mt-4">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-[var(--app-ink)]">Nom d'expéditeur</span>
          <input
            v-model="sender"
            type="text"
            maxlength="11"
            placeholder="Dibodev"
            class="input-field h-10 w-full @lg:max-w-xs"
          />
        </label>
      </div>

      <div class="mt-4 flex items-center gap-3">
        <button class="app-btn-primary" :disabled="isSaving" @click="save">
          {{ isSaving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
        <span v-if="senderPreview" class="text-xs text-[var(--app-ink-soft)]"> Aperçu : « {{ senderPreview }} » </span>
      </div>
    </section>

    <section class="app-card p-5">
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Automatisations</h2>
      <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
        Désactivées par défaut : vous gardez la main en manuel. Activez-les pour laisser DevLeadHunter envoyer tout
        seul, toujours dans la fenêtre légale (lun–ven 8h–20h, sam 10h–19h).
      </p>

      <div class="mt-4 flex items-start gap-3">
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-[var(--app-ink)]">Relance SMS automatique</p>
          <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
            Relance par SMS les prospects emailés il y a {{ autoRelanceAfterDays }} jours sans réponse (une ouverture ou
            un clic ne les exclut pas). Leur site de démonstration est réveillé et repart pour 21 jours.
          </p>
        </div>
        <UiSwitch id="sms-auto-relance" :model-value="autoRelanceEnabled" @update:model-value="onToggleAutoRelance" />
      </div>

      <div v-if="autoRelanceEnabled" class="mt-3">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-[var(--app-ink)]">Délai avant relance (jours)</span>
          <input
            v-model.number="autoRelanceAfterDays"
            type="number"
            min="7"
            max="120"
            class="input-field h-10 w-full @lg:max-w-[8rem]"
            @change="saveAutomation"
          />
        </label>
      </div>

      <div class="mt-5 flex items-start gap-3 border-t border-[var(--app-line-soft)] pt-4">
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-[var(--app-ink)]">Prospection SMS des prospects sans email</p>
          <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">
            Contacte par SMS les prospects qui ont un mobile 06/07 mais pas d'email — le SMS devient le premier contact,
            avec leur site de démonstration.
          </p>
        </div>
        <UiSwitch id="sms-cold" :model-value="coldSmsEnabled" @update:model-value="onToggleColdSms" />
      </div>
    </section>

    <section class="app-card p-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Prospects à relancer</h2>
          <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
            Emailés il y a plus de 30 jours, sans réponse, avec un mobile et une démo active.
          </p>
        </div>
        <button
          class="app-btn-secondary"
          :disabled="isLoadingCandidates || rows.length === 0 || !canSend"
          @click="sendAll"
        >
          Tout relancer
        </button>
      </div>

      <div class="mt-4">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-[var(--app-ink)]">Modèle de relance</span>
          <UiSelectField
            :model-value="relanceTemplateKey"
            :options="relanceTemplateOptions"
            placeholder="Choisir un modèle…"
            @update:model-value="onChangeRelanceTemplate"
          />
        </label>
        <p
          v-if="relanceTemplatePreview"
          class="mt-2 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] p-3 text-xs leading-relaxed text-[var(--app-ink)]"
        >
          {{ relanceTemplatePreview }}
        </p>
        <p class="mt-1 text-[11px] text-[var(--app-ink-soft)]">
          Rendu pour chaque prospect (salutation, lien de sa démo, votre prénom). Utilisé par « Relancer », « Tout
          relancer » et la relance automatique. Un seul SMS par prospect.
        </p>
      </div>

      <div v-if="isLoadingCandidates" class="mt-4 flex justify-center py-6">
        <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-[var(--app-ink-soft)]" />
      </div>

      <p v-else-if="rows.length === 0" class="mt-4 text-xs text-[var(--app-ink-soft)]">
        Aucun prospect éligible à une relance SMS pour le moment.
      </p>

      <div v-else class="mt-4 divide-y divide-[var(--app-line-soft)]">
        <div v-for="row in rows" :key="row.prospect_id" class="flex items-center gap-3 py-2.5">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ row.name }}</p>
            <p class="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-[var(--app-ink-soft)]">
              <span>{{ row.city || '—' }}</span>
              <span class="inline-flex items-center gap-1">
                <UIcon name="i-lucide-phone" class="h-3 w-3" />{{ row.phone }}
              </span>
              <span>Emailé le {{ formatDate(row.emailed_at) }}</span>
            </p>
          </div>
          <span v-if="row.sent" class="app-badge app-badge--success shrink-0">Envoyé</span>
          <span v-else-if="row.error" class="shrink-0 text-xs text-[var(--app-red)]">{{ row.error }}</span>
          <button
            v-else
            class="app-btn-secondary h-8 shrink-0 px-3 text-xs"
            :disabled="row.sending || !canSend"
            @click="sendOne(row)"
          >
            {{ row.sending ? 'Envoi…' : 'Relancer' }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { UseAuthReturn, UseToastReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { SmsCandidateRow } from '~/types/SmsSettingsPage'
import type { SelectFieldOption } from '~/types/SelectField'
import type { SmsConfig, SmsRelanceCandidate, SmsSendResult, SmsTemplate } from '~/services/smsService'
import { SmsService } from '~/services/smsService'
import { SmsVariables } from '~/utils/smsVariables'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const toast: UseToastReturn = useToast()
const { user }: UseAuthReturn = useAuth()

const config: Ref<SmsConfig | null> = ref(null)
const sender: Ref<string> = ref('')
const isSaving: Ref<boolean> = ref(false)

const coldSmsEnabled: Ref<boolean> = ref(false)
const autoRelanceEnabled: Ref<boolean> = ref(false)
const autoRelanceAfterDays: Ref<number> = ref(30)

/** Key of the library template the J+30 relance renders. */
const relanceTemplateKey: Ref<string> = ref('')

/** Follow-up templates of the SMS library. */
const relanceTemplates: Ref<SmsTemplate[]> = ref([])

const rows: Ref<SmsCandidateRow[]> = ref([])
const isLoadingCandidates: Ref<boolean> = ref(false)

/** Whether sends are possible (a sender is configured + the server key is ready). */
const canSend: ComputedRef<boolean> = computed(
  (): boolean => Boolean(config.value?.sender) && Boolean(config.value?.provider_ready),
)

/** Live preview of the sender name as it will appear. */
const senderPreview: ComputedRef<string> = computed((): string => sender.value.trim())

const relanceTemplateOptions: ComputedRef<SelectFieldOption<string>[]> = computed((): SelectFieldOption<string>[] =>
  relanceTemplates.value.map(
    (template: SmsTemplate): SelectFieldOption<string> => ({ value: template.key, label: template.name }),
  ),
)

/** The chosen relance template with sample values, STOP mention included, as a prospect would read it. */
const relanceTemplatePreview: ComputedRef<string> = computed((): string => {
  const template: SmsTemplate | undefined = relanceTemplates.value.find(
    (candidate: SmsTemplate): boolean => candidate.key === relanceTemplateKey.value,
  )
  if (!template) return ''
  return `${SmsVariables.renderWithSampleValues(template.body, SmsVariables.firstNameOf(user.value?.name))} STOP au 36180`
})

/**
 * Format an ISO date to a short French date.
 * @param iso - The ISO timestamp.
 * @returns The formatted date.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Load the SMS config (sender + automation opt-ins). */
async function loadConfig(): Promise<void> {
  try {
    config.value = await SmsService.getConfig()
    sender.value = config.value.sender
    coldSmsEnabled.value = config.value.cold_sms_enabled
    autoRelanceEnabled.value = config.value.auto_relance_enabled
    autoRelanceAfterDays.value = config.value.auto_relance_after_days
    relanceTemplateKey.value = config.value.relance_template_key
  } catch {
    toast.error('Impossible de charger la configuration SMS')
  }
}

/** Load the follow-up templates of the SMS library. */
async function loadRelanceTemplates(): Promise<void> {
  try {
    relanceTemplates.value = await SmsService.listTemplates('follow_up')
  } catch {
    relanceTemplates.value = []
  }
}

/** Persist the SMS automation opt-ins and the relance template. */
async function saveAutomation(): Promise<void> {
  try {
    config.value = await SmsService.updateAutomation({
      cold_sms_enabled: coldSmsEnabled.value,
      auto_relance_enabled: autoRelanceEnabled.value,
      auto_relance_after_days: autoRelanceAfterDays.value,
      relance_template_key: relanceTemplateKey.value || undefined,
    })
    toast.success('Automatisations enregistrées')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'enregistrement")
  }
}

/**
 * Toggle the auto-relance and persist.
 * @param value - The new state.
 */
async function onToggleAutoRelance(value: boolean): Promise<void> {
  autoRelanceEnabled.value = value
  await saveAutomation()
}

/**
 * Toggle the cold-SMS and persist.
 * @param value - The new state.
 */
async function onToggleColdSms(value: boolean): Promise<void> {
  coldSmsEnabled.value = value
  await saveAutomation()
}

/**
 * Pick the relance template and persist.
 * @param key - The chosen template key.
 */
async function onChangeRelanceTemplate(key: string): Promise<void> {
  relanceTemplateKey.value = key
  await saveAutomation()
}

/** Load the relance candidates. */
async function loadCandidates(): Promise<void> {
  isLoadingCandidates.value = true
  try {
    const candidates: SmsRelanceCandidate[] = await SmsService.listCandidates()
    rows.value = candidates.map(
      (candidate: SmsRelanceCandidate): SmsCandidateRow => ({
        ...candidate,
        sending: false,
        sent: false,
        error: null,
      }),
    )
  } catch {
    rows.value = []
  } finally {
    isLoadingCandidates.value = false
  }
}

/** Save the sender configuration. */
async function save(): Promise<void> {
  isSaving.value = true
  try {
    config.value = await SmsService.updateConfig({ sender: sender.value.trim() })
    toast.success('Configuration SMS enregistrée')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'enregistrement")
  } finally {
    isSaving.value = false
  }
}

/**
 * Send a relance SMS to one candidate row.
 * @param row - The candidate row.
 */
async function sendOne(row: SmsCandidateRow): Promise<void> {
  row.sending = true
  row.error = null
  try {
    const result: SmsSendResult = await SmsService.sendRelance(row.prospect_id)
    if (result.sent) {
      row.sent = true
    } else {
      row.error = result.reason ?? "Échec de l'envoi"
    }
  } catch (err: unknown) {
    row.error = err instanceof Error ? err.message : "Échec de l'envoi"
  } finally {
    row.sending = false
  }
}

/** Send a relance SMS to every eligible candidate. */
async function sendAll(): Promise<void> {
  for (const row of rows.value) {
    if (!row.sent && !row.error) {
      await sendOne(row)
    }
  }
}

onMounted(async (): Promise<void> => {
  await loadConfig()
  await loadRelanceTemplates()
  await loadCandidates()
})
</script>
