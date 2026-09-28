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

  /**
   * The machine-readable code of a refused call, when the API sent one (`detail: { code, message }`).
   * @param error - What `$fetch` threw.
   * @returns The code, or null (a sentence, field errors, no answer).
   */
  static code(error: unknown): string | null {
    const detail: unknown = (error as ApiRefusal | null)?.data?.detail
    if (typeof detail !== 'object' || detail === null || Array.isArray(detail)) return null
    const code: unknown = (detail as Record<string, unknown>).code
    return typeof code === 'string' ? code : null
  }
}
