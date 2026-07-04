<template>
  <DemoPlumberCuivrePage :content="content" business-name="Plomberie Rivière" />
</template>

<script lang="ts" setup>
/**
 * PAGE TEMPORAIRE DE PREVIEW (plumber-cuivre) — à supprimer après revue.
 * Reproduit la sortie exacte de build_content() côté API, avec l'enrichissement
 * simulé (photos, avis, note, horaires). Ajouter `?bare=1` à l'URL pour voir
 * l'état « sans enrichissement » (aucune photo, aucun avis) : le design doit
 * rester impeccable. N'écrase aucune autre template.
 */
import type { ComputedRef } from 'vue'
import DemoPlumberCuivrePage from '~/components/templates/plumber-cuivre/index.vue'

const route = useRoute()

/** Mode « sans enrichissement » : ?bare=1. */
const isBare: ComputedRef<boolean> = computed((): boolean => route.query.bare === '1')

const heroImage = 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1400&q=75'
const galleryImages: string[] = [
  'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1507089947368-19c1da9775ae?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1564540583246-934409427776?auto=format&fit=crop&w=1200&q=70',
  'https://images.unsplash.com/photo-1585128792020-803d29415281?auto=format&fit=crop&w=1200&q=70',
]

const content: ComputedRef<Record<string, unknown>> = computed(
  (): Record<string, unknown> => ({
    theme: { primary: '#1080B4', secondary: '#10293D', accent: '#22A8C4' },
    body: [
      {
        component: 'cuivre_hero',
        badge: 'Artisan plombier — Rennes',
        title: 'Plomberie Rivière',
        subtitle:
          'Dépannage, débouchage, chauffe-eau et salle de bain — un travail propre, garanti, au juste prix à Rennes.',
        city: 'Rennes',
        phone: '02 99 12 34 56',
        cta_call_label: 'Appeler maintenant',
        cta_quote_label: 'Demander un devis',
        image: isBare.value ? '' : heroImage,
        image_caption: 'Chantier récent — Rennes',
        points: [
          { component: 'cuivre_hero_point', label: 'Devis gratuit' },
          { component: 'cuivre_hero_point', label: 'Prix annoncé avant travaux' },
          { component: 'cuivre_hero_point', label: 'Chantier laissé propre' },
        ],
      },
      {
        component: 'cuivre_trust',
        items: [
          { component: 'cuivre_trust_item', value: '7j/7', label: 'dépannage & urgences' },
          { component: 'cuivre_trust_item', value: '10 ans', label: 'garantie décennale' },
          { component: 'cuivre_trust_item', value: '0 €', label: 'le devis, toujours gratuit' },
          isBare.value
            ? { component: 'cuivre_trust_item', value: '< 24 h', label: 'réponse à votre demande' }
            : { component: 'cuivre_trust_item', value: '4,8/5', label: 'Avis Google' },
        ],
      },
      {
        component: 'cuivre_emergency',
        heading: "Une fuite ? Réagissez vite, on s'occupe du reste.",
        text:
          "Fuite d'eau, dégât des eaux, canalisation bouchée ou ballon en panne : coupez l'eau, appelez — un plombier vous guide au téléphone et intervient rapidement.",
        phone: '02 99 12 34 56',
        availability_label: '7j/7 — week-ends compris',
        items: [
          { component: 'cuivre_emergency_item', label: 'Recherche de fuite sans casse inutile' },
          { component: 'cuivre_emergency_item', label: 'Débouchage et remise en service' },
          { component: 'cuivre_emergency_item', label: 'Intervention possible le jour même' },
        ],
      },
      {
        component: 'cuivre_services',
        heading: "Ce qu'on répare, pose et rénove",
        subheading:
          "Pour les particuliers et les professionnels, à Rennes — de la fuite réparée dans l'heure à la salle de bain livrée clé en main.",
        items: [
          {
            component: 'cuivre_service_item',
            label: 'Dépannage & recherche de fuite',
            description: 'Fuites visibles ou cachées : détection précise, réparation durable, dégâts limités.',
          },
          {
            component: 'cuivre_service_item',
            label: 'Débouchage de canalisations',
            description: 'WC, éviers, douches, colonnes : un débouchage propre, au furet ou à la pompe, sans abîmer vos installations.',
          },
          {
            component: 'cuivre_service_item',
            label: 'Chauffe-eau & ballon',
            description: "Remplacement, entretien et réglage — de l'électrique au thermodynamique, dimensionné pour votre foyer.",
          },
          {
            component: 'cuivre_service_item',
            label: 'Chauffage & radiateurs',
            description: 'Purge, équilibrage, remplacement de radiateurs et raccordements — pour un hiver sans mauvaise surprise.',
          },
          {
            component: 'cuivre_service_item',
            label: 'Salle de bain clé en main',
            description: 'De la dépose à la pose finale : douche, baignoire, meubles — coordonné avec les bons corps de métier.',
          },
          {
            component: 'cuivre_service_item',
            label: 'Robinetterie & sanitaires',
            description: 'Pose et remplacement de robinets, WC, éviers — des marques fiables, posées dans les règles.',
          },
          {
            component: 'cuivre_service_item',
            label: 'Cuisine & électroménager',
            description: "Évier, lave-vaisselle, lave-linge : arrivées d'eau, évacuations et pose soignée, sans fuite au premier cycle.",
          },
          {
            component: 'cuivre_service_item',
            label: 'Entretien & mise en conformité',
            description: "Adoucisseur, groupe de sécurité, arrivées d'eau : une installation saine, durable et aux normes.",
          },
        ],
      },
      {
        component: 'cuivre_craft',
        kicker: "Les règles de l'art",
        heading: 'Un chantier bien fait, ça se voit aux détails.',
        text:
          "Derrière chaque intervention, il y a des gestes de métier : protéger les lieux, poser du matériel de qualité, tester l'étanchéité, et laisser le chantier plus propre qu'en arrivant.",
        items: [
          {
            component: 'cuivre_craft_item',
            label: 'Matériel de qualité',
            description: 'Cuivre, laiton et marques éprouvées — pas de premier prix qui lâche dans deux ans.',
          },
          {
            component: 'cuivre_craft_item',
            label: 'Étanchéité testée',
            description: 'Chaque raccord est mis en pression et contrôlé avant de refermer.',
          },
          {
            component: 'cuivre_craft_item',
            label: 'Chantier protégé',
            description: 'Sols bâchés, meubles couverts, évacuation des gravats comprise.',
          },
          {
            component: 'cuivre_craft_item',
            label: "Règles de l'art",
            description: 'Des installations conformes aux DTU et aux normes en vigueur.',
          },
        ],
      },
      {
        component: 'cuivre_about',
        kicker: 'Votre plombier',
        heading: "Un artisan d'ici, pas une plateforme.",
        text:
          "Quand vous appelez, c'est un plombier qui répond — pas un centre d'appels. Le diagnostic est honnête, le devis est clair, et le travail est fait avec le même soin que s'il s'agissait de notre propre maison. Vous savez toujours qui entre chez vous, ce qui sera fait, et pour quel prix.",
        image: isBare.value ? '' : 'https://images.unsplash.com/photo-1620626011761-996317b8d101?auto=format&fit=crop&w=1200&q=70',
        image_caption: 'Au travail — Rennes',
        points: [
          { component: 'cuivre_about_point', label: 'Artisan assuré — RC Pro & garantie décennale' },
          { component: 'cuivre_about_point', label: 'Réponse sous 24 h, devis détaillé sous 48 h' },
          { component: 'cuivre_about_point', label: 'Conseils francs : on ne vend que ce qui est utile' },
        ],
      },
      {
        component: 'cuivre_gallery',
        heading: 'Nos chantiers récents',
        subheading: 'Salles de bain, chaufferies, cuisines : un aperçu de nos derniers chantiers.',
        items: isBare.value
          ? []
          : galleryImages.map((image: string, index: number): Record<string, unknown> => ({
              component: 'cuivre_gallery_item',
              image,
              caption: ['Salle de bain — rénovation', 'Maison — réseau neuf', 'Douche italienne', 'Salle d’eau', 'Robinetterie'][index] ?? '',
            })),
      },
      {
        component: 'cuivre_process',
        heading: 'Comment ça se passe',
        subheading: 'Du premier appel à la remise en eau — simple et sans surprise.',
        items: [
          {
            component: 'cuivre_process_item',
            title: 'Vous appelez',
            description: 'On qualifie votre besoin et, en urgence, on vous donne les premiers gestes au téléphone.',
          },
          {
            component: 'cuivre_process_item',
            title: 'Visite & devis',
            description: 'On se déplace, on constate, et vous recevez un devis clair, gratuit et détaillé.',
          },
          {
            component: 'cuivre_process_item',
            title: 'Intervention',
            description: 'Travail soigné, matériel de qualité, étanchéité testée avant de refermer.',
          },
          {
            component: 'cuivre_process_item',
            title: 'Contrôle & nettoyage',
            description: 'On vérifie tout avec vous et on laisse le chantier propre.',
          },
        ],
      },
      {
        component: 'cuivre_reviews',
        heading: 'Ce que disent nos clients',
        items: isBare.value
          ? []
          : [
              {
                component: 'cuivre_review_item',
                quote:
                  "Fuite sous l'évier un dimanche soir : rappelé en dix minutes, guidé pour couper l'eau, réparé le lendemain matin. Sérieux, propre et honnête sur le prix.",
                author: 'Camille B.',
                rating: 5,
              },
              {
                component: 'cuivre_review_item',
                quote:
                  'Remplacement de notre chauffe-eau : devis clair, pose soignée, tout expliqué. Le chantier était impeccable en partant.',
                author: 'Hervé M.',
                rating: 5,
              },
              {
                component: 'cuivre_review_item',
                quote:
                  "Salle de bain refaite du sol au plafond. Délais tenus, belles finitions, et un vrai suivi du début à la fin. Je recommande sans hésiter.",
                author: 'Nathalie P.',
                rating: 4,
              },
            ],
      },
      {
        component: 'cuivre_brands',
        heading: 'Du matériel qui dure',
        subheading: 'Des marques couramment posées et garanties — choisies pour leur fiabilité, pas pour la marge.',
        items: [
          { component: 'cuivre_brand_item', label: 'Grohe' },
          { component: 'cuivre_brand_item', label: 'Hansgrohe' },
          { component: 'cuivre_brand_item', label: 'Geberit' },
          { component: 'cuivre_brand_item', label: 'Jacob Delafon' },
          { component: 'cuivre_brand_item', label: 'Atlantic' },
          { component: 'cuivre_brand_item', label: 'Thermor' },
          { component: 'cuivre_brand_item', label: 'De Dietrich' },
          { component: 'cuivre_brand_item', label: 'Villeroy & Boch' },
        ],
      },
      {
        component: 'cuivre_zone',
        heading: "Secteur d'intervention",
        city: 'Rennes',
        area_label: 'Rennes et ses alentours',
        note: 'Le déplacement est inclus dans le devis — pas de frais cachés.',
      },
      {
        component: 'cuivre_faq',
        heading: 'Questions fréquentes',
        items: [
          {
            component: 'cuivre_faq_item',
            question: 'Le devis est-il vraiment gratuit ?',
            answer:
              'Oui. Le déplacement pour constater et le chiffrage sont gratuits et sans engagement. Le prix validé ensemble est le prix payé.',
          },
          {
            component: 'cuivre_faq_item',
            question: 'En combien de temps intervenez-vous pour une fuite ?',
            answer:
              "Les urgences passent en priorité : l'objectif est d'intervenir dans la journée. Au téléphone, on vous donne aussi les premiers gestes pour limiter les dégâts.",
          },
          {
            component: 'cuivre_faq_item',
            question: 'Travaillez-vous avec les assurances en cas de dégât des eaux ?',
            answer:
              'Oui. On vous fournit les éléments nécessaires à votre dossier (constat, factures, photos) et, si besoin, une recherche de fuite documentée.',
          },
          {
            component: 'cuivre_faq_item',
            question: 'Vos travaux sont-ils garantis ?',
            answer:
              'Oui. Les travaux sont couverts par la garantie décennale et une assurance responsabilité civile professionnelle ; le matériel posé conserve sa garantie fabricant.',
          },
          {
            component: 'cuivre_faq_item',
            question: 'Pouvez-vous rénover une salle de bain complète ?',
            answer:
              'Oui, en coordonnant les corps de métier nécessaires (carrelage, électricité) pour livrer une salle de bain terminée, prête à utiliser.',
          },
          {
            component: 'cuivre_faq_item',
            question: 'Quels moyens de paiement acceptez-vous ?',
            answer:
              'Carte, virement ou chèque, avec une facture détaillée remise après chaque intervention. Pour les gros chantiers, un échéancier peut être convenu au devis.',
          },
          {
            component: 'cuivre_faq_item',
            question: 'Quels délais pour des travaux planifiés ?',
            answer:
              "Après validation du devis, une date est calée ensemble — en général sous une à trois semaines selon la saison et l'ampleur du chantier. La date convenue est tenue.",
          },
          {
            component: 'cuivre_faq_item',
            question: 'Intervenez-vous pour les copropriétés et les professionnels ?',
            answer:
              'Oui : syndics, gestionnaires, commerces et petites entreprises. Interventions documentées (photos, rapport) et facturation adaptée.',
          },
        ],
      },
      {
        component: 'cuivre_contact',
        heading: 'Parlons de votre projet',
        subheading:
          'Une fuite, un chauffe-eau, une salle de bain : décrivez votre besoin, vous recevez une réponse rapide et un devis gratuit.',
        phone: '02 99 12 34 56',
        email: 'contact@plomberieriviere.fr',
        city: 'Rennes',
        hours: isBare.value ? '' : 'Lun–Ven 8h–19h · Sam 9h–12h',
        cta_label: 'Appeler maintenant',
      },
    ],
  }),
)
</script>
