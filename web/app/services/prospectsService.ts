import { api } from '~/services/api'

import type {
  Prospect,
  ProspectCreatePayload,
  ProspectUpdatePayload,
  ProspectEnrichPayload,
  ProspectSearchSuggestion,
  ProspectSearchSuggestionsPayload,
} from '~/types'

const BASE_URL: string = '/api/v1/prospects'

/**
 
 * Pré-remplit les champs d'un prospect depuis Google Maps.
 
 * @param payload - Nom d'entreprise, lien Google Maps et/ou ville.
 
 * @returns Les champs prospect pré-remplis.
 
 */

/**
 *
 */
export async function enrichProspect(payload: ProspectEnrichPayload): Promise<ProspectCreatePayload> {
  return api.post<ProspectCreatePayload>(`${BASE_URL}/enrich`, payload)
}

/**
 
 * Recherche des suggestions d'entreprises sur Google Maps.
 
 * @param payload - Requête de recherche et filtres optionnels.
 
 * @returns La liste des suggestions correspondantes.
 
 */

/**
 *
 */
export async function searchProspectSuggestions(
  payload: ProspectSearchSuggestionsPayload,
): Promise<ProspectSearchSuggestion[]> {
  return api.post<ProspectSearchSuggestion[]>(`${BASE_URL}/search-suggestions`, payload)
}

/**
 
 * Crée un prospect manuellement.
 
 * @param payload - Données du prospect à enregistrer.
 
 * @returns Le prospect créé.
 
 */

/**
 *
 */
export async function createProspect(payload: ProspectCreatePayload): Promise<Prospect> {
  return api.post<Prospect>(BASE_URL, payload)
}

/**
 
 * Liste les prospects sauvegardés de l'utilisateur courant.
 
 * @returns Les prospects enregistrés.
 
 */

/**
 *
 */
export async function listProspects(): Promise<Prospect[]> {
  return api.get<Prospect[]>(BASE_URL)
}

/**

 * Met à jour les champs d'un prospect existant.

 * @param prospectId - Identifiant du prospect à modifier.
 * @param payload - Champs à mettre à jour (partiels).
 * @returns Le prospect mis à jour.

 */
export async function updateProspect(prospectId: number, payload: ProspectUpdatePayload): Promise<Prospect> {
  return api.put<Prospect>(`${BASE_URL}/${prospectId}`, payload)
}

/**

 * Supprime un prospect par identifiant.
 
 * @param prospectId - Identifiant du prospect à supprimer.
 
 * @returns Une promesse résolue une fois la suppression effectuée.
 
 */

/**
 *
 */
export async function deleteProspect(prospectId: number): Promise<void> {
  await api.delete(`${BASE_URL}/${prospectId}`)
}
