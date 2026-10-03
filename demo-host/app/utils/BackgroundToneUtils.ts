import type { RgbaColor } from '~/types/BackgroundTone'

const MIN_OPAQUE_ALPHA: number = 0.9
const MAX_CHANNEL: number = 255
const DARK_INK: RgbaColor = { red: 17, green: 17, blue: 17, alpha: 1 }
const LIGHT_INK: RgbaColor = { red: 255, green: 255, blue: 255, alpha: 1 }
const MIN_CONTRAST_FOR_MUTED_INK: number = 7
const RED_LUMINANCE_WEIGHT: number = 0.2126
const GREEN_LUMINANCE_WEIGHT: number = 0.7152
const BLUE_LUMINANCE_WEIGHT: number = 0.0722
const SRGB_LINEAR_SEGMENT_LIMIT: number = 0.04045
const SRGB_LINEAR_SEGMENT_DIVISOR: number = 12.92
const SRGB_GAMMA_OFFSET: number = 0.055
const SRGB_GAMMA: number = 2.4
const CONTRAST_LUMINANCE_OFFSET: number = 0.05

/**
 * Background colour and readable ink of the band a template paints at its bottom edge (client only).
 */
export class BackgroundToneUtils {
  /**
   * The opaque background at the bottom edge of an element, read on its chain of last visible children.
   * @param root - The element the strip follows.
   * @returns The colour, or null when nothing along the chain paints an opaque background.
   */
  static bottomBackground(root: HTMLElement): RgbaColor | null {
    const chain: HTMLElement[] = [root]
    let next: HTMLElement | null = BackgroundToneUtils.lastVisibleChild(root)
    while (next) {
      chain.push(next)
      next = BackgroundToneUtils.lastVisibleChild(next)
    }
    for (const element of chain.reverse()) {
      const color: RgbaColor | null = BackgroundToneUtils.toRgba(getComputedStyle(element).backgroundColor)
      if (color && color.alpha >= MIN_OPAQUE_ALPHA) return color
    }
    return null
  }

  /**
   * Whether white ink contrasts more than near-black ink with a background (WCAG contrast ratio).
   * @param background - The background colour.
   * @returns True when the text should be light.
   */
  static prefersLightInk(background: RgbaColor): boolean {
    const lightInkContrast: number = BackgroundToneUtils.contrastRatio(background, LIGHT_INK)
    const darkInkContrast: number = BackgroundToneUtils.contrastRatio(background, DARK_INK)
    return lightInkContrast > darkInkContrast
  }

  /**
   * Whether a mid-tone background keeps the ink at full strength, because even the better ink stays under 7:1.
   * @param background - The background colour.
   * @returns True when the ink must not be muted.
   */
  static needsFullInk(background: RgbaColor): boolean {
    const lightInkContrast: number = BackgroundToneUtils.contrastRatio(background, LIGHT_INK)
    const darkInkContrast: number = BackgroundToneUtils.contrastRatio(background, DARK_INK)
    return Math.max(lightInkContrast, darkInkContrast) < MIN_CONTRAST_FOR_MUTED_INK
  }

  /**
   * A computed CSS colour of any syntax (`rgb()`, `color(srgb …)`, `oklch()`) turned into channels by painting it.
   * @param cssColor - A computed CSS colour.
   * @returns Its channels (0-255, alpha 0-1), or null when it cannot be painted.
   */
  static toRgba(cssColor: string): RgbaColor | null {
    const context: CanvasRenderingContext2D | null = document.createElement('canvas').getContext('2d')
    if (!context || !cssColor) return null
    context.clearRect(0, 0, 1, 1)
    context.fillStyle = cssColor
    context.fillRect(0, 0, 1, 1)
    const pixel: Uint8ClampedArray = context.getImageData(0, 0, 1, 1).data
    return {
      red: pixel[0] ?? 0,
      green: pixel[1] ?? 0,
      blue: pixel[2] ?? 0,
      alpha: (pixel[3] ?? 0) / MAX_CHANNEL,
    }
  }

  /**
   * The WCAG contrast ratio between two opaque colours, from 1 to 21.
   * @param first - A colour.
   * @param second - Another colour.
   * @returns The ratio of the lighter relative luminance to the darker one.
   */
  private static contrastRatio(first: RgbaColor, second: RgbaColor): number {
    const firstLuminance: number = BackgroundToneUtils.relativeLuminance(first)
    const secondLuminance: number = BackgroundToneUtils.relativeLuminance(second)
    const lighter: number = Math.max(firstLuminance, secondLuminance)
    const darker: number = Math.min(firstLuminance, secondLuminance)
    return (lighter + CONTRAST_LUMINANCE_OFFSET) / (darker + CONTRAST_LUMINANCE_OFFSET)
  }

  /**
   * The WCAG relative luminance of a colour, from 0 (black) to 1 (white).
   * @param color - An opaque colour.
   * @returns Its luminance.
   */
  private static relativeLuminance(color: RgbaColor): number {
    return (
      RED_LUMINANCE_WEIGHT * BackgroundToneUtils.linearChannel(color.red) +
      GREEN_LUMINANCE_WEIGHT * BackgroundToneUtils.linearChannel(color.green) +
      BLUE_LUMINANCE_WEIGHT * BackgroundToneUtils.linearChannel(color.blue)
    )
  }

  /**
   * An sRGB channel converted to linear light, as the WCAG luminance formula requires.
   * @param channel - The channel, from 0 to 255.
   * @returns The linear value, from 0 to 1.
   */
  private static linearChannel(channel: number): number {
    const ratio: number = channel / MAX_CHANNEL
    if (ratio <= SRGB_LINEAR_SEGMENT_LIMIT) return ratio / SRGB_LINEAR_SEGMENT_DIVISOR
    return ((ratio + SRGB_GAMMA_OFFSET) / (1 + SRGB_GAMMA_OFFSET)) ** SRGB_GAMMA
  }

  /**
   * The last child that takes room on the page: displayed, not fixed or absolute, with a height.
   * @param element - The parent.
   * @returns The child, or null when none qualifies.
   */
  private static lastVisibleChild(element: HTMLElement): HTMLElement | null {
    const children: Element[] = Array.from(element.children).reverse()
    for (const child of children) {
      if (!(child instanceof HTMLElement) || child.offsetHeight === 0) continue
      const style: CSSStyleDeclaration = getComputedStyle(child)
      const isTakenOutOfPage: boolean = style.position === 'fixed' || style.position === 'absolute'
      if (style.display === 'none' || style.visibility === 'hidden' || isTakenOutOfPage) continue
      return child
    }
    return null
  }
}
