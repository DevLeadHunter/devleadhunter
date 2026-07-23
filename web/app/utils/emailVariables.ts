/** Personalisation variables for email templates (mirrors `api/services/email_variables.py`). */

export type EmailVariable = {
  key: string
  token: string
  label: string
  description: string
  example: string
}

export class EmailVariables {
  private constructor() {}

  static readonly catalog: EmailVariable[] = [
    {
      key: 'salutation',
      token: '{salutation}',
      label: 'Salutation',
      description:
        'Formule d’accueil sûre selon le contact connu (« Bonjour Jean », « Bonjour M. Dupont » ou « Bonjour »).',
      example: 'Bonjour Jean',
    },
    {
      key: 'prenom',
      token: '{prenom}',
      label: 'Prénom',
      description: 'Prénom du décisionnaire (vide si inconnu — jamais le nom de l’entreprise).',
      example: 'Jean',
    },
    {
      key: 'nom',
      token: '{nom}',
      label: 'Nom',
      description: 'Nom de famille du décisionnaire (vide si inconnu).',
      example: 'Dupont',
    },
    {
      key: 'entreprise',
      token: '{entreprise}',
      label: 'Entreprise',
      description: 'Nom de l’entreprise du prospect.',
      example: 'Restaurant Le Gourmet',
    },
    {
      key: 'ville',
      token: '{ville}',
      label: 'Ville',
      description: 'Ville du prospect.',
      example: 'Lyon',
    },
    {
      key: 'metier',
      token: '{metier}',
      label: 'Métier',
      description: 'Catégorie / métier du prospect.',
      example: 'plombier',
    },
    {
      key: 'email',
      token: '{email}',
      label: 'Email',
      description: 'Adresse email du prospect.',
      example: 'contact@legourmet.fr',
    },
    {
      key: 'phone',
      token: '{phone}',
      label: 'Téléphone',
      description: 'Numéro de téléphone du prospect.',
      example: '01 23 45 67 89',
    },
    {
      key: 'lien_demo',
      token: '{lien_demo}',
      label: 'Lien démo',
      description: 'URL de la démo personnalisée du prospect (l’email n’est pas envoyé si elle manque).',
      example: 'https://demo.dibodev.fr/le-gourmet',
    },
    {
      key: 'lien_video',
      token: '{lien_video}',
      label: 'Lien vidéo',
      description: 'URL de la page vidéo de prospection trackée (vide sans vidéo générée).',
      example: 'https://demo.dibodev.fr/v/le-gourmet',
    },
    {
      key: 'vignette_video',
      token: '{vignette_video}',
      label: 'Vignette vidéo',
      description: 'Bloc image cliquable de la vidéo de prospection (HTML prêt à coller, renvoie au player).',
      example: '[vignette cliquable de la vidéo]',
    },
  ]

  /**
   * Build a sample substitution map for realistic template preview.
   * @returns Record mapping each variable key to its example value.
   */
  static buildPreviewSampleVariables(): Record<string, string> {
    return EmailVariables.catalog.reduce<Record<string, string>>(
      (map: Record<string, string>, variable: EmailVariable): Record<string, string> => {
        map[variable.key] = variable.example
        return map
      },
      {},
    )
  }
}
