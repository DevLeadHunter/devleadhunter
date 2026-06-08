<template>
  <DemoPlumberSimplePage :content="content" business-name="Dupont Plomberie" />
</template>

<script lang="ts" setup>
import DemoPlumberSimplePage from '~/components/templates/plumber-simple/index.vue'
// PAGE TEMPORAIRE DE PREVIEW (simple) — à supprimer après revue. N'écrase aucune autre template.
const content = {
  theme: { primary: '#0284c7', secondary: '#0f172a', accent: '#f59e0b' },
  body: [
    {
      component: 'hero',
      title: 'Dupont Plomberie',
      subtitle: 'Artisan plombier à Bordeaux — dépannage rapide, travail soigné, devis gratuit.',
      phone: '05 56 12 34 56',
      cta_label: 'Appeler',
      badge: 'Urgences 7j/7',
    },
    {
      component: 'trust',
      items: [
        { value: '15 ans', label: "D'expérience" },
        { value: '< 2h', label: 'En urgence' },
        { value: '4,9/5', label: 'Avis Google' },
        { value: 'Gratuit', label: 'Devis' },
      ],
    },
    {
      component: 'services',
      heading: 'Nos services',
      subheading: 'Des solutions complètes pour particuliers et professionnels.',
      items: [
        { label: "Dépannage d'urgence", description: 'Fuite, canalisation bouchée ou chauffe-eau en panne — 7j/7.', icon: 'emergency' },
        { label: 'Recherche de fuite', description: 'Diagnostic précis sans casse inutile.', icon: 'leak' },
        { label: 'Chauffe-eau', description: 'Entretien, remplacement et mise aux normes.', icon: 'heater' },
        { label: 'Installation', description: 'Robinetterie, WC et sanitaires posés proprement.', icon: 'install' },
      ],
    },
    {
      component: 'why_us',
      heading: 'Pourquoi nous choisir ?',
      items: [
        { label: 'Devis gratuit et transparent avant chaque intervention' },
        { label: 'Un artisan qualifié de A à Z — jamais de sous-traitance' },
        { label: 'Travail soigné, garanti et facturé au juste prix' },
      ],
    },
    {
      component: 'contact',
      heading: 'Contactez-nous',
      subheading: 'Réponse sous 2h · Devis gratuit · Intervention rapide à Bordeaux',
      email: 'contact@dupont-plomberie.fr',
      phone: '05 56 12 34 56',
      city: 'Bordeaux',
    },
  ],
}
</script>
