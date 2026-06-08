<template>
  <DemoPlumberSignaturePage :content="content" business-name="Dupont Plomberie" />
</template>

<script lang="ts" setup>
import DemoPlumberSignaturePage from '~/components/templates/plumber-signature/index.vue'
// PAGE TEMPORAIRE DE PREVIEW (signature) — à supprimer après revue. N'écrase aucune autre template.
const img1 = 'https://images.unsplash.com/photo-1607472586893-edb57bdc0e39'
const img2 = 'https://images.unsplash.com/photo-1581578731548-c64695cc6952'
const img3 = 'https://images.unsplash.com/photo-1585704032915-c3400ca199e7'
const img4 = 'https://images.unsplash.com/photo-1620626011761-996317b8d101'
const content = {
  theme: { primary: '#0F5257', secondary: '#14181C', accent: '#E8552D' },
  body: [
    {
      component: 'hero',
      badge: 'Artisan plombier',
      title: 'Dupont Plomberie',
      subtitle: 'Dépannage, recherche de fuite et rénovation — un travail soigné, garanti, au juste prix.',
      cta_label: 'Appeler maintenant',
      phone: '05 56 12 34 56',
      city: 'Bordeaux',
      image: img1,
      points: ['Devis gratuit', 'Intervention rapide', 'Travail garanti'],
    },
    {
      component: 'trust',
      items: [
        { value: '15 ans', label: "D'expérience" },
        { value: '< 2h', label: 'En urgence' },
        { value: '4,9/5', label: 'Avis Google' },
        { value: '+800', label: 'Chantiers' },
      ],
    },
    {
      component: 'services',
      heading: 'Ce que nous prenons en charge',
      subheading: 'Particuliers et professionnels à Bordeaux et alentours.',
      items: [
        { label: "Dépannage d'urgence", description: 'Fuite, panne, canalisation bouchée — 24h/24.', icon: 'emergency' },
        { label: 'Recherche de fuite', description: 'Détection précise sans casse inutile.', icon: 'search' },
        { label: 'Rénovation salle de bain', description: 'Du devis à la finition.', icon: 'bath' },
        { label: 'Chauffe-eau & chaudière', description: 'Entretien et mise aux normes.', icon: 'heater' },
      ],
    },
    {
      component: 'steps',
      heading: 'Comment ça se passe',
      subheading: 'En toute simplicité, du premier appel à la facture.',
      items: [
        { title: 'Vous appelez', description: 'On évalue votre besoin au téléphone.', icon: 'phone' },
        { title: 'Devis gratuit', description: 'Un prix clair, sans surprise.', icon: 'doc' },
        { title: 'Intervention', description: 'Travail soigné et garanti.', icon: 'install' },
        { title: 'Paiement', description: 'Une fois satisfait, au juste prix.', icon: 'euro' },
      ],
    },
    {
      component: 'gallery',
      heading: 'Quelques chantiers récents',
      subheading: 'Un aperçu de notre travail.',
      items: [
        { image: img2, caption: 'Rénovation complète', location: 'Bordeaux Centre' },
        { image: img3, caption: 'Salle de bain moderne', location: 'Mérignac' },
        { image: img4, caption: 'Réparation urgente', location: 'Pessac' },
        { image: img1, caption: 'Installation chauffe-eau', location: 'Talence' },
      ],
    },
    {
      component: 'before_after',
      heading: 'Le résultat parle de lui-même',
      subheading: 'Glissez pour comparer.',
      before_image: img2,
      after_image: img3,
      before_label: 'Avant',
      after_label: 'Après',
      caption: 'Rénovation salle de bain — 3 jours de travaux.',
    },
    {
      component: 'story',
      kicker: "L'artisan",
      heading: 'Un savoir-faire transmis, pas sous-traité',
      image: img2,
      paragraphs: [
        'Artisan plombier depuis 15 ans, je prends en charge chaque chantier de A à Z.',
        'Pas de sous-traitance : vous avez affaire à un seul interlocuteur, du devis à la finition.',
      ],
      values: [
        { label: 'Travail garanti', description: 'Chaque intervention est garantie.', icon: 'shield' },
        { label: 'Juste prix', description: 'Devis transparent, sans surprise.', icon: 'euro' },
      ],
      stats: [
        { value: '15 ans', label: 'Métier' },
        { value: '+800', label: 'Clients' },
      ],
      signature_name: 'Jean Dupont',
      signature_role: 'Artisan plombier',
    },
    {
      component: 'testimonials',
      heading: 'Ce que disent nos clients',
      items: [
        { quote: 'Intervention rapide et travail impeccable. Je recommande !', author: 'Marie L.', location: 'Bordeaux', rating: 5 },
        { quote: 'Très professionnel, devis respecté au centime près.', author: 'Paul R.', location: 'Mérignac', rating: 5 },
        { quote: 'Disponible en urgence un dimanche, sauvé !', author: 'Sophie M.', location: 'Pessac', rating: 5 },
      ],
    },
    {
      component: 'faq',
      heading: 'Vous vous demandez peut-être…',
      items: [
        { question: 'Intervenez-vous en urgence ?', answer: 'Oui, 24h/24 et 7j/7 pour les urgences plomberie.' },
        { question: 'Le devis est-il gratuit ?', answer: 'Toujours. Et sans engagement.' },
        { question: 'Quelle zone couvrez-vous ?', answer: 'Bordeaux et toute la métropole.' },
      ],
    },
    {
      component: 'urgency',
      heading: 'Une fuite, une panne, une urgence ?',
      subheading: 'On décroche et on intervient vite. 24 h/24, 7 j/7.',
      phone: '05 56 12 34 56',
    },
    {
      component: 'contact',
      heading: 'Parlons de votre projet',
      subheading: 'Réponse rapide, devis sans engagement.',
      email: 'contact@dupont-plomberie.fr',
      phone: '05 56 12 34 56',
      city: 'Bordeaux',
      hours: 'Lun–Sam 8 h–20 h · Urgences 24 h/24',
    },
  ],
}
</script>
