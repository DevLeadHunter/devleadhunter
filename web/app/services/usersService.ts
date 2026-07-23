import type { User } from '~/types'
import { ApiClient } from './api'

const USERS_BASE_URL: string = '/api/v1/users'

export class UsersService {
  /**
   * Get all users (admin only)
   * @returns List of users
   * @throws If request fails
   */
  static async getAllUsers(): Promise<User[]> {
    return ApiClient.get<User[]>(USERS_BASE_URL)
  }

  /**
   * Get a user by ID (admin only)
   * @param userId - User ID
   * @returns User information
   * @throws If request fails
   */
  static async getUserById(userId: number): Promise<User> {
    return ApiClient.get<User>(`${USERS_BASE_URL}/${userId}`)
  }

  /**
   * Create a new user (admin only)
   * @param userData - User fields plus password.
   * @returns Created user
   * @throws If request fails
   */
  static async createUser(userData: Partial<User> & { password: string }): Promise<User> {
    return ApiClient.post<User>(USERS_BASE_URL, userData)
  }

  /**
   * Update a user (admin only)
   * @param userId - User ID
   * @param userData - Updated user data
   * @returns Updated user
   * @throws If request fails
   */
  static async updateUser(userId: number, userData: Partial<User>): Promise<User> {
    return ApiClient.put<User>(`${USERS_BASE_URL}/${userId}`, userData)
  }

  /**
   * Delete a user (admin only)
   * @param userId - User ID
   * @returns Void
   * @throws If request fails
   */
  static async deleteUser(userId: number): Promise<void> {
    await ApiClient.delete(`${USERS_BASE_URL}/${userId}`)
  }
}
