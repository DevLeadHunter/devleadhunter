import { nextTick } from 'vue'
import type {
  DragToReorderGhostFrame,
  DragToReorderLanding,
  DragToReorderOptions,
  DragToReorderSession,
  UseDragToReorderReturn,
} from '~/types/Composables'

/** Pointer travel before a press on a grip turns into a drag, so a plain click goes through. */
const DRAG_START_THRESHOLD_PX: number = 4

/** Vertical lists: share of an item's height around its midpoint where nothing happens, so a still hand never flips the order. */
const VERTICAL_DEAD_ZONE_RATIO: number = 0.3
const VERTICAL_DEAD_ZONE_MIN_PX: number = 6

/** Grids: inset of each cell the pointer must enter before the item takes that cell. */
const GRID_HIT_INSET_RATIO: number = 0.2

/** Distance from the scroll viewport edge where it starts scrolling by itself, and the top speed per frame. */
const AUTOSCROLL_EDGE_PX: number = 56
const AUTOSCROLL_MAX_STEP_PX: number = 14

const GLIDE_DURATION_MS: number = 200
const LIFT_DURATION_MS: number = 140
const GLIDE_EASING: string = 'cubic-bezier(0.2, 0.7, 0.2, 1)'
const DEFAULT_LIFT_SCALE: number = 1.01
const CARD_FRAME_BORDER_RADIUS: string = '0.75rem'
const ITEM_KEY_ATTRIBUTE: string = 'data-reorder-key'
const SLOT_CLASS: string = 'drag-reorder-slot'
const SLOT_LABEL_CLASS: string = 'drag-reorder-slot-label'
const BODY_DRAGGING_CLASS: string = 'is-drag-reordering'

/**
 * Nearest ancestor that scrolls vertically, or null when the document itself scrolls.
 * @param element - Element to start from.
 * @returns The scrolling ancestor, or null.
 */
function findScrollParent(element: HTMLElement | null): HTMLElement | null {
  let node: HTMLElement | null = element?.parentElement ?? null
  while (node && node !== document.body) {
    const overflowY: string = getComputedStyle(node).overflowY
    if ((overflowY === 'auto' || overflowY === 'scroll') && node.scrollHeight > node.clientHeight) return node
    node = node.parentElement
  }
  return null
}

/**
 * Milliseconds for a motion, or 0 when the user asked for reduced motion.
 * @param durationMs - Nominal duration.
 * @returns The duration to animate with.
 */
function motionDuration(durationMs: number): number {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : durationMs
}

/**
 * Reorder a list or a grid by dragging items from a grip: a lifted copy follows the pointer, the others glide, and the copy lands in its slot on release.
 * @param options - Container access, order accessors and callbacks; see `DragToReorderOptions`.
 * @returns The grip `pointerdown` handler and a cancel to call on unmount.
 */
