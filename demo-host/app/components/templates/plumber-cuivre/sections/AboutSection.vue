<template>
  <section v-if="about.heading || about.text" id="artisan" class="cuivre-section" aria-label="Votre plombier">
    <div class="cuivre-container cuivre-about__inner">
      <div class="cuivre-about__media" data-cuivre-reveal>
        <figure v-if="about.image" class="cuivre-about__frame">
          <img :src="about.image" :alt="about.imageCaption || 'Votre plombier au travail'" class="cuivre-about__photo" loading="lazy" />
          <figcaption v-if="about.imageCaption" class="cuivre-about__caption">
            <span class="cuivre-about__caption-dot" aria-hidden="true"></span>
            {{ about.imageCaption }}
          </figcaption>
        </figure>

        <div v-else class="cuivre-about__placeholder" aria-hidden="true">
          <CuivreGlyph name="drop" class="cuivre-about__placeholder-icon" />
          <p class="cuivre-about__placeholder-label">Artisan plombier</p>
          <p v-if="about.imageCaption" class="cuivre-about__placeholder-caption">{{ about.imageCaption }}</p>
        </div>
      </div>

      <div class="cuivre-about__copy" data-cuivre-reveal :style="{ '--cuivre-reveal-delay': '110ms' }">
        <p class="cuivre-eyebrow"><span class="cuivre-eyebrow__num">04</span>{{ about.kicker }}</p>
        <h2 class="cuivre-heading">{{ about.heading }}</h2>
        <p v-if="about.text" class="cuivre-about__text">{{ about.text }}</p>

        <ul v-if="about.points.length" class="cuivre-about__points">
          <li v-for="point in about.points" :key="point" class="cuivre-about__point">
            <CuivreGlyph name="check" class="cuivre-about__point-icon" />
            {{ point }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
/**
 * « Votre plombier » : la section qui humanise le site — photo de l'artisan
 * au travail (2e photo d'enrichissement) ou carte décorative goutte, discours
 * « un artisan, pas une plateforme » et engagements en badges.
 */
import CuivreGlyph from './CuivreGlyph.vue'
import type { CuivreAboutContent } from '../types'

defineProps<{
  about: CuivreAboutContent
}>()
</script>

<style scoped>
.cuivre-about__inner {
  display: grid;
  gap: 2.8rem;
  align-items: center;
}

@media (min-width: 1024px) {
  .cuivre-about__inner {
    grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
    gap: 4.5rem;
  }
}

.cuivre-about__frame {
  margin: 0;
  padding: 0.7rem;
  background: var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  border-radius: 18px;
  box-shadow: 0 24px 50px -32px color-mix(in srgb, var(--cuivre-blue) 50%, transparent);
}

.cuivre-about__photo {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 12px;
  filter: saturate(1.02) contrast(1.02);
}

.cuivre-about__caption {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0;
  padding: 0.7rem 0.45rem 0.15rem;
  font-family: var(--cuivre-font-sans);
  font-size: 0.84rem;
  color: var(--cuivre-muted);
}

.cuivre-about__caption-dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 9999px 9999px 9999px 2px;
  transform: rotate(45deg);
  background: var(--cuivre-aqua);
}

.cuivre-about__placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  aspect-ratio: 4 / 3;
  border-radius: 18px;
  background:
    radial-gradient(ellipse 75% 65% at 50% 38%, color-mix(in srgb, var(--cuivre-aqua) 10%, transparent), transparent 72%),
    var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
}

.cuivre-about__placeholder-icon {
  width: 44px;
  height: 44px;
  color: var(--cuivre-blue);
}

.cuivre-about__placeholder-label {
  font-family: var(--cuivre-font-display);
  font-weight: 700;
  font-size: 0.78rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--cuivre-blue);
}

.cuivre-about__placeholder-caption {
  font-family: var(--cuivre-font-sans);
  font-size: 0.84rem;
  color: var(--cuivre-muted);
}

.cuivre-about__text {
  margin-top: 1.2rem;
  max-width: 34rem;
  font-size: 0.97rem;
  line-height: 1.75;
  color: var(--cuivre-muted);
}

.cuivre-about__points {
  margin-top: 1.5rem;
  display: grid;
  gap: 0.6rem;
  list-style: none;
  padding: 0;
}

.cuivre-about__point {
  display: inline-flex;
  align-items: baseline;
  gap: 0.6rem;
  width: fit-content;
  padding: 0.55rem 1rem;
  border-radius: 9999px;
  background: var(--cuivre-card);
  border: 1px solid var(--cuivre-rule);
  font-family: var(--cuivre-font-sans);
  font-weight: 500;
  font-size: 0.88rem;
  color: var(--cuivre-ink);
}

.cuivre-about__point-icon {
  width: 13px;
  height: 13px;
  flex: none;
  transform: translateY(1px);
  color: var(--cuivre-aqua);
}
</style>
