<template>
  <div class="wysiwyg-editor">
    <!-- Toolbar -->
    <div v-if="editor" class="editor-toolbar">
      <button
        type="button"
        @click="editor.chain().focus().toggleBold().run()"
        :class="{ 'is-active': editor.isActive('bold') }"
        class="toolbar-btn"
        title="Gras"
      >
        <i class="fas fa-bold"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().toggleItalic().run()"
        :class="{ 'is-active': editor.isActive('italic') }"
        class="toolbar-btn"
        title="Italique"
      >
        <i class="fas fa-italic"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().toggleUnderline().run()"
        :class="{ 'is-active': editor.isActive('underline') }"
        class="toolbar-btn"
        title="Souligné"
      >
        <i class="fas fa-underline"></i>
      </button>
      
      <div class="toolbar-separator"></div>
      
      <button
        type="button"
        @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
        :class="{ 'is-active': editor.isActive('heading', { level: 1 }) }"
        class="toolbar-btn"
        title="Titre 1"
      >
        <i class="fas fa-heading"></i>1
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
        :class="{ 'is-active': editor.isActive('heading', { level: 2 }) }"
        class="toolbar-btn"
        title="Titre 2"
      >
        <i class="fas fa-heading"></i>2
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().setParagraph().run()"
        :class="{ 'is-active': editor.isActive('paragraph') }"
        class="toolbar-btn"
        title="Paragraphe"
      >
        <i class="fas fa-paragraph"></i>
      </button>
      
      <div class="toolbar-separator"></div>
      
      <button
        type="button"
        @click="editor.chain().focus().toggleBulletList().run()"
        :class="{ 'is-active': editor.isActive('bulletList') }"
        class="toolbar-btn"
        title="Liste à puces"
      >
        <i class="fas fa-list-ul"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().toggleOrderedList().run()"
        :class="{ 'is-active': editor.isActive('orderedList') }"
        class="toolbar-btn"
        title="Liste numérotée"
      >
        <i class="fas fa-list-ol"></i>
      </button>
      
      <div class="toolbar-separator"></div>
      
      <button
        type="button"
        @click="editor.chain().focus().setTextAlign('left').run()"
        :class="{ 'is-active': editor.isActive({ textAlign: 'left' }) }"
        class="toolbar-btn"
        title="Aligner à gauche"
      >
        <i class="fas fa-align-left"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().setTextAlign('center').run()"
        :class="{ 'is-active': editor.isActive({ textAlign: 'center' }) }"
        class="toolbar-btn"
        title="Centrer"
      >
        <i class="fas fa-align-center"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().setTextAlign('right').run()"
        :class="{ 'is-active': editor.isActive({ textAlign: 'right' }) }"
        class="toolbar-btn"
        title="Aligner à droite"
      >
        <i class="fas fa-align-right"></i>
      </button>
      
      <div class="toolbar-separator"></div>
      
      <button
        type="button"
        @click="addLink"
        :class="{ 'is-active': editor.isActive('link') }"
        class="toolbar-btn"
        title="Ajouter un lien"
      >
        <i class="fas fa-link"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().unsetLink().run()"
        :disabled="!editor.isActive('link')"
        class="toolbar-btn"
        title="Supprimer le lien"
      >
        <i class="fas fa-unlink"></i>
      </button>
      
      <div class="toolbar-separator"></div>
      
      <button
        type="button"
        @click="editor.chain().focus().undo().run()"
        :disabled="!editor.can().undo()"
        class="toolbar-btn"
        title="Annuler"
      >
        <i class="fas fa-undo"></i>
      </button>
      
      <button
        type="button"
        @click="editor.chain().focus().redo().run()"
        :disabled="!editor.can().redo()"
        class="toolbar-btn"
        title="Rétablir"
      >
        <i class="fas fa-redo"></i>
      </button>
    </div>

    <!-- Editor Content -->
    <editor-content :editor="editor" class="editor-content" />
  </div>
</template>

<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import { watch } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit,
    Link.configure({
      openOnClick: false,
      HTMLAttributes: {
        class: 'text-blue-500 underline'
      }
    }),
    TextAlign.configure({
      types: ['heading', 'paragraph']
    }),
    Underline
  ],
  editorProps: {
    attributes: {
      class: 'prose prose-sm max-w-none focus:outline-none'
    }
  },
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  }
})

// Watch for external changes to modelValue
watch(() => props.modelValue, (value) => {
  const isSame = editor.value?.getHTML() === value
  if (!isSame && editor.value) {
    editor.value.commands.setContent(value, false)
  }
})

const addLink = () => {
  const url = window.prompt('URL:')
  if (url && editor.value) {
    editor.value.chain().focus().setLink({ href: url }).run()
  }
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<style scoped>
.wysiwyg-editor {
  @apply border border-gray-700 rounded-lg overflow-hidden bg-gray-900;
}

.editor-toolbar {
  @apply flex flex-wrap gap-1 p-2 border-b border-gray-700 bg-gray-800;
}

.toolbar-btn {
  @apply px-3 py-1.5 rounded text-gray-300 hover:bg-gray-700 hover:text-white transition-colors text-sm font-medium;
}

.toolbar-btn.is-active {
  @apply bg-blue-600 text-white;
}

.toolbar-btn:disabled {
  @apply opacity-50 cursor-not-allowed hover:bg-transparent hover:text-gray-300;
}

.toolbar-separator {
  @apply w-px bg-gray-700 mx-1;
}

.editor-content {
  @apply p-4 min-h-[300px] text-gray-200;
}

:deep(.ProseMirror) {
  @apply focus:outline-none;
}

:deep(.ProseMirror p) {
  @apply mb-2;
}

:deep(.ProseMirror h1) {
  @apply text-2xl font-bold mb-3 mt-4;
}

:deep(.ProseMirror h2) {
  @apply text-xl font-bold mb-2 mt-3;
}

:deep(.ProseMirror ul) {
  @apply list-disc list-inside mb-2;
}

:deep(.ProseMirror ol) {
  @apply list-decimal list-inside mb-2;
}

:deep(.ProseMirror a) {
  @apply text-blue-400 underline;
}

:deep(.ProseMirror strong) {
  @apply font-bold;
}

:deep(.ProseMirror em) {
  @apply italic;
}

:deep(.ProseMirror u) {
  @apply underline;
}
</style>

