import type { VideoBuildPhase } from '~/types/UiVideoGenerationModal'

/** The website video build's phases, in the order the desktop app reports them. */
export const SITE_VIDEO_BUILD_PHASES: VideoBuildPhase[] = [
  { key: 'preparing', label: 'Préparation (contexte + clip présentateur)' },
  { key: 'site_capture', label: 'Capture du site (défilement)' },
  { key: 'editor_capture', label: 'Séquence éditeur Storyblok' },
  { key: 'background_assemble', label: 'Assemblage du fond' },
  { key: 'montage', label: 'Montage final (webcam + habillage)' },
]

/** The receptionist video build's phases, in the order the desktop app reports them. */
export const RECEPTIONIST_VIDEO_BUILD_PHASES: VideoBuildPhase[] = [
  { key: 'preparing', label: 'Préparation (clip présentateur)' },
  { key: 'widget_capture', label: 'Capture de la réceptionniste (réponse en direct)' },
  { key: 'widget_assemble', label: 'Assemblage de la séquence' },
  { key: 'montage', label: 'Montage final (webcam + habillage)' },
]
