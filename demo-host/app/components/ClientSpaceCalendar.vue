<template>
  <ClientSpaceSection title="Connexions" :meta="STATUS_LABELS[calendar.status]">
    <p v-if="calendar.status === 'unavailable'" class="cs-muted">
      Agenda Google : la connexion n’est pas encore ouverte. Vos rendez-vous arrivent en demandes, avec les créneaux
      souhaités par le visiteur.
    </p>

    <div v-else-if="calendar.status !== 'connected'" class="csc__connect">
      <p class="csc__lead">
        {{
          calendar.status === 'error'
            ? `L’accès à votre agenda a été perdu : les rendez-vous repassent en demandes à confirmer. Reconnectez-le pour que ${assistantName} réserve à nouveau.`
            : `Connectez votre agenda Google : ${assistantName} proposera vos créneaux libres aux visiteurs et y réservera leurs rendez-vous.`
        }}
      </p>
      <button v-if="!props.readOnly" type="button" class="cs-button" :disabled="isBusy" @click="emit('connect')">
        {{ calendar.status === 'error' ? 'Reconnecter Google Agenda' : 'Connecter Google Agenda' }}
      </button>
      <p v-if="!props.readOnly" class="cs-muted">
        Google s’ouvre dans un nouvel onglet : autorisez l’accès à vos événements et à vos disponibilités, puis revenez
        ici.
      </p>
      <p v-if="errorMessage" class="csc__error">{{ errorMessage }}</p>
    </div>

    <form v-else class="csc__form" @submit.prevent="submit">
      <p class="csc__lead">
        Agenda Google connecté<template v-if="calendar.account_email">
          : <strong>{{ calendar.account_email }}</strong></template
        >. {{ assistantName }} y réserve les rendez-vous, sur vos créneaux libres et dans vos horaires.
      </p>
      <p v-if="calendar.last_error" class="csc__error">Dernier problème le {{ calendar.last_error }}</p>

      <fieldset class="csc__fields" :disabled="props.readOnly">
        <div class="csc__pair">
          <label class="cs-field">
            <span class="cs-label">Durée d’un rendez-vous</span>
            <select v-model.number="duration" class="cs-input">
              <option v-for="minutes in calendar.duration_choices" :key="minutes" :value="minutes">
                {{ durationLabel(minutes) }}
              </option>
            </select>
          </label>
          <label class="cs-field">
            <span class="cs-label">Délai minimum avant un rendez-vous</span>
            <select v-model.number="notice" class="cs-input">
              <option v-for="hours in calendar.min_notice_choices" :key="hours" :value="hours">
                {{ hours === 0 ? 'Aucun' : `${hours} h` }}
              </option>
            </select>
          </label>
        </div>

        <label class="cs-field">
          <span class="cs-label">Types de rendez-vous (facultatif, un par ligne)</span>
          <textarea
            v-model="typesText"
            class="cs-input csc__types"
            rows="3"
            placeholder="Révision&#10;Contrôle technique"
          />
          <span class="cs-muted csc__hint">Le visiteur choisit l’un d’eux avant son créneau. 6 au plus.</span>
        </label>

        <label class="cs-field">
          <span class="cs-label">Agenda utilisé</span>
          <input v-model="calendarId" class="cs-input" type="text" maxlength="255" autocomplete="off" />
          <span class="cs-muted csc__hint">
            « primary » : votre agenda principal. Pour un autre agenda, collez son identifiant (paramètres de l’agenda,
            « Intégrer l’agenda »).
          </span>
        </label>
      </fieldset>

      <ClientSpaceSaveBar
        v-if="!props.readOnly"
        :is-busy="isBusy"
        :can-save="hasChanges"
        :error-message="errorMessage"
        :show-saved="hasSaved && !hasChanges"
      >
        <button type="button" class="cs-button cs-button--outline" :disabled="isBusy" @click="emit('disconnect')">
          Déconnecter
        </button>
      </ClientSpaceSaveBar>
      <p v-if="!props.readOnly" class="cs-muted csc__hint">
        Déconnecter efface l’accès gardé ici. Pour le retirer aussi chez Google : votre compte Google, rubrique
        Sécurité, accès des applications tierces.
      </p>
    </form>
  </ClientSpaceSection>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type {
  AiAssistantClientCalendar,
  AiAssistantClientCalendarStatus,
  AiAssistantClientCalendarUpdate,
} from '~/types/AiAssistantClientSpace'
import type { ClientSpaceCalendarEmits, ClientSpaceCalendarProps } from '~/types/ClientSpaceCalendar'

