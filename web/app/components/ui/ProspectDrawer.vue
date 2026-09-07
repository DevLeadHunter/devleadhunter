<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="open && prospect"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl"
      >
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="$emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-store" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </div>

          <div class="min-w-0 flex-1">
            <div class="mb-1 flex flex-wrap items-center gap-1.5">
              <span
                class="inline-flex items-center rounded border border-[var(--app-line)] bg-[var(--app-surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--app-ink-soft)]"
              >
                {{ prospect.category }}
              </span>
              <UiProspectSourceBadge :source="prospect.source" />
            </div>

            <h2 class="truncate text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ prospect.name }}
            </h2>

            <div class="mt-1.5 flex items-center gap-1">
              <span
                v-for="i in 4"
                :key="i"
                :class="[
                  'h-1.5 w-1.5 rounded-full',
                  i <= prospect.confidence ? confidenceColor : 'bg-[var(--app-surface-2)]',
                ]"
              />
              <span class="ml-1 text-[10px] text-[var(--app-ink-soft)]">Confiance {{ prospect.confidence }}/4</span>
            </div>
          </div>

          <div class="flex shrink-0 items-center gap-0.5">
            <button
              v-if="!editMode"
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              title="Modifier ce prospect"
              aria-label="Modifier ce prospect"
              @click="startEdit"
            >
              <UIcon name="i-lucide-square-pen" class="h-4 w-4" />
            </button>
            <button
              v-if="!editMode"
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              title="Réglages du prospect"
              aria-label="Réglages du prospect"
              @click="emit('openSettings', prospect)"
            >
              <UIcon name="i-lucide-settings" class="h-4 w-4" />
            </button>
            <button
              v-if="!editMode"
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-red-soft)] hover:text-[var(--app-red)]"
              title="Supprimer ce prospect"
              aria-label="Supprimer ce prospect"
              @click="deleteConfirmModal?.open()"
            >
              <UIcon name="i-lucide-trash-2" class="h-4 w-4" />
            </button>
            <button
              class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              aria-label="Fermer"
              @click="$emit('close')"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <UiDrawerBrowseNav
          v-if="!editMode"
          :position-label="browsePositionLabel"
          :can-previous="canBrowsePrevious"
          :can-next="canBrowseNext"
          @previous="$emit('browsePrevious')"
          @next="$emit('browseNext')"
        />

        <div class="flex-1 overflow-y-auto">
          <template v-if="!editMode">
            <div v-if="prospect.organization_id" class="px-5 pt-4">
              <div
                v-if="isReservedByMe"
                class="flex items-center justify-between gap-3 rounded-lg border border-[var(--app-accent)]/40 bg-[var(--app-accent-soft)] px-3 py-2.5"
              >
                <span class="flex items-center gap-2 text-xs font-medium text-[var(--app-accent-ink)]">
                  <UIcon name="i-lucide-lock-keyhole" class="h-3.5 w-3.5" />
                  Vous avez réservé ce prospect — il est verrouillé pour les autres membres.
                </span>
                <button
                  type="button"
                  class="btn-secondary shrink-0 text-xs"
                  :disabled="isReserving"
                  @click="handleRelease"
                >
                  <UIcon v-if="isReserving" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                  Libérer
                </button>
              </div>
              <div
                v-else-if="isReservedByOther"
                class="flex items-center gap-2 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] px-3 py-2.5 text-xs font-medium text-[var(--app-ink-soft)]"
              >
                <UIcon name="i-lucide-lock" class="h-3.5 w-3.5" />
                Réservé par {{ prospect.reserved_by_name || 'un membre de votre organisation' }}.
              </div>
              <div
                v-else
                class="flex items-center justify-between gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5"
              >
                <span class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-lock-open" class="h-3.5 w-3.5" />
                  Prospect partagé avec votre organisation — libre.
                </span>
                <button
                  type="button"
                  class="btn-secondary shrink-0 text-xs"
                  :disabled="isReserving"
                  @click="handleReserve"
                >
                  <UIcon v-if="isReserving" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                  Réserver
                </button>
              </div>
            </div>

            <div v-if="prospect.do_not_contact" class="px-5 pt-4">
              <UiProspectDoNotContactBanner
                :reason="prospect.do_not_contact_reason ?? null"
                :is-toggling="isTogglingContact"
                @resume="handleResumeContact"
              />
            </div>

            <div v-if="prospect.email_undeliverable" class="px-5 pt-4">
              <UiProspectEmailUndeliverableBanner
                :reason="prospect.email_undeliverable_reason ?? null"
                :phone="prospect.phone ?? null"
              />
            </div>

            <div class="space-y-3 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Contact</p>

              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                  <UIcon name="i-lucide-phone" class="h-4 w-4 text-[var(--app-ink-soft)]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Téléphone</p>
                  <p
                    v-if="prospect.phone"
                    class="text-sm font-medium whitespace-nowrap text-[var(--app-ink)] tabular-nums"
                  >
                    {{ prospect.phone }}
                  </p>
                  <p v-else class="text-sm text-[var(--app-faint)]">—</p>
                  <span
                    v-if="prospect.sms_opted_out"
                    class="app-badge app-badge--danger mt-1"
                    title="A répondu STOP — plus aucun SMS ne peut lui être envoyé"
                  >
                    <UIcon name="i-lucide-message-square-off" class="h-3 w-3" />
                    STOP SMS
                  </span>
                </div>
                <a
                  v-if="prospect.phone"
                  :href="`tel:${prospect.phone}`"
                  class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-accent-ink)]"
                  title="Appeler"
                >
                  <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                </a>
              </div>

              <div class="flex items-start gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                  <UIcon name="i-lucide-mail" class="h-4 w-4 text-[var(--app-ink-soft)]" />
                </div>
                <div class="min-w-0 flex-1">
                  <UiProspectEmails
                    :prospect="prospect"
                    :editable="canEditEmails"
                    @updated="$emit('updated', $event)"
                  />
                  <span
                    v-if="prospect.email_unsubscribed"
                    class="app-badge app-badge--danger mt-1"
                    title="S'est désinscrit de la liste d'emails — exclu des campagnes"
                  >
                    <UIcon name="i-lucide-mail-x" class="h-3 w-3" />
                    Désinscrit email
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                  <UIcon
                    :name="prospect.contacted ? 'i-lucide-mail-check' : 'i-lucide-mail-question'"
                    :class="['h-4 w-4', prospect.contacted ? 'text-[var(--app-green)]' : 'text-[var(--app-ink-soft)]']"
                  />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Contacté</p>
                  <p class="text-sm font-medium text-[var(--app-ink)]">
                    {{ prospect.contacted ? 'Oui' : 'Pas encore' }}
                  </p>
                </div>
                <UiSwitch
                  id="prospect-contacted"
                  :model-value="prospect.contacted"
                  @update:model-value="$emit('toggleContacted', prospect)"
                />
              </div>

              <div class="flex items-center gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                  <UIcon name="i-lucide-globe" class="h-4 w-4 text-[var(--app-ink-soft)]" />
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Site web</p>
                  <p v-if="prospect.website" class="truncate text-sm text-[var(--app-accent-ink)]">
                    {{ prospect.website }}
                  </p>
                  <p v-else class="text-sm text-[var(--app-faint)]">—</p>
                  <span
                    v-if="prospect.website_status === 'dead'"
                    class="app-badge app-badge--danger mt-1"
                    title="DNS mort, erreur 404/5xx ou page « site introuvable » — vérifiez en ouvrant le lien"
                  >
                    <UIcon name="i-lucide-unplug" class="h-3 w-3" />
                    Ne répond plus
                  </span>
                  <span
                    v-else-if="prospect.website_status === 'placeholder'"
                    class="app-badge app-badge--info mt-1"
                    title="Mini-site annuaire (business.site, Solocal…) — pas un vrai site"
                  >
                    <UIcon name="i-lucide-layout-template" class="h-3 w-3" />
                    Mini-site annuaire
                  </span>
                </div>
                <a
                  v-if="prospect.website"
                  :href="prospect.website"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-accent-ink)]"
                  title="Ouvrir le site"
                >
                  <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                </a>
                <button
                  v-if="prospect.website"
                  type="button"
                  :disabled="isSaving"
                  class="flex h-7 w-7 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-red)] disabled:opacity-50"
                  title="Ce n'est pas son site (ex. site de la franchise) — le retirer"
                  @click="removeWebsite"
                >
                  <UIcon name="i-lucide-unlink" class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div class="border-t border-[var(--app-surface-2)]"></div>

            <div class="space-y-3 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Localisation</p>
              <div class="flex items-start gap-3">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--app-surface-2)]">
                  <UIcon name="i-lucide-map-pin" class="h-4 w-4 text-[var(--app-ink-soft)]" />
                </div>
                <div>
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Adresse</p>
                  <div v-if="prospect.address || prospect.city" class="mt-0.5">
                    <p v-if="prospect.address" class="text-sm text-[var(--app-ink)]">{{ prospect.address }}</p>
                    <p v-if="prospect.city" class="text-sm text-[var(--app-ink-soft)]">{{ prospect.city }}</p>
                  </div>
                  <p v-else class="text-sm text-[var(--app-faint)]">—</p>
                </div>
              </div>
            </div>

            <div class="border-t border-[var(--app-surface-2)]"></div>

            <div class="px-5 py-4">
              <p class="mb-3 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                Informations
              </p>
              <div class="grid grid-cols-2 gap-x-4 gap-y-3">
                <div>
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Catégorie</p>
                  <p class="mt-0.5 text-sm text-[var(--app-ink)]">{{ prospect.category }}</p>
                </div>
                <div>
                  <p class="mb-1 text-[10px] text-[var(--app-ink-soft)]">Source</p>
                  <UiProspectSourceBadge :source="prospect.source" />
                </div>
                <div v-if="prospect.created_at">
                  <p class="text-[10px] text-[var(--app-ink-soft)]">Ajouté le</p>
                  <p class="mt-0.5 text-sm text-[var(--app-ink)]">{{ formatLongMonthDate(prospect.created_at) }}</p>
                </div>
                <div>
                  <p class="text-[10px] text-[var(--app-ink-soft)]">ID</p>
                  <p class="mt-0.5 font-mono text-sm text-[var(--app-ink-soft)]">#{{ prospect.id }}</p>
                </div>
              </div>
            </div>

            <div class="border-t border-[var(--app-surface-2)]"></div>

            <div v-if="prospect.website" class="space-y-3 px-5 py-4">
              <div class="flex items-center justify-between gap-3">
                <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Audit du site existant
                </p>
                <button type="button" class="btn-secondary text-xs" :disabled="isAuditing" @click="handleLighthouse">
                  <UIcon
                    :name="isAuditing ? 'i-lucide-loader-circle' : 'i-lucide-gauge'"
                    :class="['h-3.5 w-3.5', isAuditing && 'animate-spin']"
                  />
                  {{ isAuditing ? 'Analyse…' : prospect.lighthouse_json ? 'Relancer' : 'Analyser' }}
                </button>
              </div>

              <p v-if="isAuditing" class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Lighthouse analyse le site (30 à 60 secondes)…
              </p>

              <template v-else-if="prospect.lighthouse_json">
                <div class="grid grid-cols-4 gap-2">
                  <div
                    v-for="gauge in lighthouseGauges"
                    :key="gauge.label"
                    class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-2 py-2.5 text-center"
                  >
                    <p class="text-lg font-bold tabular-nums" :style="{ color: gauge.color }">
                      {{ gauge.score ?? '—' }}
                    </p>
                    <p class="mt-0.5 text-[9px] leading-tight text-[var(--app-ink-soft)] uppercase">
                      {{ gauge.label }}
                    </p>
                  </div>
                </div>
                <div
                  :class="[
                    'flex items-start gap-2 rounded-lg px-3 py-2.5 text-xs leading-relaxed',
                    prospect.lighthouse_json.is_improvable
                      ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                      : 'bg-[var(--app-green-soft)] text-[var(--app-green)]',
                  ]"
                >
                  <UIcon
                    :name="prospect.lighthouse_json.is_improvable ? 'i-lucide-flame' : 'i-lucide-circle-check'"
                    class="mt-0.5 h-3.5 w-3.5 shrink-0"
                  />
                  <span>
                    {{
                      prospect.lighthouse_json.is_improvable
                        ? 'Site améliorable — bon candidat pour proposer une refonte.'
                        : 'Site plutôt sain — la refonte sera plus difficile à vendre.'
                    }}
                  </span>
                </div>
                <p v-if="prospect.lighthouse_at" class="text-[10px] text-[var(--app-faint)]">
                  Audité le {{ formatLongMonthDate(prospect.lighthouse_at) }} · mobile
                </p>
              </template>

              <p v-else class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Ce prospect a déjà un site — analysez sa qualité (performance, SEO…) pour savoir si une refonte se vend.
              </p>
            </div>

            <div v-if="prospect.website" class="border-t border-[var(--app-surface-2)]"></div>

            <div data-swipe-ignore>
              <UiProspectEnrichment
                :prospect-id="prospect.id"
                :prospect-name="prospect.name"
                :prospect-city="prospect.city ?? ''"
                :prospect-google-maps-url="prospect.google_maps_url ?? ''"
                :prospect-facebook-url="prospect.facebook_url ?? ''"
                :open="open"
              />
            </div>

            <div class="border-t border-[var(--app-surface-2)]"></div>

            <div v-if="!isLoadingDemoSite && !demoSite" class="space-y-2 px-5 py-4">
              <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
                Comportement démo
              </p>
              <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Aucun site démo pour ce prospect — générez-en un pour suivre ses visites et préparer une relance.
              </p>
            </div>
            <UiProspectBehavior
              v-else
              :prospect-id="prospect.id"
              :prospect-email="prospect.email ?? null"
              :prospect-name="prospect.name"
              :open="open"
            />
          </template>

          <form v-else id="prospect-edit-form" class="space-y-4 p-5" @submit.prevent="handleSave">
            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Nom *
              </label>
              <input v-model="editForm.name" type="text" required class="input-field" placeholder="Nom du prospect" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Téléphone
                </label>
                <input v-model="editForm.phone" type="tel" class="input-field" placeholder="06 12 34 56 78" />
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Email
                </label>
                <input v-model="editForm.email" type="email" class="input-field" placeholder="contact@..." />
              </div>
            </div>

            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Site web
              </label>
              <input v-model="editForm.website" type="url" class="input-field" placeholder="https://..." />
            </div>

            <div>
              <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                Adresse
              </label>
              <UiAddressAutocompleteInput
                v-model="editForm.address"
                placeholder="12 Rue de la Paix"
                @select="handleAddressSelect"
              />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Ville
                </label>
                <UiCityAutocompleteInput v-model="editForm.city" placeholder="Paris" />
              </div>
              <div>
                <label class="mb-1 block text-[10px] font-medium tracking-wider text-[var(--app-ink-soft)] uppercase">
                  Catégorie
                </label>
                <input v-model="editForm.category" type="text" class="input-field" placeholder="plombier" />
              </div>
            </div>
          </form>
        </div>

        <div class="border-t border-[var(--app-line)] px-5 py-4">
          <div v-if="!editMode" class="space-y-2">
            <div class="flex gap-2">
              <button
                v-if="prospect.email"
                class="btn-secondary min-w-0 flex-1 px-3 whitespace-nowrap"
                @click="$emit('sendEmail', prospect)"
              >
                <UIcon name="i-lucide-mail" class="h-4 w-4 shrink-0" />Email
              </button>
              <button
                v-if="prospect.phone"
                class="btn-secondary min-w-0 flex-1 px-3 whitespace-nowrap"
                title="Envoyer un SMS à ce prospect"
                @click="$emit('sendSms', prospect)"
              >
                <UIcon name="i-lucide-message-square-text" class="h-4 w-4 shrink-0" />SMS
              </button>
              <button
                class="btn-secondary min-w-0 flex-1 px-3 whitespace-nowrap"
                title="Marquer ce prospect comme vendu"
                @click="$emit('markAsSold', prospect)"
              >
                <UIcon name="i-lucide-shopping-cart" class="h-4 w-4 shrink-0" />
                <span class="truncate">Vendu</span>
              </button>
            </div>
            <a
              v-if="demoSite?.demo_url"
              :href="DemoSiteService.withInternalFlag(demoSite.demo_url) ?? undefined"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-primary w-full"
            >
              <UIcon name="i-lucide-external-link" class="mr-1.5 h-4 w-4" />Ouvrir la démo
            </a>
            <button v-else class="btn-primary w-full" :disabled="isLoadingDemoSite" @click="generateDemoSite">
              <UIcon name="i-lucide-wand-sparkles" class="mr-1.5 h-4 w-4" />Générer un site démo
            </button>
          </div>

          <div v-else class="flex gap-2">
            <button type="button" class="btn-secondary flex-1" :disabled="isSaving" @click="cancelEdit">Annuler</button>
            <button type="submit" form="prospect-edit-form" class="btn-primary flex-1" :disabled="isSaving">
              <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
              Enregistrer
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <UiConfirmModal
      ref="deleteConfirmModal"
      title="Supprimer le prospect"
      :message="deleteMessage"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDelete"
    />
  </Teleport>
