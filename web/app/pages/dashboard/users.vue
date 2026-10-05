<template>
  <div class="space-y-5">
    <UiPageHeader
      eyebrow="Administration"
      title="Utilisateurs"
      description="Les comptes ayant accès à l'outil, leur rôle et leur consommation de crédits."
    >
      <template #actions>
        <button
          type="button"
          class="app-btn-secondary h-11 px-4 text-sm whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50 @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          :disabled="isLoading"
          @click="loadUsers"
        >
          <UIcon name="i-lucide-refresh-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
      </template>
      <template #primary-action>
        <button
          type="button"
          class="app-btn-primary h-11 px-4 text-sm whitespace-nowrap @2xl:pointer-fine:h-9 @2xl:pointer-fine:text-xs"
          @click="openUserDrawer('create', null)"
        >
          <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
          Ajouter un utilisateur
        </button>
      </template>
    </UiPageHeader>

    <div
      class="grid grid-cols-2 gap-4 @sm:grid-cols-3 [&>*:last-child:nth-child(odd)]:col-span-2 @sm:[&>*:last-child:nth-child(odd)]:col-span-1"
    >
      <UiStatCard label="Comptes" :value="users.length" icon="i-lucide-users" accent="neutral" />
      <UiStatCard label="Administrateurs" :value="adminCount" icon="i-lucide-shield-check" accent="sky" />
      <UiStatCard label="Crédits consommés" :value="totalCreditsConsumed" icon="i-lucide-coins" accent="emerald" />
    </div>

    <div class="flex justify-end">
      <div class="relative w-full @2xl:pointer-fine:w-72">
        <UIcon
          name="i-lucide-search"
          class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
        />
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Nom ou email…"
          aria-label="Rechercher un utilisateur"
          class="app-input pl-9"
        />
      </div>
    </div>

    <UiLoader v-if="isLoading" label="Chargement des utilisateurs…" />

    <UiEmptyState
      v-else-if="filteredUsers.length === 0"
      title="Aucun utilisateur trouvé"
      :description="searchQuery ? 'Aucun compte ne correspond à votre recherche.' : undefined"
    />

    <div v-else class="app-card overflow-hidden">
      <BaseTable min-width="760px">
        <template #head>
          <BaseTableTh>Utilisateur</BaseTableTh>
          <BaseTableTh>Email</BaseTableTh>
          <BaseTableTh align="center">Rôle</BaseTableTh>
          <BaseTableTh align="right">Crédits dispo.</BaseTableTh>
          <BaseTableTh align="right">Crédits consommés</BaseTableTh>
          <BaseTableTh align="center" sr-only>Actions</BaseTableTh>
        </template>

        <BaseTableTr v-for="user in filteredUsers" :key="user.id">
          <BaseTableTd>
            <span class="flex items-center gap-2.5">
              <span
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] text-xs font-semibold text-[var(--app-ink)]"
              >
                {{ initialsOf(user.name) }}
              </span>
              <span class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ user.name }}</span>
            </span>
          </BaseTableTd>

          <BaseTableTd label="Email" class="font-label text-xs text-[var(--app-ink-soft)]">{{
            user.email
          }}</BaseTableTd>

          <BaseTableTd label="Rôle" align="center">
            <span :class="['app-badge', user.role === 'ADMIN' || user.role === 'SUPER_ADMIN' ? 'app-badge--info' : '']">
              {{ roleLabel(user.role) }}
            </span>
          </BaseTableTd>

          <BaseTableTd label="Crédits dispo." align="right" class="text-sm text-[var(--app-ink)] tabular-nums">
            <span v-if="hasUnlimitedCredits(user)" class="text-[var(--app-ink-soft)]">Illimités</span>
            <span v-else class="font-semibold">{{ user.credits_available }}</span>
          </BaseTableTd>

          <BaseTableTd
            label="Crédits consommés"
            align="right"
            class="text-sm font-semibold text-[var(--app-ink)] tabular-nums"
          >
            {{ user.credits_consumed ?? 0 }}
          </BaseTableTd>

          <BaseTableTd align="center">
            <span class="inline-flex items-center gap-1">
              <button
                type="button"
                class="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                :aria-label="`Modifier ${user.name}`"
                title="Modifier"
                @click="openUserDrawer('edit', user)"
              >
                <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                class="flex h-7 w-7 cursor-pointer items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)]"
                :aria-label="`Supprimer ${user.name}`"
                title="Supprimer"
                @click="askDelete(user)"
              >
                <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
              </button>
            </span>
          </BaseTableTd>
        </BaseTableTr>
      </BaseTable>
    </div>

    <UiConfirmModal
      ref="confirmModal"
      title="Supprimer l'utilisateur"
      :message="deleteMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { User } from '~/types'
