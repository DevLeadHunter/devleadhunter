<template>
  <!--
    Eight-spoked asterisk mark used across the landing (dividers, ticker,
    oversized watermarks). Inline SVG instead of the Unicode « ✳ » glyph:
    U+2733 falls back to Apple Color Emoji on iOS (rendered green, ignoring
    `color`). Each spoke is a tapered filled shape (wider rounded tip,
    converging near the center) to match the original glyph's silhouette.
    Inherits size via `1em` and color via `currentColor`, so `text-[…]`
    utility classes keep controlling it.
  -->
  <svg
    class="inline-block h-[1em] w-[1em] align-[-0.125em]"
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
    focusable="false"
  >
    <path
      v-for="spokeIndex in 8"
      :key="spokeIndex"
      d="M11.78 11.4 L11.2 3 A0.8 0.8 0 0 1 12.8 3 L12.22 11.4 Z"
      :transform="`rotate(${(spokeIndex - 1) * 45} 12 12)`"
    />
  </svg>
</template>
