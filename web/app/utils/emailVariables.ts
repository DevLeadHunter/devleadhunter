/**
 * Personalisation variables available in email templates.
 *
 * Mirrors the backend source of truth (`api/services/email_variables.py`). Used
 * to render the clickable variable palette, the `{`-autocomplete and the preview
 * sample values — no more hard-coded prose or stale English keys.
 * @module utils/emailVariables
 */

/** One personalisation variable and its display metadata. */
export interface EmailVariable {
  /** Raw key without braces (e.g. `salutation`). */
  key: string
  /** Full placeholder as typed in a template (e.g. `{salutation}`). */
  token: string
  /** Short French label for the palette. */
  label: string
  /** What the variable resolves to, in plain French. */
  description: string
  /** Realistic example value shown on hover / in the preview. */
  example: string
}

/**
 * The available variables, in the order they should appear in the palette.
 * `example` values also feed the template preview so `{salutation}`, `{entreprise}`…
 * actually resolve to something realistic.
 */
export const EMAIL_VARIABLES: EmailVariable[] = [
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
 * Sample substitution map (key → example) used to render a realistic preview.
 * @returns A record mapping each variable key to its example value.
 */
export function buildPreviewSampleVariables(): Record<string, string> {
  return EMAIL_VARIABLES.reduce<Record<string, string>>(
    (map: Record<string, string>, variable: EmailVariable): Record<string, string> => {
      map[variable.key] = variable.example
      return map
    },
    {},
  )
}
