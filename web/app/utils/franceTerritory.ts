/**
 * Static metropolitan-France reference data for the prospection coverage page —
 * region names (INSEE codes, matching the france-geojson contours the map uses)
 * and a curated list of major cities used to suggest « zones à attaquer ».
 * Pure data, no Vue/Nuxt dependency.
 */

/** The 13 metropolitan regions, keyed by INSEE region code. */
export const FRANCE_REGIONS: Readonly<Record<string, string>> = {
  '11': 'Île-de-France',
  '24': 'Centre-Val de Loire',
  '27': 'Bourgogne-Franche-Comté',
  '28': 'Normandie',
  '32': 'Hauts-de-France',
  '44': 'Grand Est',
  '52': 'Pays de la Loire',
  '53': 'Bretagne',
  '75': 'Nouvelle-Aquitaine',
  '76': 'Occitanie',
  '84': 'Auvergne-Rhône-Alpes',
  '93': "Provence-Alpes-Côte d'Azur",
  '94': 'Corse',
}

/** A major French city suggested as a prospection target. */
export type FranceMajorCity = {
  /** Display name. */
  name: string
  /** Department code (« 69 », « 2A »…). */
  dept: string
  /** INSEE region code (keys of FRANCE_REGIONS). */
  region: string
}

/**
 * The largest metropolitan cities (by population), used to surface
 * « villes jamais prospectées » — ordered by rough population so the biggest
 * opportunities come first.
 */
export const FRANCE_MAJOR_CITIES: ReadonlyArray<FranceMajorCity> = [
  { name: 'Paris', dept: '75', region: '11' },
  { name: 'Marseille', dept: '13', region: '93' },
  { name: 'Lyon', dept: '69', region: '84' },
  { name: 'Toulouse', dept: '31', region: '76' },
  { name: 'Nice', dept: '06', region: '93' },
  { name: 'Nantes', dept: '44', region: '52' },
  { name: 'Montpellier', dept: '34', region: '76' },
  { name: 'Strasbourg', dept: '67', region: '44' },
  { name: 'Bordeaux', dept: '33', region: '75' },
  { name: 'Lille', dept: '59', region: '32' },
  { name: 'Rennes', dept: '35', region: '53' },
  { name: 'Reims', dept: '51', region: '44' },
  { name: 'Toulon', dept: '83', region: '93' },
  { name: 'Saint-Étienne', dept: '42', region: '84' },
  { name: 'Le Havre', dept: '76', region: '28' },
  { name: 'Grenoble', dept: '38', region: '84' },
  { name: 'Dijon', dept: '21', region: '27' },
  { name: 'Angers', dept: '49', region: '52' },
  { name: 'Nîmes', dept: '30', region: '76' },
  { name: 'Clermont-Ferrand', dept: '63', region: '84' },
  { name: 'Le Mans', dept: '72', region: '52' },
  { name: 'Aix-en-Provence', dept: '13', region: '93' },
  { name: 'Brest', dept: '29', region: '53' },
  { name: 'Tours', dept: '37', region: '24' },
  { name: 'Amiens', dept: '80', region: '32' },
  { name: 'Limoges', dept: '87', region: '75' },
  { name: 'Annecy', dept: '74', region: '84' },
  { name: 'Perpignan', dept: '66', region: '76' },
  { name: 'Besançon', dept: '25', region: '27' },
  { name: 'Metz', dept: '57', region: '44' },
  { name: 'Orléans', dept: '45', region: '24' },
  { name: 'Rouen', dept: '76', region: '28' },
  { name: 'Mulhouse', dept: '68', region: '44' },
  { name: 'Caen', dept: '14', region: '28' },
  { name: 'Nancy', dept: '54', region: '44' },
  { name: 'La Rochelle', dept: '17', region: '75' },
  { name: 'Avignon', dept: '84', region: '93' },
  { name: 'Poitiers', dept: '86', region: '75' },
  { name: 'Bayonne', dept: '64', region: '75' },
  { name: 'Ajaccio', dept: '2A', region: '94' },
]
