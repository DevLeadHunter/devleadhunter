import type { Feature, MultiPolygon, Polygon } from 'geojson'

export type RegionContourFeature = Feature<Polygon | MultiPolygon, { code: string } & Record<string, unknown>>

/** Region contour files of the map, read once per session as JSON even when served as HTML (the desktop app does). */
export class RegionContours {
  private static readonly featuresByFile: Map<string, RegionContourFeature[]> = new Map()

  /**
   * Read the polygons of one file that carry their region code; a failed or empty read is asked again next time.
   * @param url - Public path of the file.
   * @returns The file's contours, none when it cannot be read.
   */
  static async read(url: string): Promise<RegionContourFeature[]> {
    const known: RegionContourFeature[] | undefined = RegionContours.featuresByFile.get(url)
    if (known) {
      return known
    }
    const parsed: unknown = await $fetch<unknown>(url, { responseType: 'json' }).catch((): null => null)
    const entries: unknown = RegionContours.isRecord(parsed) ? parsed.features : null
    const features: RegionContourFeature[] = Array.isArray(entries)
      ? entries.filter((entry: unknown): entry is RegionContourFeature => RegionContours.isContour(entry))
      : []
    if (features.length > 0) {
      RegionContours.featuresByFile.set(url, features)
    }
    return features
  }

  /**
   * Whether a parsed value is a usable contour: a polygon or multipolygon with a string region code.
   * @param value - One entry of a file's `features`.
   * @returns True when the map can paint it.
   */
  static isContour(value: unknown): value is RegionContourFeature {
    if (!RegionContours.isRecord(value)) {
      return false
    }
    const { geometry, properties }: { geometry?: unknown; properties?: unknown } = value
    return (
      RegionContours.isRecord(geometry) &&
      RegionContours.isRecord(properties) &&
      (geometry.type === 'Polygon' || geometry.type === 'MultiPolygon') &&
      Array.isArray(geometry.coordinates) &&
      typeof properties.code === 'string'
    )
  }

  /**
   * Whether a parsed value is a plain object whose fields can be read.
   * @param value - Any parsed JSON value.
   * @returns True for a non-null object.
   */
  private static isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null
  }
}
