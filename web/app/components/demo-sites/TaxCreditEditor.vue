<template>
  <div class="space-y-4">
    <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-3">
      <UiSwitch
        id="tax-credit-section-shown"
        :model-value="draft.isSectionShown"
        label="Afficher la section"
        @update:model-value="toggleSection"
      />
      <p class="mt-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        Pour une entreprise déclarée « services à la personne » : la moitié de la facture d'entretien revient au client
        en crédit d'impôt. La section s'affiche sous les prestations et sa question s'ajoute à la FAQ.
      </p>
    </div>

    <template v-if="draft.isSectionShown">
      <div>
        <label for="tax-credit-heading" class="app-label mb-1.5 block">Titre</label>
        <input
          id="tax-credit-heading"
          :value="draft.heading"
          type="text"
          class="input-field"
          maxlength="120"
          placeholder="Votre entretien de jardin à moitié prix"
          @input="updateTextField('heading', ($event.target as HTMLInputElement).value)"
        />
        <p v-if="!hasHeading" class="mt-1.5 text-[11px] text-[var(--app-red)]">
          Sans titre, la section ne peut pas être publiée.
        </p>
      </div>

      <div>
        <label for="tax-credit-lead" class="app-label mb-1.5 block">Explication</label>
        <textarea
          id="tax-credit-lead"
          :value="draft.lead"
          class="input-field field-sizing-content min-h-20 resize-none leading-relaxed"
          rows="3"
          maxlength="600"
          placeholder="Ce que le client récupère, en une ou deux phrases"
          @input="updateTextField('lead', ($event.target as HTMLTextAreaElement).value)"
        />
      </div>

      <div>
        <div class="mb-1.5 flex items-center justify-between gap-2">
          <p id="tax-credit-points-label" class="app-label">Points clés</p>
          <span class="text-[10px] text-[var(--app-ink-soft)] tabular-nums">
            {{ draft.points.length }}/{{ maximumPoints }}
          </span>
        </div>
        <ul v-if="draft.points.length" class="space-y-2" aria-labelledby="tax-credit-points-label">
          <li v-for="(point, index) in draft.points" :key="index" class="flex items-center gap-2">
            <input
              :value="point"
              type="text"
              class="input-field min-w-0 flex-1"
              maxlength="160"
              :aria-label="`Point ${index + 1}`"
              @input="updatePoint(index, ($event.target as HTMLInputElement).value)"
            />
            <button
              type="button"
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-red)]"
              :aria-label="`Retirer le point ${index + 1}`"
              @click="removePoint(index)"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />
            </button>
          </li>
        </ul>
        <p
          v-else
          class="rounded-lg border border-dashed border-[var(--app-line)] p-3 text-xs text-[var(--app-ink-soft)]"
        >
          Aucun point : la section n'affiche que le titre et l'explication.
        </p>
        <button
          type="button"
          class="btn-secondary mt-2 inline-flex w-full items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!canAddPoint"
          :title="canAddPoint ? undefined : `${maximumPoints} points maximum`"
          @click="addPoint"
        >
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Ajouter un point
        </button>
      </div>

      <div>
        <label for="tax-credit-note" class="app-label mb-1.5 block">Mention</label>
        <input
          id="tax-credit-note"
          :value="draft.note"
          type="text"
          class="input-field"
          maxlength="300"
          placeholder="Plafond de 5 000 € par an et par foyer"
          @input="updateTextField('note', ($event.target as HTMLInputElement).value)"
        />
        <p class="mt-1.5 text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
          En petit sous les points : le plafond, la condition.
        </p>
      </div>

      <fieldset class="space-y-2 rounded-xl border border-[var(--app-line)] p-3">
        <legend class="app-label px-1">Question ajoutée à la FAQ</legend>
        <div>
          <label for="tax-credit-faq-question" class="mb-1 block text-[11px] text-[var(--app-ink-soft)]"
            >Question</label
          >
          <input
            id="tax-credit-faq-question"
            :value="draft.faqQuestion"
            type="text"
            class="input-field"
            maxlength="160"
            placeholder="Puis-je bénéficier du crédit d'impôt de 50 % ?"
            @input="updateTextField('faqQuestion', ($event.target as HTMLInputElement).value)"
          />
        </div>
        <div>
          <label for="tax-credit-faq-answer" class="mb-1 block text-[11px] text-[var(--app-ink-soft)]">Réponse</label>
          <textarea
            id="tax-credit-faq-answer"
            :value="draft.faqAnswer"
            class="input-field field-sizing-content min-h-20 resize-none leading-relaxed"
            rows="3"
            maxlength="600"
            placeholder="La réponse, en deux ou trois phrases"
            @input="updateTextField('faqAnswer', ($event.target as HTMLTextAreaElement).value)"
          />
        </div>
        <p class="text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
          Ajoutée quand la question et la réponse sont remplies, sauf si la FAQ parle déjà du crédit d'impôt.
        </p>
      </fieldset>
    </template>

    <p
      v-else
      class="rounded-xl border border-dashed border-[var(--app-line)] p-4 text-xs leading-relaxed text-[var(--app-ink-soft)]"
    >
      La section et sa question de FAQ sont retirées du site à la publication.
    </p>
  </div>
</template>

<script lang="ts" setup>
import type {
  TaxCreditDraft,
  TaxCreditDraftTextField,
  TaxCreditEditorEmits,
  TaxCreditEditorProps,
} from '~/types/TaxCreditEditor'
import type { ComputedRef, EmitFn, PropType } from 'vue'
import { computed } from 'vue'
import { TaxCreditSection } from '~/utils/taxCreditSection'

const props: TaxCreditEditorProps = defineProps({
  draft: {
    type: Object as PropType<TaxCreditDraft>,
    required: true,
  },
})

const emit: EmitFn<TaxCreditEditorEmits> = defineEmits<TaxCreditEditorEmits>()

const maximumPoints: number = TaxCreditSection.MAX_POINTS

const hasHeading: ComputedRef<boolean> = computed((): boolean => props.draft.heading.trim().length > 0)

const canAddPoint: ComputedRef<boolean> = computed((): boolean => props.draft.points.length < maximumPoints)

/**
 * Show or hide the section on the site; switching on a blank draft proposes texts for a garden-maintenance provider.
 * @param isShown - Whether the section is shown.
 */
function toggleSection(isShown: boolean): void {
  if (isShown && TaxCreditSection.isBlank(props.draft)) {
    emit('update:draft', TaxCreditSection.proposedDraft())
    return
  }
  emit('update:draft', { ...props.draft, isSectionShown: isShown })
}

/**
 * Replace one text of the section.
 * @param field - The text edited.
 * @param value - Its new value.
 */
function updateTextField(field: TaxCreditDraftTextField, value: string): void {
  emit('update:draft', { ...props.draft, [field]: value })
}

/**
 * Replace one key point.
 * @param index - Position of the point.
 * @param value - Its new text.
 */
function updatePoint(index: number, value: string): void {
  const points: string[] = [...props.draft.points]
  points[index] = value
  emit('update:draft', { ...props.draft, points })
}

/**
 * Add an empty key point at the end, up to the section's maximum.
 */
function addPoint(): void {
  if (!canAddPoint.value) {
    return
  }

  emit('update:draft', { ...props.draft, points: [...props.draft.points, ''] })
}

/**
 * Remove one key point.
 * @param index - Position of the point.
 */
function removePoint(index: number): void {
  emit('update:draft', {
    ...props.draft,
    points: props.draft.points.filter((_point: string, position: number): boolean => position !== index),
  })
}
</script>
