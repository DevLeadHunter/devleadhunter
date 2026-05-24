<template>
  <div class="wysiwyg-editor">
    <!-- Toolbar -->
    <div v-if="editor" class="editor-toolbar">
      <button
        type="button"
        :class="{ 'is-active': editor.isActive('bold') }"
        class="toolbar-btn"
        title="Gras"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <i class="fas fa-bold"></i>
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('italic') }"
        class="toolbar-btn"
        title="Italique"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <i class="fas fa-italic"></i>
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('underline') }"
        class="toolbar-btn"
        title="Souligné"
        @click="editor.chain().focus().toggleUnderline().run()"
      >
        <i class="fas fa-underline"></i>
      </button>

      <div class="toolbar-separator"></div>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('heading', { level: 1 }) }"
        class="toolbar-btn"
        title="Titre 1"
        @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
      >
        <i class="fas fa-heading"></i>1
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('heading', { level: 2 }) }"
        class="toolbar-btn"
        title="Titre 2"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        <i class="fas fa-heading"></i>2
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('paragraph') }"
        class="toolbar-btn"
        title="Paragraphe"
        @click="editor.chain().focus().setParagraph().run()"
      >
        <i class="fas fa-paragraph"></i>
      </button>

      <div class="toolbar-separator"></div>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('bulletList') }"
        class="toolbar-btn"
        title="Liste à puces"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        <i class="fas fa-list-ul"></i>
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('orderedList') }"
        class="toolbar-btn"
        title="Liste numérotée"
        @click="editor.chain().focus().toggleOrderedList().run()"
      >
        <i class="fas fa-list-ol"></i>
      </button>

      <div class="toolbar-separator"></div>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive({ textAlign: 'left' }) }"
        class="toolbar-btn"
        title="Aligner à gauche"
        @click="editor.chain().focus().setTextAlign('left').run()"
      >
        <i class="fas fa-align-left"></i>
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive({ textAlign: 'center' }) }"
        class="toolbar-btn"
        title="Centrer"
        @click="editor.chain().focus().setTextAlign('center').run()"
      >
        <i class="fas fa-align-center"></i>
      </button>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive({ textAlign: 'right' }) }"
        class="toolbar-btn"
        title="Aligner à droite"
        @click="editor.chain().focus().setTextAlign('right').run()"
      >
        <i class="fas fa-align-right"></i>
      </button>

      <div class="toolbar-separator"></div>

      <button
        type="button"
        :class="{ 'is-active': editor.isActive('link') }"
        class="toolbar-btn"
        title="Ajouter un lien"
        @click="addLink"
      >
        <i class="fas fa-link"></i>
      </button>

      <button
        type="button"
        :disabled="!editor.isActive('link')"
        class="toolbar-btn"
        title="Supprimer le lien"
        @click="editor.chain().focus().unsetLink().run()"
      >
        <i class="fas fa-unlink"></i>
      </button>

      <div class="toolbar-separator"></div>

      <button
        type="button"
        :disabled="!editor.can().undo()"
        class="toolbar-btn"
        title="Annuler"
        @click="editor.chain().focus().undo().run()"
      >
        <i class="fas fa-undo"></i>
      </button>

      <button
        type="button"
        :disabled="!editor.can().redo()"
        class="toolbar-btn"
        title="Rétablir"
        @click="editor.chain().focus().redo().run()"
      >
        <i class="fas fa-redo"></i>
      </button>
    </div>

    <!-- Editor Content -->
    <EditorContent :editor="editor" class="editor-content" />
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
        class: 'text-blue-500 underline',
      },
    }),
    TextAlign.configure({
      types: ['heading', 'paragraph'],
    }),
    Underline,
  ],
  editorProps: {
    attributes: {
      class: 'prose prose-sm max-w-none focus:outline-none',
    },
  },
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
})

// Watch for external changes to modelValue
watch(
  () => props.modelValue,
  (value) => {
    const isSame = editor.value?.getHTML() === value
    if (!isSame && editor.value) {
      editor.value.commands.setContent(value, false)
    }
  },
)

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
  @apply overflow-hidden rounded-lg border border-gray-700 bg-gray-900;
}

.editor-toolbar {
  @apply flex flex-wrap gap-1 border-b border-gray-700 bg-gray-800 p-2;
}

.toolbar-btn {
  @apply rounded px-3 py-1.5 text-sm font-medium text-gray-300 transition-colors hover:bg-gray-700 hover:text-white;
}

.toolbar-btn.is-active {
  @apply bg-blue-600 text-white;
}

.toolbar-btn:disabled {
  @apply cursor-not-allowed opacity-50 hover:bg-transparent hover:text-gray-300;
}

.toolbar-separator {
  @apply mx-1 w-px bg-gray-700;
}

.editor-content {
  @apply min-h-[300px] p-4 text-gray-200;
}

:deep(.ProseMirror) {
  @apply focus:outline-none;
}

:deep(.ProseMirror p) {
  @apply mb-2;
}

:deep(.ProseMirror h1) {
  @apply mb-3 mt-4 text-2xl font-bold;
}

:deep(.ProseMirror h2) {
  @apply mb-2 mt-3 text-xl font-bold;
}

:deep(.ProseMirror ul) {
  @apply mb-2 list-inside list-disc;
}

:deep(.ProseMirror ol) {
  @apply mb-2 list-inside list-decimal;
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