const STATUS_LABELS: Record<AiAssistantClientCalendarStatus, string> = {
  unavailable: 'Bientôt',
  disconnected: 'Agenda non connecté',
  connected: 'Agenda connecté',
  error: 'À reconnecter',
}

const MAX_TYPES: number = 6

/**
 * The client's Google agenda: connect it, set how the assistant books in it, or disconnect it.
 * @param calendar The agenda section, defaults applied.
 * @param assistantName The assistant's first name.
 * @param isBusy A call is in flight.
 * @param errorMessage Why the last call was refused, if it was.
 * @param hasSaved The last settings save went through.
 * @param readOnly The example space: shown, never connected nor saved.
 */
const props: ClientSpaceCalendarProps = defineProps({
  calendar: { type: Object as PropType<AiAssistantClientCalendar>, required: true },
  assistantName: { type: String, required: true },
  isBusy: { type: Boolean, default: false },
  errorMessage: { type: String as PropType<string | null>, default: null },
  hasSaved: { type: Boolean, default: false },
  readOnly: { type: Boolean, default: false },
})

const emit: EmitFn<ClientSpaceCalendarEmits> = defineEmits<ClientSpaceCalendarEmits>()

const duration: Ref<number> = ref(props.calendar.duration_minutes)
const notice: Ref<number> = ref(props.calendar.min_notice_hours)
const typesText: Ref<string> = ref(props.calendar.appointment_types.join('\n'))
const calendarId: Ref<string> = ref(props.calendar.calendar_id)

/** The kinds typed, one per line (or separated by commas), trimmed and bounded. */
const types: ComputedRef<string[]> = computed((): string[] =>
  typesText.value
    .split(/[\n,]/)
    .map((kind: string): string => kind.trim())
    .filter((kind: string): boolean => kind.length > 0)
    .slice(0, MAX_TYPES),
)

const changes: ComputedRef<AiAssistantClientCalendarUpdate> = computed((): AiAssistantClientCalendarUpdate => {
  const update: AiAssistantClientCalendarUpdate = {}
  if (duration.value !== props.calendar.duration_minutes) update.duration_minutes = duration.value
  if (notice.value !== props.calendar.min_notice_hours) update.min_notice_hours = notice.value
  if (types.value.join('\n') !== props.calendar.appointment_types.join('\n')) update.appointment_types = types.value
  const id: string = calendarId.value.trim() || 'primary'
  if (id !== props.calendar.calendar_id) update.calendar_id = id
  return update
})

const hasChanges: ComputedRef<boolean> = computed((): boolean => Object.keys(changes.value).length > 0)

/**
 * A duration as the client reads it (« 45 min », « 1 h 30 »).
 * @param minutes The duration in minutes.
 * @returns Its label.
 */
function durationLabel(minutes: number): string {
  const hours: number = Math.floor(minutes / 60)
  const rest: number = minutes % 60
  if (hours === 0) return `${rest} min`
  return rest === 0 ? `${hours} h` : `${hours} h ${rest}`
}

/** Send only the settings that changed. */
function submit(): void {
  if (!hasChanges.value) return
  emit('save', changes.value)
}

watch(
  (): AiAssistantClientCalendar => props.calendar,
  (saved: AiAssistantClientCalendar): void => {
    duration.value = saved.duration_minutes
    notice.value = saved.min_notice_hours
    typesText.value = saved.appointment_types.join('\n')
    calendarId.value = saved.calendar_id
  },
)
</script>

<style scoped>
.csc__fields {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
}

.csc__connect,
.csc__form {
  display: grid;
  gap: 14px;
}

.csc__lead {
  margin: 0;
  font-size: 15px;
  line-height: 1.5;
}

.csc__pair {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.csc__types {
  resize: vertical;
  font: inherit;
}

.csc__hint {
  font-size: 12px;
}

.csc__error {
  margin: 0;
  font-size: 13px;
  color: var(--cs-danger);
}
</style>
