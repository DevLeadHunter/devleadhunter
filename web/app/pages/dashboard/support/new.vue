<template>
  <div>
    <UiLoader v-if="isSubmitting" />
    <div v-else class="space-y-8">
      <NuxtLink to="/dashboard/support" class="btn-secondary inline-flex w-fit items-center gap-2">
        <i class="fa-solid fa-arrow-left"></i>
        Back to tickets
      </NuxtLink>

      <header class="space-y-2">
        <h1 class="text-xl leading-tight font-semibold text-[var(--app-ink)]">Report an issue or request help</h1>
        <p class="max-w-2xl text-sm text-[var(--app-ink-soft)]">
          Describe what happened, add as much context as possible and attach screenshots if you have them. Our team will
          get back to you directly in the conversation thread.
        </p>
      </header>

      <div class="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <form class="card space-y-6 p-6" @submit.prevent="handleSubmit">
          <div class="space-y-2">
            <label class="text-sm font-medium text-[var(--app-ink)]" for="subject">Subject</label>
            <input
              id="subject"
              v-model="form.subject"
              type="text"
              required
              minlength="4"
              class="input-field"
              placeholder="Give your request a short title"
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium text-[var(--app-ink)]" for="topic">Category</label>
            <select id="topic" v-model="form.topic" required class="input-field">
              <option disabled value="">Select a topic</option>
              <option v-for="topic in topics" :key="topic.value" :value="topic.value">
                {{ topic.label }}
              </option>
            </select>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium text-[var(--app-ink)]" for="message"> Details </label>
            <textarea
              id="message"
              v-model="form.message"
              rows="7"
              required
              minlength="10"
              class="input-field"
              placeholder="Explain what you expected, what happened and how we can help."
            ></textarea>
          </div>

          <div class="space-y-3">
            <label class="text-sm font-medium text-[var(--app-ink)]">Screenshots (optional)</label>
            <label
              class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--app-line)] bg-[var(--app-bg)] px-4 py-6 text-xs text-[var(--app-ink-soft)] transition-colors hover:border-[var(--app-accent-ink)]/50 hover:text-[var(--app-ink)]"
            >
              <i class="fa-solid fa-cloud-arrow-up text-lg text-[var(--app-accent-ink)]"></i>
              <span>Upload one or many images — JPG, PNG or WEBP (8 MB max per file)</span>
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
                  <i class="fa-solid fa-xmark"></i>
                </button>
              </figure>
            </div>
          </div>

          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <NuxtLink to="/dashboard/support" class="text-xs text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]">
              Cancel
            </NuxtLink>
            <button type="submit" class="btn-primary w-full gap-2 sm:w-auto" :disabled="isSubmitting">
              <span>Create ticket</span>
            </button>
          </div>
        </form>

        <aside class="card space-y-6 bg-[#101216] p-6">
          <div>
            <h2 class="text-sm font-semibold tracking-wide text-[var(--app-ink)] uppercase">Tips to speed things up</h2>
            <ul class="mt-3 space-y-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              <li class="flex items-start gap-2">
                <i class="fa-regular fa-circle-check mt-0.5 text-[var(--app-accent-ink)]"></i>
                Share the steps you followed and where it went wrong (e.g. credits consumed without results).
              </li>
              <li class="flex items-start gap-2">
                <i class="fa-regular fa-circle-check mt-0.5 text-[var(--app-accent-ink)]"></i>
                Mention dates, campaigns or prospect names so we can find the event quickly.
              </li>
              <li class="flex items-start gap-2">
                <i class="fa-regular fa-circle-check mt-0.5 text-[var(--app-accent-ink)]"></i>
                Attach clear screenshots of the error message or unexpected screen.
              </li>
            </ul>
          </div>

          <div class="space-y-3 border-t border-[#1f252d] pt-4">
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Popular topics</h3>
            <ul class="space-y-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
              <li>
                <strong class="text-[var(--app-ink)]">Credits & billing</strong> — tell us how many credits were used
                and what result you expected.
              </li>
              <li>
                <strong class="text-[var(--app-ink)]">Bug report</strong> — explain the workflow, browser, and page
                where the issue appears.
              </li>
              <li>
                <strong class="text-[var(--app-ink)]">Refund request</strong> — include the payment amount and date if
                you ask for a refund.
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
      toast.error('Unsupported format. Please use PNG, JPG or WEBP.')
      return
    }
    if (file.size > 8 * 1024 * 1024) {
      toast.error('File is too large (maximum 8 MB per image).')
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
    toast.error('Unable to load support topics right now.')
  }
}

async function handleSubmit(): Promise<void> {
  if (!form.topic) {
    toast.warning('Please select a topic.')
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

    toast.success('Ticket created successfully.')
    await router.push(`/dashboard/support/${ticket.id}`)
  } catch (error) {
    console.error('Failed to create ticket', error)
    toast.error('We could not create your ticket. Please try again later.')
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
