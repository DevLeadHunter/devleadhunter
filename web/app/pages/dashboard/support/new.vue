<template>
  <div class="mx-auto max-w-2xl space-y-8">
    <div>
      <NuxtLink
        to="/dashboard/support"
        class="text-muted mb-4 inline-flex items-center gap-1.5 text-xs font-medium transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Support
      </NuxtLink>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Nouveau ticket</h1>
      <p class="text-muted mt-2 text-sm leading-relaxed">
        Décrivez votre problème. On vous répond directement dans le fil de conversation.
      </p>
    </div>

    <form class="space-y-5" @submit.prevent="handleSubmit">
      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium" for="subject">
          Sujet <span class="text-[var(--app-red)]">*</span>
        </label>
        <input
          id="subject"
          v-model="form.subject"
          type="text"
          required
          minlength="4"
          class="input-field"
          placeholder="Ex : les crédits ont été débités sans résultat"
        />
      </div>

      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium" for="topic">
          Catégorie <span class="text-[var(--app-red)]">*</span>
        </label>
        <select id="topic" v-model="form.topic" required class="input-field">
          <option disabled value="">Sélectionner une catégorie</option>
          <option v-for="topic in topics" :key="topic.value" :value="topic.value">{{ topic.label }}</option>
        </select>
      </div>

      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium" for="message">
          Détails <span class="text-[var(--app-red)]">*</span>
        </label>
        <textarea
          id="message"
          v-model="form.message"
          rows="7"
          required
          minlength="10"
          class="input-field h-auto py-2.5"
          placeholder="Ce que vous attendiez, ce qui s'est passé, et quand."
        ></textarea>
      </div>

      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium">Captures d'écran</label>
        <label
          class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-[var(--app-line)] px-6 py-8 text-center transition-colors hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]"
        >
          <span class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--app-surface-2)]">
            <UIcon name="i-lucide-image-plus" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>
          <span class="text-sm font-medium text-[var(--app-ink)]">Ajouter des images</span>
          <span class="text-muted text-xs">PNG, JPG ou WEBP — 8 Mo max</span>
          <input
            ref="attachmentInput"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            class="hidden"
            multiple
            @change="handleAttachments"
          />
        </label>

        <div v-if="previews.length" class="mt-3 grid gap-3 sm:grid-cols-3">
          <figure
            v-for="(preview, index) in previews"
            :key="preview.url"
            class="relative overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
          >
            <img :src="preview.url" :alt="preview.name" class="h-24 w-full object-cover" />
            <figcaption class="text-muted truncate px-2 py-1.5 text-[11px]">{{ preview.name }}</figcaption>
            <button
              type="button"
              class="btn-danger absolute top-1.5 right-1.5 flex h-6 w-6 items-center justify-center !p-0"
              :aria-label="`Retirer ${preview.name}`"
              @click="removeAttachment(index)"
            >
              <UIcon name="i-lucide-x" class="h-3 w-3" />
            </button>
          </figure>
        </div>
      </div>

      <UiCollapsibleCard icon="i-lucide-lightbulb" title="Comment décrire votre problème" suffix="pour aller plus vite">
        <ul class="space-y-2.5 px-4 py-4">
          <li v-for="tip in WRITING_TIPS" :key="tip" class="text-muted flex items-start gap-2 text-xs leading-relaxed">
            <UIcon name="i-lucide-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
            <span>{{ tip }}</span>
          </li>
        </ul>
      </UiCollapsibleCard>

      <div class="flex items-center justify-end gap-4">
        <NuxtLink to="/dashboard/support" class="text-muted text-xs font-medium hover:text-[var(--app-ink)]">
          Annuler
        </NuxtLink>
        <button type="submit" class="btn-primary" :disabled="isSubmitting">
          <UIcon v-if="isSubmitting" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
          {{ isSubmitting ? 'Création…' : 'Créer le ticket' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script lang="ts" setup>
import type { SupportTicketDetail } from '~/types/index'
import type { UseToastReturn } from '~/types/Composables'
import type { Ref } from 'vue'
import type { SupportTicketTopic, SupportTopicOption } from '~/types'
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '~/composables/useToast'
import { SupportService } from '~/services/supportService'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

/** Short tips shown in the folded « comment décrire » card. */
const WRITING_TIPS: string[] = [
  'Les étapes suivies et le moment où ça a échoué.',
  'Les dates, campagnes ou noms de prospects concernés.',
  "Une capture nette du message d'erreur ou de l'écran inattendu.",
]

/** Accepted image types for attachments. */
const ALLOWED_TYPES: string[] = ['image/png', 'image/jpeg', 'image/webp']

/** Maximum attachment size, in bytes. */
const MAX_ATTACHMENT_BYTES: number = 8 * 1024 * 1024

const toast: UseToastReturn = useToast()
const router: ReturnType<typeof useRouter> = useRouter()

const topics: Ref<SupportTopicOption[]> = ref([])
const isSubmitting: Ref<boolean> = ref(false)
const attachments: Ref<File[]> = ref([])
const previews: Ref<Array<{ url: string; name: string }>> = ref([])
const attachmentInput: Ref<HTMLInputElement | null> = ref(null)

const form: { subject: string; topic: '' | SupportTicketTopic; message: string } = reactive<{
  subject: string
  topic: SupportTicketTopic | ''
  message: string
}>({
  subject: '',
  topic: '',
  message: '',
})

/**
 * Stage the picked images after validating type and size.
 * @param event - Native change event of the file input.
 */
function handleAttachments(event: Event): void {
  const input: HTMLInputElement = event.target as HTMLInputElement
  for (const file of Array.from(input.files ?? [])) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error('Format non pris en charge. Utilisez PNG, JPG ou WEBP.')
      continue
    }
    if (file.size > MAX_ATTACHMENT_BYTES) {
      toast.error('Fichier trop volumineux (8 Mo maximum par image).')
      continue
    }
    attachments.value.push(file)
    previews.value.push({ url: URL.createObjectURL(file), name: file.name })
  }
  if (attachmentInput.value) attachmentInput.value.value = ''
}

/**
 * Remove a staged image and release its preview URL.
 * @param index - Position in the staged list.
 */
function removeAttachment(index: number): void {
  const preview: { url: string; name: string } | undefined = previews.value[index]
  if (preview) URL.revokeObjectURL(preview.url)
  attachments.value.splice(index, 1)
  previews.value.splice(index, 1)
}

/**
 * Load the selectable ticket topics.
 * @returns A promise resolving once loaded.
 */
async function loadTopics(): Promise<void> {
  try {
    topics.value = await SupportService.getTopics()
  } catch {
    toast.error('Impossible de charger les catégories pour le moment.')
  }
}

/**
 * Create the ticket and jump to its conversation.
 * @returns A promise resolving once the ticket is created.
 */
async function handleSubmit(): Promise<void> {
  if (!form.topic) {
    toast.warning('Sélectionnez une catégorie.')
    return
  }
  try {
    isSubmitting.value = true
    const ticket: SupportTicketDetail = await SupportService.createTicket({
      subject: form.subject,
      topic: form.topic,
      message: form.message,
      attachments: attachments.value,
    })
    toast.success('Ticket créé.')
    await router.push(`/dashboard/support/${ticket.id}`)
  } catch {
    toast.error('Impossible de créer le ticket. Réessayez plus tard.')
  } finally {
    isSubmitting.value = false
  }
}

onMounted((): void => {
  void loadTopics()
})

onBeforeUnmount((): void => {
  previews.value.forEach((preview: { url: string; name: string }): void => URL.revokeObjectURL(preview.url))
})
</script>
