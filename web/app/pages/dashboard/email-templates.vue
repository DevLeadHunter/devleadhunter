<template>
  <div>
    <!-- Header -->
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Email Templates</h1>
      <button class="btn-primary" @click="openCreateModal">
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>New Template</span>
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
        <div class="h-4 w-full rounded bg-[#2a2a2a]"></div>
      </div>
    </div>

    <!-- Templates list -->
    <div v-else-if="emailTemplates && emailTemplates.length > 0" class="space-y-2">
      <div v-for="template in emailTemplates" :key="template.id" class="card transition-colors hover:border-[#f9f9f9]">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="mb-1 flex items-center gap-2">
              <h3 class="text-base font-semibold text-[#f9f9f9]">{{ template.name }}</h3>
              <span
                v-if="!template.is_active"
                class="text-muted inline-flex items-center rounded-full bg-[#8b949e]/20 px-2 py-0.5 text-xs font-medium"
              >
                Inactive
              </span>
            </div>
            <p class="text-muted mb-2 text-sm">{{ template.subject }}</p>
            <div class="text-muted text-xs">
              <span v-if="template.variables && template.variables.length > 0">
                <i class="fa-solid fa-code mr-1"></i>{{ template.variables.join(', ') }}
              </span>
              <span v-else>No variables</span>
            </div>
          </div>
          <div class="ml-4 flex gap-2">
            <button class="btn-secondary text-xs" @click="openEditModal(template)">Edit</button>
            <button class="btn-secondary text-xs" @click="handlePreviewTemplate(template)">Preview</button>
            <button
              class="btn-danger flex h-10 w-10 items-center justify-center text-xs"
              @click="confirmDelete(template)"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="card py-12 text-center">
      <i class="fa-solid fa-file-lines text-muted mb-3 text-5xl"></i>
      <p class="text-muted mb-4 text-sm">No templates created</p>
      <div class="flex justify-center">
        <button class="btn-primary" @click="openCreateModal">
          <i class="fa-solid fa-plus mr-1.5"></i>
          <span>Create Your First Template</span>
        </button>
      </div>
    </div>

    <!-- Create/Edit Template Modal -->
    <div
      v-if="showTemplateModal"
      class="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 backdrop-blur-sm"
      @click.self="closeTemplateModal"
    >
      <div class="border-muted mx-4 my-8 w-full max-w-4xl rounded-lg border bg-[#1a1a1a] p-6">
        <h2 class="mb-4 text-base font-semibold text-[#f9f9f9]">
          {{ editingTemplate ? 'Edit Template' : 'New Template' }}
        </h2>

        <form class="space-y-3" @submit.prevent="handleSaveTemplate">
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium"> Template Name * </label>
            <input
              v-model="templateForm.name"
              type="text"
              required
              placeholder="e.g., Website Proposal"
              class="input-field"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium"> Email Subject * </label>
            <input
              v-model="templateForm.subject"
              type="text"
              required
              placeholder="e.g., Website creation for {company_name}"
              class="input-field"
            />
            <p class="text-muted mt-1 text-xs">Use {variable} for dynamic variables</p>
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium"> Email Body (HTML) * </label>
            <textarea
              v-model="templateForm.body_html"
              required
              rows="16"
              placeholder="Hello {name},&#10;&#10;Let me introduce myself..."
              class="input-field font-mono text-xs"
            ></textarea>
            <p class="text-muted mt-1 text-xs">Available variables: {name}, {company_name}, {email}, etc.</p>
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="closeTemplateModal">Cancel</button>
            <button type="submit" :disabled="isSaving" class="btn-primary flex-1">
              {{ isSaving ? 'Saving...' : 'Save Template' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Preview Modal -->
    <div
      v-if="showPreviewModal && previewHtml"
      class="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 backdrop-blur-sm"
      @click.self="showPreviewModal = false"
    >
      <div class="border-muted mx-4 my-8 w-full max-w-4xl rounded-lg border bg-[#1a1a1a] p-6">
        <h2 class="mb-4 text-base font-semibold text-[#f9f9f9]">Template Preview</h2>

        <div class="border-muted rounded border bg-[#050505] p-6">
          <div class="border-muted mb-4 border-b pb-4">
            <p class="text-muted text-xs">Subject:</p>
            <p class="text-sm font-medium text-[#f9f9f9]">{{ previewSubject }}</p>
          </div>
          <!-- eslint-disable-next-line vue/no-v-html -- Preview of user's own email template HTML -->
          <div class="prose prose-invert max-w-none text-sm" v-html="previewHtml"></div>
        </div>

        <button class="btn-primary mt-6 w-full" @click="showPreviewModal = false">Close</button>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <UiConfirmModal
      ref="confirmModal"
      title="Delete Template"
      :message="`Are you sure you want to delete the template '${templateToDelete?.name}'? This action cannot be undone.`"
      confirm-text="Delete"
      cancel-text="Cancel"
      @confirm="handleDeleteTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { EmailTemplate } from '~/types'
import {
  getEmailTemplates,
  createEmailTemplate,
  updateEmailTemplate,
  deleteEmailTemplate,
  previewEmailTemplate,
} from '~/services/emailTemplatesService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()

// State
const emailTemplates = ref<EmailTemplate[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const showTemplateModal = ref(false)
const showPreviewModal = ref(false)
const editingTemplate = ref<EmailTemplate | null>(null)
const previewSubject = ref('')
const previewHtml = ref('')
const templateToDelete = ref<EmailTemplate | null>(null)
const confirmModal = ref<{ open: () => void; close: () => void } | null>(null)

// Form data
const templateForm = ref({
  name: '',
  subject: '',
  body_html: '',
})

// Load templates
const loadTemplates = async () => {
  try {
    isLoading.value = true
    emailTemplates.value = await getEmailTemplates()
  } catch (error) {
    toast.error('Failed to load templates')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// Open create modal
const openCreateModal = () => {
  editingTemplate.value = null
  templateForm.value = {
    name: '',
    subject: '',
    body_html: '',
  }
  showTemplateModal.value = true
}

// Open edit modal
const openEditModal = (template: EmailTemplate) => {
  editingTemplate.value = template
  templateForm.value = {
    name: template.name,
    subject: template.subject,
    body_html: template.body_html,
  }
  showTemplateModal.value = true
}

// Close template modal
const closeTemplateModal = () => {
  showTemplateModal.value = false
  editingTemplate.value = null
}

// Save template
const handleSaveTemplate = async () => {
  try {
    isSaving.value = true

    if (editingTemplate.value) {
      // Update existing template
      const updated = await updateEmailTemplate(editingTemplate.value.id, templateForm.value)
      const index = emailTemplates.value.findIndex((t) => t.id === updated.id)
      if (index !== -1) {
        emailTemplates.value[index] = updated
      }
      toast.success('Template updated')
    } else {
      // Create new template
      const newTemplate = await createEmailTemplate(templateForm.value)
      if (!emailTemplates.value) {
        emailTemplates.value = []
      }
      emailTemplates.value.unshift(newTemplate)
      toast.success('Template created successfully')
    }

    closeTemplateModal()
  } catch (error: unknown) {
    toast.error(error.response?.data?.detail || 'Failed to save template')
    console.error(error)
  } finally {
    isSaving.value = false
  }
}

// Preview template
const handlePreviewTemplate = async (template: EmailTemplate) => {
  try {
    // Use sample data for preview
    const sampleVariables: Record<string, string> = {
      name: 'Jean Dupont',
      company_name: 'Restaurant Le Gourmet',
      email: 'contact@legourmet.fr',
      phone: '01 23 45 67 89',
    }

    const preview = await previewEmailTemplate(template.id, sampleVariables)
    previewSubject.value = preview.subject
    previewHtml.value = preview.body_html
    showPreviewModal.value = true
  } catch {
    // If preview fails, show template as-is
    previewSubject.value = template.subject
    previewHtml.value = template.body_html
    showPreviewModal.value = true
  }
}

// Confirm delete
const confirmDelete = (template: EmailTemplate) => {
  templateToDelete.value = template
  confirmModal.value?.open()
}

// Delete template
const handleDeleteTemplate = async () => {
  if (!templateToDelete.value) return

  try {
    await deleteEmailTemplate(templateToDelete.value.id)
    if (emailTemplates.value) {
      emailTemplates.value = emailTemplates.value.filter((t) => t.id !== templateToDelete.value!.id)
    }
    toast.success('Template deleted')
  } catch (error) {
    toast.error('Failed to delete template')
    console.error(error)
  } finally {
    templateToDelete.value = null
  }
}

onMounted(() => {
  loadTemplates()
})
</script>