</template>

<script lang="ts" setup>
import { formatLongMonthDate } from '~/utils/date'
import type { UseToastReturn } from '~/types/Composables'
import type {
  LighthouseGauge,
  ProspectEditForm,
  UiProspectDrawerEmits,
  UiProspectDrawerProps,
} from '~/types/UiProspectDrawer'
import type { AddressSuggestion } from '~/types/AddressAutocompleteInput'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { ref, computed, watch } from 'vue'
import type { Prospect, ProspectUpdatePayload } from '~/types'
import type { DemoSite, DemoSiteListResponse } from '~/services/demoSiteService'
import { DemoSiteService } from '~/services/demoSiteService'
import { ProspectsService } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'
import { useUserStore } from '~/stores/user'

/** Prospect detail drawer with edit, lighthouse audit and quick actions. */
const props: UiProspectDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospect: {
    type: Object as PropType<Prospect | null>,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
  startInEdit: {
    type: Boolean,
    default: false,
  },
  browsePositionLabel: {
    type: String,
    default: '',
  },
  canBrowsePrevious: {
    type: Boolean,
    default: false,
  },
  canBrowseNext: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProspectDrawerEmits> = defineEmits<UiProspectDrawerEmits>()

const toast: UseToastReturn = useToast()
const userStore: ReturnType<typeof useUserStore> = useUserStore()

const editMode: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const isReserving: Ref<boolean> = ref(false)
const isAuditing: Ref<boolean> = ref(false)
const isLoadingDemoSite: Ref<boolean> = ref(false)
const demoSite: Ref<DemoSite | null> = ref(null)
const deleteConfirmModal: Ref<{ open: () => void } | null> = ref(null)
const isTogglingContact: Ref<boolean> = ref(false)

// Exposed to the drawer host so it can suspend the swipe-to-next gesture while an edit is in progress.
defineExpose({ editMode })

const deleteMessage: ComputedRef<string> = computed(
  (): string => `Supprimer « ${props.prospect?.name ?? ''} » ? Cette action est irréversible.`,
)

/** Current user id (0 while the store hydrates). */
const currentUserId: ComputedRef<number> = computed((): number => userStore.user?.id ?? 0)

/** Whether the current user holds the reservation. */
const isReservedByMe: ComputedRef<boolean> = computed(
  (): boolean =>
    props.prospect?.reserved_by_user_id != null && props.prospect.reserved_by_user_id === currentUserId.value,
)

/** Whether another organization member holds the reservation. */
const isReservedByOther: ComputedRef<boolean> = computed(
  (): boolean =>
    props.prospect?.reserved_by_user_id != null && props.prospect.reserved_by_user_id !== currentUserId.value,
)

/** Emails stay editable unless another member currently holds the prospect. */
const canEditEmails: ComputedRef<boolean> = computed((): boolean => !isReservedByOther.value)

/** The four Lighthouse category gauges (red < 50, amber < 90, green otherwise). */
const lighthouseGauges: ComputedRef<LighthouseGauge[]> = computed((): LighthouseGauge[] => {
  const scores:
    | { performance: number | null; accessibility: number | null; bestPractices: number | null; seo: number | null }
    | undefined = props.prospect?.lighthouse_json?.scores
  const colorOf: (score: number | null) => string = (score: number | null): string => {
    if (score === null) return 'var(--app-faint)'
    if (score < 50) return 'var(--app-red)'
    if (score < 90) return 'var(--app-accent)'
    return 'var(--app-green)'
  }
  const entries: Array<[string, number | null]> = [
    ['Perf.', scores?.performance ?? null],
    ['Accessib.', scores?.accessibility ?? null],
    ['Pratiques', scores?.bestPractices ?? null],
    ['SEO', scores?.seo ?? null],
  ]
  return entries.map(([label, score]: [string, number | null]): LighthouseGauge => {
    return { label, score, color: colorOf(score) }
  })
})

/**
 * Find the demo site already generated for this prospect, if any.
 * @returns A promise resolved once the lookup completes.
 */
async function loadDemoSite(): Promise<void> {
  if (!props.prospect) return
  isLoadingDemoSite.value = true
  demoSite.value = null
  try {
    const response: DemoSiteListResponse = await DemoSiteService.listDemoSites()
    demoSite.value = response.items.find((site: DemoSite): boolean => site.prospect_id === props.prospect?.id) ?? null
  } catch {
    // Non-critical — the footer falls back to the generation call to action.
  } finally {
    isLoadingDemoSite.value = false
  }
}

/** Open the creation tunnel in site mode, prefilled with this prospect. */
function generateDemoSite(): void {
  if (!props.prospect) return
  void navigateTo({ path: '/dashboard/demo-sites/create', query: { prospect: String(props.prospect.id) } })
}

/**
 * Delete the prospect once confirmed, then let the host close the stack.
 * @returns A promise resolved once deleted.
 */
async function handleDelete(): Promise<void> {
  if (!props.prospect) return
  const { id, name }: Prospect = props.prospect
  try {
    await ProspectsService.deleteProspect(id)
    toast.success(`« ${name} » supprimé`)
    emit('deleted', id)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la suppression')
  }
}

/**
 * Reserve the prospect for the current user (locks it for other members).
 * @returns A promise resolved once reserved.
 */
async function handleReserve(): Promise<void> {
  if (!props.prospect) return
  isReserving.value = true
  try {
    const updated: Prospect = await ProspectsService.reserveProspect(props.prospect.id)
    emit('updated', updated)
    toast.success('Prospect réservé — verrouillé pour les autres membres')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Réservation impossible')
  } finally {
    isReserving.value = false
  }
}

/**
 * Release the reservation so another member can take the prospect.
 * @returns A promise resolved once released.
 */
async function handleRelease(): Promise<void> {
  if (!props.prospect) return
  isReserving.value = true
  try {
    const updated: Prospect = await ProspectsService.releaseProspect(props.prospect.id)
    emit('updated', updated)
    toast.success('Prospect libéré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Libération impossible')
  } finally {
    isReserving.value = false
  }
}

/**
 * Run the Lighthouse audit on the prospect's existing website (slow, 30-60s).
 * @returns A promise resolved once the audit is stored.
 */
async function handleLighthouse(): Promise<void> {
  if (!props.prospect) return
  isAuditing.value = true
  try {
    const updated: Prospect = await ProspectsService.runLighthouseAudit(props.prospect.id)
    emit('updated', updated)
    toast.success('Audit Lighthouse terminé')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "L'audit a échoué")
  } finally {
    isAuditing.value = false
  }
}

