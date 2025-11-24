<template>
  <div>
    <!-- Header -->
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Email Templates</h1>
      <button
        @click="openCreateModal"
        class="btn-primary"
      >
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>New Template</span>
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 bg-[#2a2a2a] rounded w-3/4"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
      </div>
    </div>

    <!-- Templates list -->
    <div v-else-if="emailTemplates && emailTemplates.length > 0" class="space-y-2">
      <div
        v-for="template in emailTemplates"
        :key="template.id"
        class="card hover:border-[#f9f9f9] transition-colors"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="text-base font-semibold text-[#f9f9f9]">{{ template.name }}</h3>
              <span
                v-if="!template.is_active"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#8b949e]/20 text-muted"
              >
                Inactive
              </span>
            </div>
            <p class="text-sm text-muted mb-2">{{ template.subject }}</p>
            <div class="text-xs text-muted">
              <span v-if="template.variables && template.variables.length > 0">
                <i class="fa-solid fa-code mr-1"></i>{{ template.variables.join(', ') }}
              </span>
              <span v-else>No variables</span>
            </div>
          </div>
          <div class="flex gap-2 ml-4">
            <button
              @click="openEditModal(template)"
              class="btn-secondary text-xs"
            >
              Edit
            </button>
            <button
              @click="handlePreviewTemplate(template)"
              class="btn-secondary text-xs"
            >
              Preview
            </button>
            <button
              @click="confirmDelete(template)"
              class="btn-danger text-xs w-10 h-10 flex items-center justify-center"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="card text-center py-12">
      <i class="fa-solid fa-file-lines text-5xl text-muted mb-3"></i>
      <p class="text-muted text-sm mb-4">No templates created</p>
      <div class="flex justify-center">
        <button
          @click="openCreateModal"
          class="btn-primary"
        >
          <i class="fa-solid fa-plus mr-1.5"></i>
          <span>Create Your First Template</span>
        </button>
      </div>
    </div>

    <!-- Create/Edit Template Modal -->
    <div
      v-if="showTemplateModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 overflow-y-auto backdrop-blur-sm"
      @click.self="closeTemplateModal"
    >
      <div class="bg-[#1a1a1a] border border-muted rounded-lg p-6 max-w-4xl w-full mx-4 my-8">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">
          {{ editingTemplate ? 'Edit Template' : 'New Template' }}
        </h2>
        
        <form @submit.prevent="handleSaveTemplate" class="space-y-3">
          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">
              Template Name *
            </label>
            <input
              v-model="templateForm.name"
              type="text"
              required
              placeholder="e.g., Website Proposal"
              class="input-field"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">
              Email Subject *
            </label>
            <input
              v-model="templateForm.subject"
              type="text"
              required
              placeholder="e.g., Website creation for {company_name}"
              class="input-field"
            />
            <p class="text-xs text-muted mt-1">
              Use {variable} for dynamic variables
            </p>
          </div>

          <div>
            <label class="block text-xs font-medium text-muted mb-1.5">
              Email Body (HTML) *
            </label>
            <textarea
              v-model="templateForm.body_html"
              required
              rows="16"
              placeholder="Hello {name},&#10;&#10;Let me introduce myself..."
              class="input-field font-mono text-xs"
            ></textarea>
            <p class="text-xs text-muted mt-1">
              Available variables: {name}, {company_name}, {email}, etc.
            </p>
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="closeTemplateModal"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isSaving"
              class="btn-primary flex-1"
            >
              {{ isSaving ? 'Saving...' : 'Save Template' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Preview Modal -->
    <div
      v-if="showPreviewModal && previewHtml"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 overflow-y-auto backdrop-blur-sm"
      @click.self="showPreviewModal = false"
    >
      <div class="bg-[#1a1a1a] border border-muted rounded-lg p-6 max-w-4xl w-full mx-4 my-8">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Template Preview</h2>
        
        <div class="bg-[#050505] border border-muted rounded p-6">
          <div class="mb-4 pb-4 border-b border-muted">
            <p class="text-xs text-muted">Subject:</p>
            <p class="text-sm font-medium text-[#f9f9f9]">{{ previewSubject }}</p>
          </div>
          <div class="prose prose-invert max-w-none text-sm" v-html="previewHtml"></div>
        </div>

        <button
          @click="showPreviewModal = false"
          class="mt-6 w-full btn-primary"
        >
          Close
        </button>
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
import { ref, onMounted } from 'vue';
import type { EmailTemplate } from '~/types';
import {
  getEmailTemplates,
  createEmailTemplate,
  updateEmailTemplate,
  deleteEmailTemplate,
  previewEmailTemplate
} from '~/services/emailTemplatesService';
import { useToast } from '~/composables/useToast';

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

const toast = useToast();

// State
const emailTemplates = ref<EmailTemplate[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const showTemplateModal = ref(false);
const showPreviewModal = ref(false);
const editingTemplate = ref<EmailTemplate | null>(null);
const previewSubject = ref('');
const previewHtml = ref('');
const templateToDelete = ref<EmailTemplate | null>(null);
const confirmModal = ref<any>(null);

// Form data
const templateForm = ref({
  name: '',
  subject: '',
  body_html: ''
});

// Load templates
const loadTemplates = async () => {
  try {
    isLoading.value = true;
    emailTemplates.value = await getEmailTemplates();
  } catch (error) {
    toast.error('Failed to load templates');
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

// Open create modal
const openCreateModal = () => {
  editingTemplate.value = null;
  templateForm.value = {
    name: '',
    subject: '',
    body_html: ''
  };
  showTemplateModal.value = true;
};

// Open edit modal
const openEditModal = (template: EmailTemplate) => {
  editingTemplate.value = template;
  templateForm.value = {
    name: template.name,
    subject: template.subject,
    body_html: template.body_html
  };
  showTemplateModal.value = true;
};

// Close template modal
const closeTemplateModal = () => {
  showTemplateModal.value = false;
  editingTemplate.value = null;
};

// Save template
const handleSaveTemplate = async () => {
  try {
    isSaving.value = true;
    
    if (editingTemplate.value) {
      // Update existing template
      const updated = await updateEmailTemplate(editingTemplate.value.id, templateForm.value);
      const index = emailTemplates.value.findIndex(t => t.id === updated.id);
      if (index !== -1) {
        emailTemplates.value[index] = updated;
      }
      toast.success('Template updated');
    } else {
      // Create new template
      const newTemplate = await createEmailTemplate(templateForm.value);
      if (!emailTemplates.value) {
        emailTemplates.value = [];
      }
      emailTemplates.value.unshift(newTemplate);
      toast.success('Template created successfully');
    }
    
    closeTemplateModal();
  } catch (error: any) {
    toast.error(error.response?.data?.detail || 'Failed to save template');
    console.error(error);
  } finally {
    isSaving.value = false;
  }
};

// Preview template
const handlePreviewTemplate = async (template: EmailTemplate) => {
  try {
    // Use sample data for preview
    const sampleVariables: Record<string, string> = {
      name: 'Jean Dupont',
      company_name: 'Restaurant Le Gourmet',
      email: 'contact@legourmet.fr',
      phone: '01 23 45 67 89'
    };
    
    const preview = await previewEmailTemplate(template.id, sampleVariables);
    previewSubject.value = preview.subject;
    previewHtml.value = preview.body_html;
    showPreviewModal.value = true;
  } catch (error) {
    // If preview fails, show template as-is
    previewSubject.value = template.subject;
    previewHtml.value = template.body_html;
    showPreviewModal.value = true;
  }
};

// Confirm delete
const confirmDelete = (template: EmailTemplate) => {
  templateToDelete.value = template;
  confirmModal.value?.open();
};

// Delete template
const handleDeleteTemplate = async () => {
  if (!templateToDelete.value) return;
  
  try {
    await deleteEmailTemplate(templateToDelete.value.id);
    if (emailTemplates.value) {
      emailTemplates.value = emailTemplates.value.filter(t => t.id !== templateToDelete.value!.id);
    }
    toast.success('Template deleted');
  } catch (error) {
    toast.error('Failed to delete template');
    console.error(error);
  } finally {
    templateToDelete.value = null;
  }
};

onMounted(() => {
  loadTemplates();
});
</script>
