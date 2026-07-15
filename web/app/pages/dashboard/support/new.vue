<template>
  <div>
    <UiLoader v-if="isSubmitting" />
    <div v-else class="space-y-8">
      <NuxtLink to="/dashboard/support" class="btn-secondary inline-flex w-fit items-center gap-2">
        <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
        Retour aux tickets
      </NuxtLink>

      <header class="space-y-2">
        <h1 class="text-xl leading-tight font-semibold text-[var(--app-ink)]">
          Signaler un problème ou demander de l'aide
        </h1>
        <p class="max-w-2xl text-sm text-[var(--app-ink-soft)]">
          Décrivez ce qui s'est passé, donnez un maximum de contexte et joignez des captures d'écran si vous en avez.
          Notre équipe vous répondra directement dans le fil de conversation.
        </p>
      </header>

      <div class="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <form class="card space-y-6 p-6" @submit.prevent="handleSubmit">
          <div class="space-y-2">
            <label class="text-sm font-medium text-[var(--app-ink)]" for="subject">Sujet</label>
            <input
              id="subject"
              v-model="form.subject"
              type="text"
              required
              minlength="4"
              class="input-field"
              placeholder="Donnez un titre court à votre demande"
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium text-[var(--app-ink)]" for="topic">Catégorie</label>
            <select id="topic" v-model="form.topic" required class="input-field">
              <option disabled value="">Sélectionner une catégorie</option>
              <option v-for="topic in topics" :key="topic.value" :value="topic.value">
                {{ topic.label }}
              </option>
            </select>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium text-[var(--app-ink)]" for="message"> Détails </label>
            <textarea
              id="message"
              v-model="form.message"
              rows="7"
              required
              minlength="10"
              class="input-field"
              placeholder="Expliquez ce que vous attendiez, ce qui s'est passé et comment nous pouvons aider."
            ></textarea>
          </div>

          <div class="space-y-3">
            <label class="text-sm font-medium text-[var(--app-ink)]">Captures d'écran (optionnel)</label>
            <label
              class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--app-line)] bg-[var(--app-bg)] px-4 py-6 text-xs text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-accent-ink)]/50 hover:text-[var(--app-ink)]"
            >
              <UIcon name="i-lucide-cloud-upload" class="h-5 w-5 text-[var(--app-accent-ink)]" />
              <span>Déposez une ou plusieurs images — JPG, PNG ou WEBP (8 Mo max par fichier)</span>
              <input
                ref="attachmentInput"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                class="hidden"
                multiple
                @change="handleAttachments"
              />
            </label>

            <div v-if="previews.length > 0" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <figure
                v-for="(preview, index) in previews"
                :key="preview.url"
                class="relative overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
              >
                <img :src="preview.url" :alt="preview.name" class="h-32 w-full object-cover" />
                <figcaption class="truncate px-3 py-2 text-[11px] text-[var(--app-ink-soft)]">
                  {{ preview.name }}
                </figcaption>
                <button
                  type="button"
                  class="absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--app-bg)]/80 text-[11px] text-[var(--app-ink)] transition-colors hover:bg-[var(--app-red)] hover:text-white"
                  @click="removeAttachment(index)"
                >
                  <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
                </button>
              </figure>
            </div>
          </div>

          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <NuxtLink to="/dashboard/support" class="text-xs text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]">
              Annuler
            </NuxtLink>
            <button type="submit" class="btn-primary w-full gap-2 sm:w-auto" :disabled="isSubmitting">
              <span>Créer le ticket</span>
            </button>
          </div>
        </form>

        <aside class="card space-y-6 p-6">
          <div>
            <h2 class="text-sm font-semibold tracking-wide text-[var(--app-ink)] uppercase">
              Pour accélérer le traitement
            </h2>
            <ul class="mt-3 space-y-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              <li class="flex items-start gap-2">
                <UIcon name="i-lucide-circle-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]" />
                Décrivez les étapes suivies et le moment où ça a échoué (ex. crédits consommés sans résultat).
              </li>
              <li class="flex items-start gap-2">
                <UIcon name="i-lucide-circle-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]" />
                Mentionnez les dates, campagnes ou noms de prospects pour retrouver l'événement rapidement.
              </li>
              <li class="flex items-start gap-2">
                <UIcon name="i-lucide-circle-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]" />
                Joignez des captures nettes du message d'erreur ou de l'écran inattendu.
              </li>
            </ul>
          </div>

          <div class="space-y-3 border-t border-[var(--app-line)] pt-4">
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Sujets fréquents</h3>
            <ul class="space-y-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              <li>
                <strong class="text-[var(--app-ink)]">Crédits & facturation</strong> — indiquez le nombre de crédits
                utilisés et le résultat attendu.
              </li>
              <li>
                <strong class="text-[var(--app-ink)]">Signalement de bug</strong> — précisez le parcours, le navigateur
                et la page concernée.
              </li>
              <li>
                <strong class="text-[var(--app-ink)]">Demande de remboursement</strong> — incluez le montant et la date
                du paiement.
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'
import type { SupportTicketTopic, SupportTopicOption } from '~/types'
import * as supportService from '~/services/supportService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()
const router = useRouter()

const topics = ref<SupportTopicOption[]>([])
const isSubmitting = ref(false)

const form = reactive<{
  subject: string
  topic: SupportTicketTopic | ''
  message: string
}>({
  subject: '',
  topic: '',
  message: '',
})

const attachments = ref<File[]>([])
const previews = ref<Array<{ url: string; name: string }>>([])
const attachmentInput = ref<HTMLInputElement | null>(null)

function resetFileInput(): void {
  if (attachmentInput.value) {
    attachmentInput.value.value = ''
  }
}

function revokePreview(index: number): void {
  URL.revokeObjectURL(previews.value[index].url)
}

function handleAttachments(event: Event): void {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])

  files.forEach((file) => {
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      toast.error('Format non pris en charge. Utilisez PNG, JPG ou WEBP.')
      return
    }
    if (file.size > 8 * 1024 * 1024) {
      toast.error('Fichier trop volumineux (8 Mo maximum par image).')
      return
    }

    attachments.value.push(file)
    previews.value.push({
      url: URL.createObjectURL(file),
      name: file.name,
    })
  })

  resetFileInput()
}

function removeAttachment(index: number): void {
  attachments.value.splice(index, 1)
  revokePreview(index)
  previews.value.splice(index, 1)
}

async function loadTopics(): Promise<void> {
  try {
    topics.value = await supportService.getTopics()
  } catch (error) {
    console.error('Failed to load support topics', error)
    toast.error('Impossible de charger les catégories pour le moment.')
  }
}

async function handleSubmit(): Promise<void> {
  if (!form.topic) {
    toast.warning('Sélectionnez une catégorie.')
    return
  }
  try {
    isSubmitting.value = true
    const ticket = await supportService.createTicket({
      subject: form.subject,
      topic: form.topic,
      message: form.message,
      attachments: attachments.value,
    })

    toast.success('Ticket créé.')
    await router.push(`/dashboard/support/${ticket.id}`)
  } catch (error) {
    console.error('Failed to create ticket', error)
    toast.error('Impossible de créer le ticket. Réessayez plus tard.')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  void loadTopics()
})

onBeforeUnmount(() => {
  previews.value.forEach((preview) => URL.revokeObjectURL(preview.url))
})
</script>
