<template>
  <Teleport to="body">
    <!-- Pas de backdrop : drawer non-modal (navigation possible pendant qu'il
         est ouvert), fermeture par X / Échap. -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-users-round" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ organization ? organization.name : 'Organisation' }}
            </h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              {{
                organization
                  ? `${organization.members.length} membre${organization.members.length > 1 ? 's' : ''} · prospects partagés`
                  : 'Travaillez en équipe sur une liste de prospects commune'
              }}
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <!-- Loading -->
          <div v-if="isLoading" class="animate-pulse space-y-3">
            <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
            <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
          </div>

          <!-- No organization yet : create -->
          <template v-else-if="organization === null">
            <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
              Créez votre organisation puis invitez d'autres comptes DevLeadHunter : la liste de prospects devient
              commune, chaque membre garde son propre email d'envoi, et un prospect réservé par un membre est verrouillé
              pour les autres — un prospect, un démarcheur.
            </p>
            <form class="space-y-3" @submit.prevent="handleCreate">
              <div>
                <label class="text-muted mb-1.5 block text-xs font-medium" for="org-name">
                  Nom de l'organisation
                </label>
                <input
                  id="org-name"
                  v-model="createName"
                  type="text"
                  required
                  minlength="2"
                  placeholder="Ex : Dibodev Team"
                  class="input-field"
                />
              </div>
              <button type="submit" class="btn-primary w-full" :disabled="isSubmitting">
                <UIcon v-if="isSubmitting" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
                Créer l'organisation
              </button>
            </form>
          </template>

          <!-- Organization -->
          <template v-else>
            <!-- Members -->
            <div>
              <p class="mb-2 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Membres</p>
              <ul class="divide-y divide-[var(--app-line-soft)]">
                <li v-for="member in organization.members" :key="member.user_id" class="flex items-center gap-3 py-2.5">
                  <span
                    class="font-label flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--app-ink)] text-[0.6rem] font-semibold text-[var(--app-surface)]"
                  >
                    {{ memberInitials(member.name) }}
                  </span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm font-medium text-[var(--app-ink)]">
                      {{ member.name }}
                      <span v-if="member.user_id === currentUserId" class="text-muted text-xs">(vous)</span>
                    </span>
                    <span class="text-muted block truncate text-xs">{{ member.email }}</span>
                  </span>
                  <span :class="['app-badge shrink-0', member.role === 'owner' ? 'app-badge--info' : '']">
                    {{ member.role === 'owner' ? 'Propriétaire' : 'Membre' }}
                  </span>
                  <button
                    v-if="isOwner && member.user_id !== currentUserId"
                    type="button"
                    class="text-muted cursor-pointer transition-colors hover:text-[var(--app-red)]"
                    title="Retirer ce membre"
                    @click="handleRemove(member.user_id, member.name)"
                  >
                    <UIcon name="i-lucide-user-round-x" class="h-4 w-4" />
                  </button>
                </li>
              </ul>
            </div>

            <!-- Invite -->
            <form class="space-y-2 border-t border-[var(--app-line-soft)] pt-4" @submit.prevent="handleInvite">
              <label class="text-muted block text-xs font-medium" for="org-invite-email">Inviter un membre</label>
              <div class="flex gap-2">
                <input
                  id="org-invite-email"
                  v-model="inviteEmail"
                  type="email"
                  required
                  placeholder="email@dumembre.fr"
                  class="input-field flex-1"
                />
                <button type="submit" class="btn-secondary shrink-0" :disabled="isSubmitting">
                  <UIcon
                    :name="isSubmitting ? 'i-lucide-loader-circle' : 'i-lucide-user-round-plus'"
                    :class="['h-4 w-4', isSubmitting && 'animate-spin']"
                  />
                  Inviter
                </button>
              </div>
              <p class="text-[11px] text-[var(--app-faint)]">La personne doit déjà avoir un compte DevLeadHunter.</p>
            </form>

            <!-- Danger zone -->
            <div class="space-y-2 border-t border-[var(--app-line-soft)] pt-4">
              <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                <template v-if="isOwner">
                  Supprimer l'organisation rend les prospects de chaque membre à nouveau personnels.
                </template>
                <template v-else>Quitter l'organisation rend vos prospects à nouveau personnels.</template>
              </p>
              <button type="button" class="btn-danger w-full" :disabled="isSubmitting" @click="handleLeaveOrDelete">
                {{ isOwner ? "Supprimer l'organisation" : "Quitter l'organisation" }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { Organization } from '~/types'
import {
  createOrganization,
  deleteOrganization,
  getMyOrganization,
  inviteMember,
  removeMember,
} from '~/services/organizationsService'
import { useToast } from '~/composables/useToast'
import { useUserStore } from '~/stores/user'

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
}>()