export function useDragToReorder<T>(options: DragToReorderOptions<T>): UseDragToReorderReturn<T> {
  const liftScale: number = options.liftScale ?? DEFAULT_LIFT_SCALE
  const ghostFrame: DragToReorderGhostFrame = options.ghostFrame ?? 'none'

  let session: DragToReorderSession<T> | null = null
  let landing: DragToReorderLanding | null = null

  /**
   * Every keyed item element of the container, in DOM order.
   * @returns The item elements.
   */
  function itemElements(): HTMLElement[] {
    const container: HTMLElement | null = options.getContainer()
    if (!container) return []
    return Array.from(container.querySelectorAll(`[${ITEM_KEY_ATTRIBUTE}]`)).filter(
      (element: Element): element is HTMLElement => element instanceof HTMLElement,
    )
  }

  /**
   * The item element carrying a given key.
   * @param key - Item key.
   * @returns The element, or null when it is not rendered.
   */
  function elementForKey(key: string): HTMLElement | null {
    return (
      itemElements().find((element: HTMLElement): boolean => element.getAttribute(ITEM_KEY_ATTRIBUTE) === key) ?? null
    )
  }

  /**
   * Arm a drag from a grip; listeners live on window so an item moved in the DOM cannot lose them.
   * @param event - The native pointerdown event on the grip.
   * @param item - The item the grip belongs to.
   */
  function onGripPointerDown(event: PointerEvent, item: T): void {
    if (event.button !== 0 || session) return
    landing?.finish()
    const grip: HTMLElement | null = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
    const element: Element | null = grip?.closest(`[${ITEM_KEY_ATTRIBUTE}]`) ?? null
    if (!(element instanceof HTMLElement)) return
    event.preventDefault()
    const bounds: DOMRect = element.getBoundingClientRect()
    session = {
      item,
      key: options.keyOf(item),
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      lastClientX: event.clientX,
      lastClientY: event.clientY,
      grabOffsetX: event.clientX - bounds.left,
      grabOffsetY: event.clientY - bounds.top,
      itemLeft: bounds.left,
      itemWidth: bounds.width,
      ghost: null,
      ghostInnerLeft: 0,
      ghostInnerTop: 0,
      isActive: false,
      autoscrollFrame: 0,
      scrollParent: null,
    }
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
    window.addEventListener('pointercancel', cancelDrag)
    window.addEventListener('keydown', onKeydown)
    window.addEventListener('blur', cancelDrag)
    window.addEventListener('scroll', onScrollWhileDragging, { capture: true, passive: true })
  }

  /**
   * Follow the pointer: start the drag past the threshold, then move the ghost and the slot.
   * @param event - The native pointermove event.
   */
  function onPointerMove(event: PointerEvent): void {
    const current: DragToReorderSession<T> | null = session
    if (!current || event.pointerId !== current.pointerId) return
    current.lastClientX = event.clientX
    current.lastClientY = event.clientY
    if (!current.isActive) {
      const travel: number =
        options.axis === 'vertical'
          ? Math.abs(event.clientY - current.startClientY)
          : Math.hypot(event.clientX - current.startClientX, event.clientY - current.startClientY)
      if (travel < DRAG_START_THRESHOLD_PX) return
      beginDrag(current)
    }
    positionGhost(current)
    moveTowardsPointer(current)
  }

  /**
   * Release: land the previewed order; a press without travel is a plain click and does nothing.
   * @param event - The native pointerup event.
   */
  function onPointerUp(event: PointerEvent): void {
    const current: DragToReorderSession<T> | null = session
    if (!current || event.pointerId !== current.pointerId) return
    if (current.isActive) commitDrag()
    else detachSession()
  }

  /** Something scrolled under a held item (wheel or autoscroll): the slot follows the pointer's new place. */
  function onScrollWhileDragging(): void {
    if (session?.isActive) moveTowardsPointer(session)
  }

  /**
   * Escape cancels the drag in progress.
   * @param event - The native keydown event.
   */
  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') cancelDrag()
  }

  /**
   * Turn the armed press into a drag: snapshot the order, lift the ghost, freeze the items and lock the page cursor.
   * @param current - The armed session.
   */
  function beginDrag(current: DragToReorderSession<T>): void {
    const element: HTMLElement | null = elementForKey(current.key)
    const container: HTMLElement | null = options.getContainer()
    current.isActive = true
    options.setDraggedKey(current.key)
    options.setDraftOrder([...options.getOrder()])
    if (element) current.ghost = createGhost(element, current)
    document.body.classList.add(BODY_DRAGGING_CLASS)
    if (container) container.style.pointerEvents = 'none'
    current.scrollParent = findScrollParent(container)
    startAutoscrollLoop(current)
  }

  /**
   * Clone the item into a fixed card aligned pixel for pixel on the original, without its positional labels, then lift it.
   * @param element - The item element being dragged.
   * @param current - The active session.
   * @returns The ghost element, appended to the document body.
   */
  function createGhost(element: HTMLElement, current: DragToReorderSession<T>): HTMLElement {
    const clone: HTMLElement = element.cloneNode(true) as HTMLElement
    clone.classList.remove(SLOT_CLASS)
    clone.removeAttribute(ITEM_KEY_ATTRIBUTE)
    clone.querySelectorAll(`.${SLOT_LABEL_CLASS}`).forEach((label: Element): void => label.remove())
    let content: HTMLElement = clone
    if (element instanceof HTMLTableRowElement) {
      const originalCells: Element[] = Array.from(element.children)
      Array.from(clone.children).forEach((cell: Element, index: number): void => {
        const original: Element | undefined = originalCells[index]
        if (cell instanceof HTMLElement && original) cell.style.width = `${original.getBoundingClientRect().width}px`
      })
      const table: HTMLTableElement = document.createElement('table')
      const body: HTMLTableSectionElement = document.createElement('tbody')
      body.appendChild(clone)
      table.appendChild(body)
      content = table
    }
    const card: HTMLDivElement = document.createElement('div')
    card.className = 'drag-reorder-ghost__card'
    if (ghostFrame === 'card') card.classList.add('drag-reorder-ghost__card--card')
    card.style.borderRadius = ghostFrame === 'card' ? CARD_FRAME_BORDER_RADIUS : getComputedStyle(element).borderRadius
    card.style.setProperty('--drag-reorder-lift', String(liftScale))
    card.style.transform = 'none'
    card.appendChild(content)
    const ghost: HTMLDivElement = document.createElement('div')
    ghost.className = 'drag-reorder-ghost'
    ghost.style.width = `${current.itemWidth + (ghostFrame === 'card' ? 2 : 0)}px`
    ghost.appendChild(card)
    document.body.appendChild(ghost)
    const ghostBounds: DOMRect = ghost.getBoundingClientRect()
    const cloneBounds: DOMRect = clone.getBoundingClientRect()
    current.ghostInnerLeft = cloneBounds.left - ghostBounds.left
    current.ghostInnerTop = cloneBounds.top - ghostBounds.top
    card.style.transform = ''
    positionGhost(current)
    const liftKeyframes: Keyframe[] = [
      { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(0, 0, 0, 0)' },
      { transform: `scale(${liftScale})`, boxShadow: getComputedStyle(card).boxShadow },
    ]
    card.animate(liftKeyframes, { duration: motionDuration(LIFT_DURATION_MS), easing: GLIDE_EASING })
    return ghost
  }

  /**
   * Wrapper transform placing the clone's top-left corner at the given viewport coordinates.
   * @param current - The active session.
   * @param left - Viewport x of the clone's left edge.
   * @param top - Viewport y of the clone's top edge.
   * @returns The CSS transform value.
   */
  function ghostTransform(current: DragToReorderSession<T>, left: number, top: number): string {
    return `translate3d(${left - current.ghostInnerLeft}px, ${top - current.ghostInnerTop}px, 0)`
  }

  /**
   * Keep the ghost under the pointer; vertical lists stay column-aligned, grids follow both axes.
   * @param current - The active session.
   */
  function positionGhost(current: DragToReorderSession<T>): void {
    if (!current.ghost) return
    const left: number = options.axis === 'vertical' ? current.itemLeft : current.lastClientX - current.grabOffsetX
    current.ghost.style.transform = ghostTransform(current, left, current.lastClientY - current.grabOffsetY)
  }

  /**
   * Vertical lists: the dragged item takes the place of the item whose midpoint (plus dead zone) the pointer crossed, measured on layout positions so the glide never makes the order oscillate.
   * @param elements - Item elements in DOM order.
   * @param from - Current index of the dragged item.
   * @param pointerY - Pointer y relative to the container.
   * @returns The index the dragged item should take.
   */
  function targetIndexVertical(elements: HTMLElement[], from: number, pointerY: number): number {
    for (let index: number = 0; index < from; index++) {
      const element: HTMLElement | undefined = elements[index]
      if (!element) continue
      const deadZone: number = Math.max(VERTICAL_DEAD_ZONE_MIN_PX, element.offsetHeight * VERTICAL_DEAD_ZONE_RATIO)
      if (pointerY < element.offsetTop + element.offsetHeight / 2 - deadZone) return index
    }
    for (let index: number = elements.length - 1; index > from; index--) {
      const element: HTMLElement | undefined = elements[index]
      if (!element) continue
      const deadZone: number = Math.max(VERTICAL_DEAD_ZONE_MIN_PX, element.offsetHeight * VERTICAL_DEAD_ZONE_RATIO)
      if (pointerY > element.offsetTop + element.offsetHeight / 2 + deadZone) return index
    }
    return from
  }

  /**
   * Grids: the dragged item takes the cell the pointer is clearly inside; below the grid means last, above means first.
   * @param elements - Item elements in DOM order.
   * @param from - Current index of the dragged item.
   * @param pointerX - Pointer x relative to the container.
   * @param pointerY - Pointer y relative to the container.
   * @returns The index the dragged item should take.
   */
  function targetIndexGrid(elements: HTMLElement[], from: number, pointerX: number, pointerY: number): number {
    for (let index: number = 0; index < elements.length; index++) {
      const element: HTMLElement | undefined = elements[index]
      if (!element) continue
      const insetX: number = Math.max(VERTICAL_DEAD_ZONE_MIN_PX, element.offsetWidth * GRID_HIT_INSET_RATIO)
      const insetY: number = Math.max(VERTICAL_DEAD_ZONE_MIN_PX, element.offsetHeight * GRID_HIT_INSET_RATIO)
      const isInsideX: boolean =
        pointerX >= element.offsetLeft + insetX && pointerX <= element.offsetLeft + element.offsetWidth - insetX
      const isInsideY: boolean =
        pointerY >= element.offsetTop + insetY && pointerY <= element.offsetTop + element.offsetHeight - insetY
      if (isInsideX && isInsideY) return index
    }
    const first: HTMLElement | undefined = elements[0]
    const last: HTMLElement | undefined = elements[elements.length - 1]
    if (last && pointerY > last.offsetTop + last.offsetHeight) return elements.length - 1
    if (first && pointerY < first.offsetTop) return 0
    return from
  }

  /**
   * Slide the dragged item to the slot under the pointer, in the draft order.
   * @param current - The active session.
   */
  function moveTowardsPointer(current: DragToReorderSession<T>): void {
    const container: HTMLElement | null = options.getContainer()
    if (!container) return
    const order: T[] = options.getOrder()
    const from: number = order.findIndex((entry: T): boolean => options.keyOf(entry) === current.key)
    const elements: HTMLElement[] = itemElements()
    if (from === -1 || elements.length !== order.length) return
    const containerBounds: DOMRect = container.getBoundingClientRect()
    const pointerX: number = current.lastClientX - containerBounds.left - container.clientLeft
    const pointerY: number = current.lastClientY - containerBounds.top - container.clientTop
    const target: number =
      options.axis === 'vertical'
        ? targetIndexVertical(elements, from, pointerY)
        : targetIndexGrid(elements, from, pointerX, pointerY)
    if (target === from) return
    const next: T[] = [...order]
    const moved: T | undefined = next.splice(from, 1)[0]
    if (moved === undefined) return
    next.splice(target, 0, moved)
    options.setDraftOrder(next)
  }

  /**
   * Scroll speed for a pointer this close to the top or bottom edge of the scroll viewport, 0 away from the edges.
   * @param current - The active session.
   * @returns Signed pixels to scroll this frame.
   */
  function autoscrollStep(current: DragToReorderSession<T>): number {
    const viewportTop: number = current.scrollParent ? current.scrollParent.getBoundingClientRect().top : 0
    const viewportBottom: number = current.scrollParent
      ? current.scrollParent.getBoundingClientRect().bottom
      : window.innerHeight
    const pointerY: number = current.lastClientY
    if (pointerY < viewportTop + AUTOSCROLL_EDGE_PX) {
      return -Math.ceil(((viewportTop + AUTOSCROLL_EDGE_PX - pointerY) / AUTOSCROLL_EDGE_PX) * AUTOSCROLL_MAX_STEP_PX)
    }
    if (pointerY > viewportBottom - AUTOSCROLL_EDGE_PX) {
      return Math.ceil(
        ((pointerY - (viewportBottom - AUTOSCROLL_EDGE_PX)) / AUTOSCROLL_EDGE_PX) * AUTOSCROLL_MAX_STEP_PX,
      )
    }
    return 0
  }

  /**
   * One frame loop for the whole drag: near an edge the scroll viewport scrolls and the slot is re-evaluated.
   * @param current - The active session.
   */
  function startAutoscrollLoop(current: DragToReorderSession<T>): void {
    const tick: () => void = (): void => {
      if (session !== current) return
      const step: number = autoscrollStep(current)
      if (step) {
        const target: Element | null = current.scrollParent ?? document.scrollingElement
        if (target) {
          const before: number = target.scrollTop
          target.scrollTop += step
          if (target.scrollTop !== before) moveTowardsPointer(current)
        }
      }
      current.autoscrollFrame = requestAnimationFrame(tick)
    }
    current.autoscrollFrame = requestAnimationFrame(tick)
  }

  /** Drop: hand the previewed order to the owner, then fly the ghost into its slot and reveal the item. */
  async function commitDrag(): Promise<void> {
    const current: DragToReorderSession<T> | null = session
    if (!current) return
    const order: T[] = options.getOrder()
    detachSession()
    options.onCommit(order)
    options.setDraftOrder(null)
    await nextTick()
    landGhost(current)
  }

  /** Escape, pointer cancel, window blur or unmount: items glide back and the ghost returns to where it was picked up. */
  async function cancelDrag(): Promise<void> {
    landing?.finish()
    const current: DragToReorderSession<T> | null = session
    if (!current) return
    const wasActive: boolean = current.isActive
    detachSession()
    if (!wasActive) return
    options.onCancel?.()
    options.setDraftOrder(null)
    await nextTick()
    landGhost(current)
  }

  /** Stop listening and unfreeze the page; the ghost and the slot survive until the ghost has landed. */
  function detachSession(): void {
    const current: DragToReorderSession<T> | null = session
    session = null
    if (!current) return
    if (current.autoscrollFrame) cancelAnimationFrame(current.autoscrollFrame)
    const container: HTMLElement | null = options.getContainer()
    if (container) container.style.pointerEvents = ''
    document.body.classList.remove(BODY_DRAGGING_CLASS)
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    window.removeEventListener('pointercancel', cancelDrag)
    window.removeEventListener('keydown', onKeydown)
    window.removeEventListener('blur', cancelDrag)
    window.removeEventListener('scroll', onScrollWhileDragging, { capture: true })
  }

  /**
   * Fly the ghost onto the slot's layout position (where it sits once any glide ends), flatten it, then reveal the item.
   * @param current - The session that just ended.
   */
  function landGhost(current: DragToReorderSession<T>): void {
    const ghost: HTMLElement | null = current.ghost
    const container: HTMLElement | null = options.getContainer()
    const slotElement: HTMLElement | null = container ? elementForKey(current.key) : null
    let isDone: boolean = false
    const finish: () => void = (): void => {
      if (isDone) return
      isDone = true
      ghost?.remove()
      options.setDraggedKey(null)
      landing = null
    }
    if (!ghost || !container || !slotElement) {
      finish()
      return
    }
    const containerBounds: DOMRect = container.getBoundingClientRect()
    const left: number =
      options.axis === 'vertical'
        ? current.itemLeft
        : containerBounds.left + container.clientLeft + slotElement.offsetLeft
    const top: number = containerBounds.top + container.clientTop + slotElement.offsetTop
    const card: HTMLElement | null = ghost.firstElementChild instanceof HTMLElement ? ghost.firstElementChild : null
    const duration: number = motionDuration(GLIDE_DURATION_MS)
    const slideKeyframes: Keyframe[] = [
      { transform: ghost.style.transform },
      { transform: ghostTransform(current, left, top) },
    ]
    const slide: Animation = ghost.animate(slideKeyframes, { duration, easing: GLIDE_EASING, fill: 'forwards' })
    if (card) {
      const cardStyle: CSSStyleDeclaration = getComputedStyle(card)
      const flattenKeyframes: Keyframe[] = [
        { transform: `scale(${liftScale})`, boxShadow: cardStyle.boxShadow, borderColor: cardStyle.borderColor },
        { transform: 'scale(1)', boxShadow: '0 0 0 0 rgba(0, 0, 0, 0)', borderColor: 'transparent' },
      ]
      card.animate(flattenKeyframes, { duration, easing: GLIDE_EASING, fill: 'forwards' })
      options.morphGhostToSlot?.(card, slotElement, duration, GLIDE_EASING)
    }
    slide.onfinish = finish
    slide.oncancel = finish
    landing = {
      finish: (): void => {
        slide.cancel()
        finish()
      },
    }
  }

  return { onGripPointerDown, cancelDrag }
}
