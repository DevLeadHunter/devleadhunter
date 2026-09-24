import type { ApiRefusal } from '~/types/ApiRefusal'

/**
 * Reads the API's answer out of the error `$fetch` throws when a call fails.
 */
export class ApiRefusalUtils {
  /**
   * The HTTP status of a failed API call, when it has one.
   * @param error - What `$fetch` threw.
   * @returns The status code, or undefined for a network failure.
   */
  static status(error: unknown): number | undefined {
    return (error as ApiRefusal | null)?.statusCode
  }

  /**
   * The API's explanation of a refused call, when it sent a readable one.
   * @param error - What `$fetch` threw.
   * @returns The detail sentence, or null (no detail, or a list of field errors).
   */
  static detail(error: unknown): string | null {
    const detail: unknown = (error as ApiRefusal | null)?.data?.detail
    return typeof detail === 'string' ? detail : null
  }
}
