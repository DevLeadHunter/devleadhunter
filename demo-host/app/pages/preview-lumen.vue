<template>
  <DemoElectricianLumenPage :content="content" business-name="Volt & Fils" />
</template>

<script lang="ts" setup>
/**
 * PAGE TEMPORAIRE DE PREVIEW (electrician-lumen) — à supprimer après revue.
 * Reproduit la sortie exacte de build_content() côté API, avec l'enrichissement
 * simulé (photos, avis, note, horaires). Ajouter `?bare=1` à l'URL pour voir
 * l'état « sans enrichissement » (aucune photo, aucun avis) : le design doit
 * rester impeccable. N'écrase aucune autre template.
 */
import type { ComputedRef } from 'vue'
import DemoElectricianLumenPage from '~/components/templates/electrician-lumen/index.vue'

const route = useRoute()

/** Mode « sans enrichissement » : ?bare=1. */
const isBare: ComputedRef<boolean> = computed((): boolean => route.query.bare === '1')

const heroImage = 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=1400&q=75'
const galleryImages: string[] = [
  'https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&q=70',
]

const content: ComputedRef<Record<string, unknown>> = computed(
  (): Record<string, unknown> => ({
    theme: { primary: '#FFD400', secondary: '#070B14', accent: '#FF9F1C' },
    body: [
      {
        component: 'lumen_hero',
        badge: 'Artisan électricien — Nantes',
        title: 'Volt & Fils',
        subtitle:
          'Dépannage, mise aux normes, rénovation et borne de recharge — un travail propre, sécurisé et garanti à Nantes.',
        city: 'Nantes',
        phone: '02 40 12 34 56',
        cta_call_label: 'Appeler maintenant',
        cta_quote_label: 'Demander un devis',
        image: isBare.value ? '' : heroImage,
        image_caption: 'Chantier récent — Nantes',
        points: [
          { component: 'lumen_hero_point', label: 'Devis gratuit' },
          { component: 'lumen_hero_point', label: 'Déplacement rapide' },
          { component: 'lumen_hero_point', label: 'Travail garanti' },
        ],
      },
      {
        component: 'lumen_trust',
        items: [
          { component: 'lumen_trust_item', value: '7j/7', label: 'dépannage & urgences' },
          { component: 'lumen_trust_item', value: 'NF C 15-100', label: 'installations aux normes' },
          { component: 'lumen_trust_item', value: '10 ans', label: 'garantie décennale' },
          isBare.value
            ? { component: 'lumen_trust_item', value: '< 24 h', label: 'réponse à votre demande' }
            : { component: 'lumen_trust_item', value: '4,9/5', label: 'Avis Google' },
        ],
      },
      {
        component: 'lumen_emergency',
        heading: 'Une panne ? On intervient vite.',
        text:
          "Coupure générale, disjoncteur qui saute, prise qui chauffe ou odeur de brûlé : ne restez pas dans le doute. Un électricien vous répond, vous guide au téléphone et se déplace si nécessaire.",
        phone: '02 40 12 34 56',
        availability_label: '7j/7 — week-ends compris',
        items: [
          { component: 'lumen_emergency_item', label: 'Recherche de panne & remise en service' },
          { component: 'lumen_emergency_item', label: "Mise en sécurité de l'installation" },
          { component: 'lumen_emergency_item', label: 'Intervention possible le jour même' },
        ],
      },
      {
        component: 'lumen_services',
        heading: "Ce qu'on installe, répare et sécurise",
        subheading:
          'Pour les particuliers et les professionnels, à Nantes — du dépannage ponctuel à la rénovation complète.',
        items: [
          {
            component: 'lumen_service_item',
            label: 'Dépannage & recherche de panne',
            description: 'Coupures, courts-circuits, disjoncteur qui saute : diagnostic précis et remise en service rapide.',
            icon: 'panne',
          },
          {
            component: 'lumen_service_item',
            label: 'Tableau électrique & mise aux normes',
            description: 'Remplacement de tableau, différentiels 30 mA, mise en conformité NF C 15-100 de l’installation.',
            icon: 'tableau',
          },
          {
            component: 'lumen_service_item',
            label: 'Rénovation électrique',
            description: 'Rénovation partielle ou complète, en site occupé, avec un chantier propre et des finitions soignées.',
            icon: 'renovation',
          },
          {
            component: 'lumen_service_item',
            label: 'Éclairage & domotique',
            description: 'Éclairage LED intérieur et extérieur, variateurs, volets et chauffage pilotés depuis votre téléphone.',
            icon: 'domotique',
          },
          {
            component: 'lumen_service_item',
            label: 'Borne de recharge (IRVE)',
            description: 'Bornes et prises renforcées pour véhicule électrique, dimensionnées selon votre tableau et votre abonnement.',
            icon: 'irve',
          },
          {
            component: 'lumen_service_item',
            label: 'Interphone & courants faibles',
            description: 'Interphone, visiophone, réseau et TV : des équipements bien intégrés, réglés et fiables.',
            icon: 'interphone',
          },
        ],
      },
      {
        component: 'lumen_safety',
        kicker: 'Sécurité & conformité',
        heading: 'Une installation aux normes, ça ne se négocie pas.',
        text:
          "Une installation vétuste ou mal protégée, c'est un risque d'incendie et d'électrocution. Chaque intervention se termine par une vérification complète : protections, différentiels, mise à la terre.",
        items: [
          { component: 'lumen_safety_item', code: 'NF C 15-100', label: 'La norme de référence, appliquée sur toute installation neuve ou rénovée' },
          { component: 'lumen_safety_item', code: 'Consuel', label: "Attestation de conformité fournie pour les travaux qui l'exigent" },
          { component: 'lumen_safety_item', code: '30 mA', label: "Des différentiels qui coupent avant l'accident, sur chaque rangée" },
          { component: 'lumen_safety_item', code: 'Terre', label: 'Mise à la terre mesurée et contrôlée sur chaque circuit' },
        ],
      },
      {
        component: 'lumen_gallery',
        heading: 'Nos chantiers récents',
        subheading: "Tableaux, rénovations, éclairages : un aperçu de ce qu'on fait de nos journées.",
        items: isBare.value
          ? []
          : galleryImages.map((image: string, index: number): Record<string, unknown> => ({
              component: 'lumen_gallery_item',
              image,
              caption: ['Tableau — pavillon', 'Rénovation complète', 'Éclairage LED', 'Borne IRVE', 'Mise aux normes'][index] ?? '',
            })),
      },
      {
        component: 'lumen_process',
        heading: 'Comment ça se passe',
        subheading: 'Du premier appel à la remise en service — simple et sans surprise.',
        items: [
          { component: 'lumen_process_item', title: 'Vous appelez', description: 'On fait le point sur votre besoin, et on vous guide déjà par téléphone.' },
          { component: 'lumen_process_item', title: 'Diagnostic sur place', description: "On se déplace, on vérifie l'installation et on mesure ce qui doit l'être." },
          { component: 'lumen_process_item', title: 'Devis clair', description: 'Un chiffrage détaillé et sans surprise, validé avant toute intervention.' },
          { component: 'lumen_process_item', title: 'Intervention propre', description: 'Travail soigné, chantier nettoyé, installation testée devant vous.' },
        ],
      },
      {
        component: 'lumen_reviews',
        heading: 'Ce que disent nos clients',
        items: isBare.value
          ? []
          : [
              {
                component: 'lumen_review_item',
                quote:
                  "Intervention le jour même pour une panne générale. Problème trouvé en 20 minutes, tout remis en service et bien expliqué. Sérieux et efficace.",
                author: 'Marie L.',
                rating: 5,
              },
              {
                component: 'lumen_review_item',
                quote:
                  'Remplacement complet de notre vieux tableau électrique. Travail très propre, délais tenus, et le prix annoncé au devis a été respecté au centime.',
                author: 'Julien R.',
                rating: 5,
              },
              {
                component: 'lumen_review_item',
                quote:
                  "Pose d'une borne de recharge pour ma voiture électrique. De bons conseils sur l'abonnement, installation nickel. Je recommande.",
                author: 'Sophie D.',
                rating: 4,
              },
            ],
      },
      {
        component: 'lumen_zone',
        heading: "Zone d'intervention",
        city: 'Nantes',
        area_label: 'Nantes et ses alentours',
        note: 'Le déplacement est inclus dans le devis — pas de frais cachés.',
      },
      {
        component: 'lumen_faq',
        heading: 'Questions fréquentes',
        items: [
          {
            component: 'lumen_faq_item',
            question: 'Le devis est-il vraiment gratuit ?',
            answer:
              "Oui. Le déplacement pour établir le devis et le chiffrage sont gratuits et sans engagement. Le prix annoncé est le prix payé.",
          },
          {
            component: 'lumen_faq_item',
            question: 'En combien de temps pouvez-vous intervenir ?',
            answer:
              "Pour un dépannage, l'objectif est d'intervenir dans la journée selon l'urgence et le planning. Pour des travaux, une date est fixée ensemble dès la validation du devis.",
          },
          {
            component: 'lumen_faq_item',
            question: 'Mon installation est ancienne, faut-il tout refaire ?',
            answer:
              "Pas forcément. Après un diagnostic, on distingue ce qui doit être mis en sécurité immédiatement de ce qui peut être planifié. Vous décidez, en connaissance de cause.",
          },
          {
            component: 'lumen_faq_item',
            question: 'Vos travaux sont-ils garantis ?',
            answer:
              'Oui. Les travaux sont couverts par la garantie décennale et une assurance responsabilité civile professionnelle. Les équipements posés conservent leur garantie fabricant.',
          },
          {
            component: 'lumen_faq_item',
            question: 'Installez-vous des bornes pour véhicule électrique ?',
            answer:
              'Oui, bornes et prises renforcées (IRVE). On dimensionne la solution selon votre tableau, votre abonnement et votre véhicule.',
          },
        ],
      },
      {
        component: 'lumen_contact',
        heading: 'Parlons de votre projet',
        subheading: 'Décrivez votre besoin — vous recevez une réponse rapide et un devis gratuit.',
        phone: '02 40 12 34 56',
        email: 'contact@voltetfils.fr',
        city: 'Nantes',
        hours: isBare.value ? '' : 'Lun–Ven 8h–19h · Sam 9h–12h',
        cta_label: 'Appeler maintenant',
      },
    ],
  }),
)
</script>
