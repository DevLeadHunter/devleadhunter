import type { User } from '~/types'
import { api } from './api'

/**
 * Users service for admin user management
 * @module services/usersService
 */

const USERS_BASE_URL = '/api/v1/users'

/**
 * Get all users (admin only)
 * @returns {Promise<User[]>} List of users
 * @throws {Error} If request fails
 */
export async function getAllUsers(): Promise<User[]> {
  return api.get<User[]>(USERS_BASE_URL)
}

/**
 * Get a user by ID (admin only)
 * @param {number} userId - User ID
 * @returns {Promise<User>} User information
 * @throws {Error} If request fails
 */
export async function getUserById(userId: number): Promise<User> {
  return api.get<User>(`${USERS_BASE_URL}/${userId}`)
}

/**
 * Create a new user (admin only)
 * @param {Partial<User> & { password: string }} userData - User data
 * @returns {Promise<User>} Created user
 * @throws {Error} If request fails
 */
export async function createUser(userData: Partial<User> & { password: string }): Promise<User> {
  return api.post<User>(USERS_BASE_URL, userData)
}

/**
 * Update a user (admin only)
 * @param {number} userId - User ID
 * @param {Partial<User>} userData - Updated user data
 * @returns {Promise<User>} Updated user
 * @throws {Error} If request fails
 */
export async function updateUser(userId: number, userData: Partial<User>): Promise<User> {
  return api.put<User>(`${USERS_BASE_URL}/${userId}`, userData)
}

/**
 * Delete a user (admin only)
 * @param {number} userId - User ID
 * @returns {Promise<void>} Void
 * @throws {Error} If request fails
 */
export async function deleteUser(userId: number): Promise<void> {
  await api.delete(`${USERS_BASE_URL}/${userId}`)
}