import type { UserFormDrawerMode } from '~/types/DrawerStack'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed, onMounted, watch } from 'vue'
import { roleLabel, isPlatformAdmin } from '~/utils/userRoles'
import { UsersService } from '~/services/usersService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'super-admin'],
})

const toast: UseToastReturn = useToast()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const users: Ref<User[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const searchQuery: Ref<string> = ref('')
const deletingUser: Ref<User | null> = ref(null)
const confirmModal: Ref<{ open: () => void } | null> = ref(null)

const filteredUsers: ComputedRef<User[]> = computed((): User[] => {
  const query: string = searchQuery.value.trim().toLowerCase()
  if (!query) return users.value
  return users.value.filter(
    (user: User): boolean => user.name.toLowerCase().includes(query) || user.email.toLowerCase().includes(query),
  )
})

const adminCount: ComputedRef<number> = computed(
  (): number => users.value.filter((user: User): boolean => isPlatformAdmin(user.role)).length,
)

const totalCreditsConsumed: ComputedRef<number> = computed((): number =>
  users.value.reduce((total: number, user: User): number => total + (user.credits_consumed ?? 0), 0),
)

const deleteMessage: ComputedRef<string> = computed(
  (): string => `Supprimer « ${deletingUser.value?.name ?? ''} » ? Cette action est irréversible.`,
)

/**
 * Initials shown in a user's avatar tile.
 * @param name - Full name of the user.
 * @returns One or two uppercase letters.
 */
function initialsOf(name: string): string {
  const parts: string[] = name.trim().split(/\s+/)
  if (parts.length >= 2) return `${parts[0]?.[0] ?? ''}${parts[1]?.[0] ?? ''}`.toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

/**
 * Whether a user's credit balance is unmetered.
 * @param user - The user to test.
 * @returns True when credits are unlimited.
 */
function hasUnlimitedCredits(user: User): boolean {
  return user.credits_available === -1 || user.credits_available === null
}

/**
 * Open the user drawer on the persistent stack.
 * @param mode - Whether the drawer creates or edits.
 * @param user - The user to edit, or null when creating.
 */
function openUserDrawer(mode: UserFormDrawerMode, user: User | null): void {
  drawerStack.push({ kind: 'user-form', mode, user })
}

/**
 * Load every user (admin only).
 * @returns A promise resolved once the list is refreshed.
 */
async function loadUsers(): Promise<void> {
  isLoading.value = true
  try {
    users.value = await UsersService.getAllUsers()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du chargement des utilisateurs')
  } finally {
    isLoading.value = false
  }
}

/**
 * Ask confirmation before deleting a user.
 * @param user - The user to delete.
 */
function askDelete(user: User): void {
  deletingUser.value = user
  confirmModal.value?.open()
}

/**
 * Delete the pending user once confirmed.
 * @returns A promise resolved once the user is deleted.
 */
async function confirmDelete(): Promise<void> {
  const user: User | null = deletingUser.value
  if (!user) return
  try {
    await UsersService.deleteUser(user.id)
    users.value = users.value.filter((candidate: User): boolean => candidate.id !== user.id)
    toast.success(`« ${user.name} » supprimé`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  } finally {
    deletingUser.value = null
  }
}

watch((): number => drawerStack.usersRefreshCounter, loadUsers)

onMounted((): void => {
  void loadUsers()
})
</script>
