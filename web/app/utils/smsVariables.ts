/** Personalisation variables of the SMS templates (mirrors `api/services/sms_variables.py`). */

export type SmsVariable = {
  key: string
  token: string
  label: string
  example: string
}

export class SmsVariables {
  private constructor() {}

  static readonly catalog: SmsVariable[] = [
    { key: 'salutation', token: '{salutation}', label: 'Salutation', example: 'Bonjour Jean' },
    { key: 'entreprise', token: '{entreprise}', label: 'Entreprise', example: 'Garage Martin' },
    { key: 'ville', token: '{ville}', label: 'Ville', example: 'Lyon' },
    { key: 'metier', token: '{metier}', label: 'Métier', example: 'garagiste' },
    { key: 'lien_demo', token: '{lien_demo}', label: 'Lien démo', example: 'demo.dibodev.fr/s/garage-martin' },
    { key: 'lien_video', token: '{lien_video}', label: 'Lien vidéo', example: 'demo.dibodev.fr/s/v/garage-martin' },
    { key: 'ancien_site', token: '{ancien_site}', label: 'Ancien site', example: 'garage-martin.fr' },
    { key: 'prix', token: '{prix}', label: 'Prix', example: '500 €' },
    { key: 'telephone', token: '{telephone}', label: 'Téléphone de contact', example: '06 12 34 56 78' },
    { key: 'signature', token: '{signature}', label: 'Signature', example: 'Léo' },
  ]

  /**
   * First word of an account name, the sign-off of every SMS (mirrors the API rule).
   * @param accountName - The sender's full name, when known.
   * @returns The first name, empty when unknown.
   */
  static firstNameOf(accountName: string | null | undefined): string {
    const trimmed: string = (accountName ?? '').trim()
    return trimmed ? (trimmed.split(' ')[0] ?? '') : ''
  }

  /**
   * Substitute every known variable by its example value, the signature by the sender's real first name.
   * @param content - A template body still holding `{variable}` tokens.
   * @param signature - The sender's first name; falls back to the catalog example when empty.
   * @returns The content with every known token replaced.
   */
  static renderWithSampleValues(content: string, signature: string): string {
    return SmsVariables.catalog.reduce<string>((rendered: string, variable: SmsVariable): string => {
      const value: string = variable.key === 'signature' && signature ? signature : variable.example
      return rendered.split(variable.token).join(value)
    }, content)
  }
}