const toast = useToast()
const userStore = useUserStore()

const organization: Ref<Organization | null> = ref<Organization | null>(null)
const isLoading: Ref<boolean> = ref<boolean>(true)
const isSubmitting: Ref<boolean> = ref<boolean>(false)
const createName: Ref<string> = ref<string>('')
const inviteEmail: Ref<string> = ref<string>('')

/** Current user id (0 while the store hydrates). */
const currentUserId: ComputedRef<number> = computed((): number => userStore.user?.id ?? 0)

/** Whether the current user owns the organization. */
const isOwner: ComputedRef<boolean> = computed(
  (): boolean => organization.value !== null && organization.value.owner_user_id === currentUserId.value,
)

/**
 * Initials shown in a member's avatar.
 * @param name - Member display name.
 * @returns Up to two uppercase initials.
 */
function memberInitials(name: string): string {
  const parts: string[] = name.trim().split(/\s+/)
  if (parts.length >= 2 && parts[0] && parts[1]) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

/**
 * Load the current user's organization.
 * @returns A promise resolved once loaded.
 */
async function loadOrganization(): Promise<void> {
  isLoading.value = true
  try {
    organization.value = await getMyOrganization()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors du chargement de l'organisation")
  } finally {
    isLoading.value = false
  }
}

/**
 * Create the organization owned by the current user.
 * @returns A promise resolved once created.
 */
async function handleCreate(): Promise<void> {
  isSubmitting.value = true
  try {
    organization.value = await createOrganization(createName.value.trim())
    toast.success('Organisation créée — vos prospects sont maintenant partageables')
    createName.value = ''
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Création impossible')
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Invite an existing user by account email.
 * @returns A promise resolved once invited.
 */
async function handleInvite(): Promise<void> {
  isSubmitting.value = true
  try {
    organization.value = await inviteMember(inviteEmail.value.trim())
    toast.success(`${inviteEmail.value.trim()} a rejoint l'organisation`)
    inviteEmail.value = ''
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Invitation impossible')
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Remove a member (owner action) after confirmation.
 * @param memberUserId - Member to remove.
 * @param memberName - Display name (confirmation message).
 * @returns A promise resolved once removed.
 */
async function handleRemove(memberUserId: number, memberName: string): Promise<void> {
  if (!confirm(`Retirer ${memberName} de l'organisation ? Ses prospects redeviendront personnels.`)) {
    return
  }
  isSubmitting.value = true
  try {
    await removeMember(memberUserId)
    await loadOrganization()
    toast.success(`${memberName} a été retiré`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Retrait impossible')
  } finally {
    isSubmitting.value = false
  }
}

/**
 * Leave the organization (member) or delete it entirely (owner), after confirmation.
 * @returns A promise resolved once done.
 */
async function handleLeaveOrDelete(): Promise<void> {
  const wasOwner: boolean = isOwner.value
  const message: string = wasOwner
    ? "Supprimer définitivement l'organisation ? Les prospects de chaque membre redeviendront personnels."
    : "Quitter l'organisation ? Vos prospects redeviendront personnels."
  if (!confirm(message)) {
    return
  }
  isSubmitting.value = true
  try {
    if (wasOwner) {
      await deleteOrganization()
    } else {
      await removeMember(currentUserId.value)
    }
    organization.value = null
    toast.success(wasOwner ? 'Organisation supprimée' : "Vous avez quitté l'organisation")
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Action impossible')
  } finally {
    isSubmitting.value = false
  }
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) {
      void loadOrganization()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