/**
 * Lift the « ne plus contacter » flag so the prospect can be contacted again.
 * @returns A promise resolved once the flag is cleared.
 */
async function handleResumeContact(): Promise<void> {
  if (!props.prospect || isTogglingContact.value) return
  isTogglingContact.value = true
  try {
    const updated: Prospect = await ProspectsService.setDoNotContact(props.prospect.id, false, null)
    emit('updated', updated)
    toast.success('Contact ré-autorisé pour ce prospect')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Action impossible')
  } finally {
    isTogglingContact.value = false
  }
}

const editForm: Ref<ProspectEditForm> = ref({
  name: '',
  phone: '',
  email: '',
  website: '',
  address: '',
  city: '',
  category: '',
})

watch(
  () => [props.open, props.prospect?.id],
  ([open]: (boolean | number | undefined)[]) => {
    if (!open) {
      // Give the closing animation time to complete before resetting
      setTimeout(() => {
        editMode.value = false
      }, 250)
      return
    }
    if (props.startInEdit) startEdit()
    void loadDemoSite()
  },
  { immediate: true },
)

/** Confidence indicator dot colour */
const confidenceColor: ComputedRef<string> = computed((): string => {
  switch (props.prospect?.confidence) {
    case 1:
      return 'bg-[var(--app-red)]'
    case 2:
      return 'bg-[var(--app-accent)]'
    case 3:
      return 'bg-[var(--app-accent-ink)]'
    case 4:
      return 'bg-[var(--app-green)]'
    default:
      return 'bg-[var(--app-ink-soft)]'
  }
})

