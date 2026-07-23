/**
 * Props for the `UiPresenterVideoDropzone` component — the drag-and-drop area
 * used as the presenter-clip empty state and after a clip is deleted.
 */
export type UiPresenterVideoDropzoneProps = {
  /** Currently picked file, or ``null`` when none is staged yet. */
  selectedFile: File | null
  /** Whether a file is being dragged over the zone (drives the highlight). */
  isDragging: boolean
  /** Whether an upload is in flight (disables the send button). */
  isUploading: boolean
  /** Compact variant used inside the folded « replace » block. */
  compact?: boolean
}
