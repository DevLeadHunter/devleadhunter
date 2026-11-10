/** Personalisation variables for email templates (mirrors `api/services/email_variables.py`). */

export type EmailVariable = {
  key: string
  token: string
  label: string
  description: string
  example: string
}

/** A variable a product module adds to the catalog. */
export type ModuleEmailVariable = EmailVariable & {
  placeAfterKey?: string
}

const moduleVariablesByModule: Map<string, ModuleEmailVariable[]> = new Map()

export class EmailVariables {
  private constructor() {}

  static readonly coreCatalog: EmailVariable[] = [
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
    {
      key: 'ancien_site',
      token: '{ancien_site}',
      label: 'Ancien site',
      description:
        'Domaine du site mort du prospect (vide s’il n’en a pas) — pour l’accroche « votre site ne répond plus ».',
      example: 'garage-du-viaduc.business.site',
    },
    {
      key: 'prix',
      token: '{prix}',
      label: 'Prix',
      description:
        'Prix de vente configuré, dans la monnaie du prospect : « 500 € », « ≈ 470 CHF », « ≈ 800 $ CA ». Vide dans un premier email — à réserver aux relances.',
      example: '500 €',
    },
    {
      key: 'date_expiration',
      token: '{date_expiration}',
      label: 'Date d’expiration',
      description:
        'Date à laquelle la démo du prospect sera retirée (TTL réel). Nécessite une démo active, comme {lien_demo}.',
      example: '12 octobre',
    },
  ]

  /**
   * Register the variables a module adds, or replace the ones it registered before.
   * @param moduleKey - The module whose offer uses them.
   * @param variables - Its variables, each placed after a core one.
   */
  static registerModuleVariables(moduleKey: string, variables: ModuleEmailVariable[]): void {
    moduleVariablesByModule.set(moduleKey, variables)
  }

  /**
   * Every variable: the core's, then each registered module's, placed after the variable it follows.
   * @returns The variables, in palette order.
   */
  static get catalog(): EmailVariable[] {
    return EmailVariables.catalogOf((): boolean => true)
  }

  /**
   * The variables the palette offers: the core's, plus those of the modules that can be used.
   * @param isModuleUsable - Whether a module's variables are offered (a module switched off is not).
   * @returns The variables, in palette order.
   */
  static catalogOf(isModuleUsable: (moduleKey: string) => boolean): EmailVariable[] {
    const catalog: EmailVariable[] = [...EmailVariables.coreCatalog]
    moduleVariablesByModule.forEach((variables: ModuleEmailVariable[], moduleKey: string): void => {
      if (!isModuleUsable(moduleKey)) {
        return
      }
      for (const variable of variables) {
        const previousIndex: number = catalog.findIndex(
          (candidate: EmailVariable): boolean => candidate.key === variable.placeAfterKey,
        )

        if (previousIndex < 0) {
          catalog.push(variable)
        } else {
          catalog.splice(previousIndex + 1, 0, variable)
        }
      }
    })
    return catalog
  }

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