/**
 * Populate the edit form with the current prospect values and enter edit mode.
 */
function startEdit(): void {
  if (!props.prospect) return
  editForm.value = {
    name: props.prospect.name,
    phone: props.prospect.phone ?? '',
    email: props.prospect.email ?? '',
    website: props.prospect.website ?? '',
    address: props.prospect.address ?? '',
    city: props.prospect.city ?? '',
    category: props.prospect.category,
  }
  editMode.value = true
}

/** Exit edit mode without saving. */
function cancelEdit(): void {
  editMode.value = false
}

/**
 * Prefill the city when the user picks a BAN address suggestion.
 * @param suggestion - Selected street address.
 */
function handleAddressSelect(suggestion: AddressSuggestion): void {
  editForm.value.city = suggestion.city
}

/**
 * Persist the edited fields via the REST API.
 * Emits `updated` on success so the parent can refresh its list.
 */
async function handleSave(): Promise<void> {
  if (!props.prospect) return
  isSaving.value = true
  try {
    const payload: ProspectUpdatePayload = {
      name: editForm.value.name || undefined,
      phone: editForm.value.phone || null,
      email: editForm.value.email || null,
      website: editForm.value.website || null,
      address: editForm.value.address || null,
      city: editForm.value.city || null,
      category: editForm.value.category || undefined,
    }
    const updated: Prospect = await ProspectsService.updateProspect(props.prospect.id, payload)
    emit('updated', updated)
    editMode.value = false
    toast.success('Prospect mis à jour')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  } finally {
    isSaving.value = false
  }
}

/**
 * Retire le site du prospect quand ce n'est pas le sien (ex. le site de la franchise) : le prospect
 * redevient « sans site » donc ciblable. Réversible via le formulaire d'édition.
 */
async function removeWebsite(): Promise<void> {
  if (!props.prospect?.website) return
  isSaving.value = true
  try {
    const updated: Prospect = await ProspectsService.updateProspect(props.prospect.id, { website: null })
    emit('updated', updated)
    toast.success('Site retiré — le prospect redevient « sans site »')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du retrait du site')
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
/* Panel slide from right */
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
