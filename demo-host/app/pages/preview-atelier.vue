<template>
  <DemoPlumberAtelierPage :content="content" business-name="Dupont Plomberie" />
</template>

<script lang="ts" setup>
import DemoPlumberAtelierPage from '~/components/templates/plumber-atelier/index.vue'
// PAGE TEMPORAIRE DE PREVIEW (atelier) — à supprimer après revue. N'écrase aucune autre template.
const content = {
  theme: { primary: '#B8732E', secondary: '#1C1B19', accent: '#2E5B6B' },
  body: [
    {
      component: 'hero',
      title: 'Dupont Plomberie',
      subtitle: 'Artisan plombier à Bordeaux — dépannage rapide, travail soigné, devis gratuit.',
      phone: '05 56 12 34 56',
      cta_label: 'Appeler',
      badge: 'Urgences 7j/7',
      city: 'Bordeaux',
    },
    {
      component: 'trust',
      heading: 'La confiance de nos clients',
      items: [
        { value: '15 ans', label: "D'expérience" },
        { value: '< 2h', label: 'En urgence' },
        { value: '4,9/5', label: 'Avis Google' },
        { value: 'Gratuit', label: 'Devis' },
      ],
    },
    {
      component: 'services',
      heading: 'Ce que nous réparons',
      subheading: 'Des solutions complètes pour particuliers et professionnels à Bordeaux.',
      items: [
        { label: "Dépannage d'urgence", description: 'Fuite, canalisation bouchée ou chauffe-eau en panne — intervention rapide, 7j/7.', icon: 'emergency' },
        { label: 'Recherche de fuite', description: 'Diagnostic précis sans casse inutile, grâce à des outils de détection professionnels.', icon: 'leak' },
        { label: 'Rénovation salle de bain', description: 'Douche, robinetterie, WC et sanitaires neufs posés proprement, du devis à la finition.', icon: 'bath' },
        { label: 'Chauffe-eau & chaudière', description: "Entretien, remplacement et mise aux normes de vos équipements de production d'eau chaude.", icon: 'heater' },
        { label: 'Débouchage & canalisations', description: 'Évacuations, colonnes et réseaux dégagés durablement, sans abîmer vos installations.', icon: 'drain' },
      ],
    },
    {
      component: 'why_us',
      heading: 'Un artisan, pas un standard téléphonique',
      items: [
        { label: 'Devis gratuit et transparent avant chaque intervention' },
        { label: 'Un artisan qualifié de A à Z — jamais de sous-traitance' },
        { label: "Intervention en moins de 2 h en cas d'urgence" },
        { label: 'Travail soigné, garanti et facturé au juste prix' },
      ],
    },
    {
      component: 'contact',
      heading: 'Un problème de plomberie ?',
      subheading: 'Réponse sous 2h · Devis gratuit · Intervention rapide à Bordeaux',
      email: 'contact@dupont-plomberie.fr',
      phone: '05 56 12 34 56',
      city: 'Bordeaux',
    },
  ],
}
</script>
