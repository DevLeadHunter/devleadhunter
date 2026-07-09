<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <template v-else-if="campaign">
      <!-- ─── Header ──────────────────────────────────────────────────────── -->
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex min-w-0 items-center gap-3">
          <button
            class="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
            @click="router.push('/dashboard/campaigns')"
          >
            <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
          </button>
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="truncate text-xl font-semibold text-[var(--app-ink)]">{{ campaign.name }}</h1>
              <span
                :class="[
                  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                  STATUS_STYLE[campaign.status] ?? 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
                ]"
              >
                <span
                  :class="['h-1.5 w-1.5 rounded-full', STATUS_DOT[campaign.status] ?? 'bg-[var(--app-ink-soft)]']"
                />
                {{ STATUS_LABELS[campaign.status] ?? campaign.status }}
              </span>
              <span
                v-if="campaign.ab_template_id_b"
                class="inline-flex items-center gap-1 rounded-full bg-[#8d7bb8]/15 px-2 py-0.5 text-[10px] font-semibold text-[#8d7bb8]"
              >
                <UIcon name="i-lucide-flask-conical" class="h-3 w-3" /> A/B
              </span>
            </div>
            <p v-if="campaign.description" class="text-muted mt-0.5 max-w-xl truncate text-sm">
              {{ campaign.description }}
            </p>
          </div>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <button v-if="campaign.status === 'active'" class="btn-secondary" @click="handlePause">
            <UIcon name="i-lucide-pause" class="mr-1.5 h-4 w-4" />Pause
          </button>
          <button v-if="campaign.status === 'paused'" class="btn-secondary" @click="handleResume">
            <UIcon name="i-lucide-play" class="mr-1.5 h-4 w-4" />Reprendre
          </button>
          <button
            v-if="campaign.status === 'draft' || campaign.status === 'paused'"
            :disabled="!canLaunch"
            class="btn-primary disabled:cursor-not-allowed disabled:opacity-40"
            :title="canLaunch ? '' : 'Sélectionnez un template J1 dans la configuration'"
            @click="handleLaunch"
          >
            <UIcon name="i-lucide-rocket" class="mr-1.5 h-4 w-4" />
            {{ campaign.status === 'paused' ? 'Relancer' : 'Lancer' }}
          </button>
          <button
            class="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
            title="Modifier"
            @click="openEditModal"
          >
            <UIcon name="i-lucide-pencil" class="h-4 w-4" />
          </button>
          <button
            class="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--app-red)]/40 text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/10"
            title="Supprimer"
            @click="confirmDeleteModal?.open()"
          >
            <UIcon name="i-lucide-trash-2" class="h-4 w-4" />
          </button>
        </div>
      </div>

      <!-- ─── Stats strip ─────────────────────────────────────────────────── -->
      <div v-if="stats" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div
          v-for="m in metricCards"
          :key="m.label"
          class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-3.5"
        >
          <div class="flex items-center gap-2">
            <UIcon :name="m.icon" :class="['h-3.5 w-3.5', m.color]" />
            <p class="text-muted text-xs">{{ m.label }}</p>
          </div>
          <p :class="['mt-1.5 text-2xl font-bold', m.color]">{{ m.value }}</p>
        </div>
      </div>

      <!-- ─── Tabs ────────────────────────────────────────────────────────── -->
      <div class="border-b border-[var(--app-line)]">
        <nav class="flex gap-1">
          <button
            v-for="tab in TABS"
            :key="tab.key"
            :class="[
              '-mb-px flex items-center gap-2 border-b-2 px-3 pt-1 pb-2.5 text-sm font-medium transition-colors',
              activeTab === tab.key
                ? 'border-[var(--app-ink)] text-[var(--app-ink)]'
                : 'border-transparent text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
            ]"
            @click="activeTab = tab.key"
          >
            <UIcon :name="tab.icon" class="h-4 w-4" />
            {{ tab.label }}
            <span
              v-if="tab.key === 'queue' && queueData?.pending_count"
              class="rounded-full bg-[#1f3a5c] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-accent-ink)]"
            >
              {{ queueData.pending_count }}
            </span>
          </button>
        </nav>
      </div>

      <!-- ═══ Tab: Configuration ══════════════════════════════════════════ -->
      <div v-if="activeTab === 'config'" class="space-y-4">
        <!-- Cadence -->
        <section class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
          <div class="mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-timer" class="h-4 w-4 text-[var(--app-accent-ink)]" />
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Cadence d'envoi</h3>
          </div>
          <div class="flex items-center gap-2 text-sm text-[var(--app-ink)]">
            <span>1 email toutes les</span>
            <input
              v-model.number="settingsForm.send_delay_minutes"
              type="number"
              min="1"
              max="1440"
              class="input-field h-9 w-20 text-center"
            />
            <span>minutes</span>
          </div>
          <p class="text-muted mt-2 text-xs">
            Rate limiting strict pour préserver ta délivrabilité. 20 min = ~72 emails/jour.
          </p>
        </section>

        <!-- Templates -->
        <section class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
          <div class="mb-4 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-mail" class="h-4 w-4 text-[var(--app-green)]" />
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Email initial (J1)</h3>
            </div>
            <button
              type="button"
              class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
              @click="settingsForm.enable_ab = !settingsForm.enable_ab"
            >
              <UIcon name="i-lucide-flask-conical" class="h-3.5 w-3.5" />
              <span>A/B test</span>
              <span
                :class="[
                  'relative inline-block h-5 w-9 rounded-full transition-colors',
                  settingsForm.enable_ab ? 'bg-[#8d7bb8]' : 'bg-[var(--app-surface-2)]',
                ]"
              >
                <span
                  :class="[
                    'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all',
                    settingsForm.enable_ab ? 'left-4' : 'left-0.5',
                  ]"
                />
              </span>
            </button>
          </div>

          <div :class="settingsForm.enable_ab ? 'grid gap-4 md:grid-cols-2' : ''">
            <div>
              <label
                v-if="settingsForm.enable_ab"
                class="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[var(--app-accent-ink)]"
              >
                <span class="rounded bg-[#1f3a5c] px-1.5 py-0.5 font-bold">A</span> Variante A
              </label>
              <UiTemplateSelect v-model="settingsForm.template_id" :templates="templates" />
            </div>
            <div v-if="settingsForm.enable_ab">
              <label class="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[#8d7bb8]">
                <span class="rounded bg-[#8d7bb8]/15 px-1.5 py-0.5 font-bold">B</span> Variante B
              </label>
              <UiTemplateSelect v-model="settingsForm.ab_template_id_b" :templates="templates" />
            </div>
          </div>

          <div
            v-if="settingsForm.enable_ab"
            class="mt-3 flex items-start gap-2 rounded-lg border border-[#8d7bb8]/20 bg-[#8d7bb8]/5 px-3 py-2"
          >
            <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#8d7bb8]" />
            <p class="text-xs text-[#8d7bb8]">
              Distribution 50/50 automatique — chaque variante part à la moitié des prospects.
            </p>
          </div>
        </section>

        <!-- Follow-ups -->
        <section class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
          <div class="mb-4 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-reply" class="h-4 w-4 text-[var(--app-accent)]" />
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Séquence de relances</h3>
            </div>
            <button
              class="flex items-center gap-1.5 rounded-lg border border-[var(--app-line)] px-2.5 py-1 text-xs text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface)]"
              @click="addFollowUp"
            >
              <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />Ajouter
            </button>
          </div>

          <div
            v-if="settingsForm.follow_ups.length === 0"
            class="rounded-lg border border-dashed border-[var(--app-line)] py-8 text-center"
          >
            <UIcon name="i-lucide-reply-all" class="mx-auto mb-2 h-7 w-7 text-[var(--app-faint)]" />
            <p class="text-muted text-sm">Aucune relance configurée</p>
            <p class="text-muted mt-0.5 text-xs">Les prospects qui ne répondent pas ne recevront pas de suivi.</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="(fu, idx) in settingsForm.follow_ups"
              :key="idx"
              class="relative flex gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
            >
              <div
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#3a2a0a] text-xs font-bold text-[var(--app-accent)]"
              >
                {{ idx + 1 }}
              </div>
              <div class="flex-1 space-y-2.5">
                <div class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <UIcon name="i-lucide-clock" class="h-3.5 w-3.5" />
                  <span>J+</span>
                  <input
                    v-model.number="fu.delay_days"
                    type="number"
                    min="1"
                    max="365"
                    class="input-field h-7 w-14 px-2 text-center text-xs"
                  />
                  <span>après l'envoi précédent</span>
                </div>
                <UiTemplateSelect v-model="fu.template_id" :templates="templates" />
              </div>
              <button
                class="absolute top-2 right-2 text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-red)]"
                @click="removeFollowUp(idx)"
              >
                <UIcon name="i-lucide-x" class="h-4 w-4" />
              </button>
            </div>
          </div>

          <!-- Behaviour-personalised follow-ups (additive) -->
          <label
            class="mt-4 flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
          >
            <input
              v-model="settingsForm.behavior_personalized_followups"
              type="checkbox"
              class="mt-0.5 h-4 w-4 rounded border-[var(--app-line)]"
            />
            <span class="text-xs">
              <span class="font-medium text-[var(--app-ink)]">Relance personnalisée selon le comportement</span>
              <span class="text-muted mt-0.5 block">
                Personnalise le corps des relances à partir du comportement du prospect sur la démo (clics, visites…).
                Conserve le template comme base si aucune donnée n'est disponible.
              </span>
            </span>
          </label>
        </section>

        <div class="flex items-center justify-end gap-3">
          <span v-if="settingsDirty" class="text-muted text-xs">Modifications non enregistrées</span>
          <button :disabled="isSavingSettings" class="btn-primary disabled:opacity-50" @click="saveSettings">
            <UIcon v-if="isSavingSettings" name="i-lucide-loader-circle" class="mr-2 h-4 w-4 animate-spin" />
            <UIcon v-else name="i-lucide-check" class="mr-2 h-4 w-4" />
            Enregistrer
          </button>
        </div>
      </div>

      <!-- ═══ Tab: A/B ════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'ab'" class="space-y-4">
        <div
          v-if="!campaign.ab_template_id_b"
          class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] py-14 text-center"
        >
          <UIcon name="i-lucide-flask-conical" class="mx-auto mb-3 h-10 w-10 text-[var(--app-faint)]" />
          <p class="font-medium text-[var(--app-ink)]">A/B test non activé</p>
          <p class="text-muted mx-auto mt-1 max-w-sm text-sm">
            Active l'A/B test dans la configuration pour comparer deux variantes en temps réel.
          </p>
          <button class="btn-secondary mt-4" @click="activeTab = 'config'">
            <UIcon name="i-lucide-settings-2" class="mr-1.5 h-4 w-4" />Configurer
          </button>
        </div>

        <template v-else-if="stats?.ab_stats">
          <div class="grid gap-4 md:grid-cols-2">
            <div
              v-for="v in stats.ab_stats"
              :key="v.variant"
              :class="[
                'rounded-xl border-2 bg-[var(--app-surface)] p-5',
                v.variant === 'A' ? 'border-[var(--app-accent-ink)]/30' : 'border-[#8d7bb8]/30',
              ]"
            >
              <div class="mb-4 flex items-center justify-between">
                <span
                  :class="[
                    'flex items-center gap-2 text-base font-bold',
                    v.variant === 'A' ? 'text-[var(--app-accent-ink)]' : 'text-[#8d7bb8]',
                  ]"
                >
                  <span
                    :class="[
                      'flex h-6 w-6 items-center justify-center rounded-lg text-sm',
                      v.variant === 'A' ? 'bg-[#1f3a5c]' : 'bg-[#8d7bb8]/15',
                    ]"
                    >{{ v.variant }}</span
                  >
                  Variante {{ v.variant }}
                </span>
                <span
                  v-if="isWinner(v)"
                  class="inline-flex items-center gap-1 rounded-full bg-[#1a3a2a] px-2 py-0.5 text-xs font-semibold text-[var(--app-green)]"
                >
                  <UIcon name="i-lucide-trophy" class="h-3 w-3" /> Gagnant
                </span>
              </div>
              <div class="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p class="text-xl font-bold text-[var(--app-ink)]">{{ v.sent }}</p>
                  <p class="text-muted text-xs">Envoyés</p>
                </div>
                <div>
                  <p class="text-xl font-bold text-[var(--app-ink)]">{{ v.open_rate }}%</p>
                  <p class="text-muted text-xs">Ouverture</p>
                </div>
                <div>
                  <p class="text-xl font-bold text-[var(--app-ink)]">{{ v.click_rate }}%</p>
                  <p class="text-muted text-xs">Clic</p>
                </div>
              </div>
              <div class="mt-4">
                <div class="mb-1 flex justify-between text-xs text-[var(--app-ink-soft)]">
                  <span>Taux d'ouverture</span>
                  <span>{{ v.opened }}/{{ v.sent }}</span>
                </div>
                <div class="h-2 w-full rounded-full bg-[var(--app-surface-2)]">
                  <div
                    :class="[
                      'h-2 rounded-full transition-all',
                      v.variant === 'A' ? 'bg-[var(--app-accent-ink)]' : 'bg-[#8d7bb8]',
                    ]"
                    :style="`width: ${Math.min(v.open_rate, 100)}%`"
                  />
                </div>
              </div>
            </div>
          </div>

          <div
            :class="[
              'flex items-start gap-2 rounded-lg border px-3 py-2.5',
              hasSignificantDiff
                ? 'border-[var(--app-green)]/20 bg-[var(--app-green)]/5'
                : 'border-[var(--app-line)] bg-[var(--app-surface)]',
            ]"
          >
            <UIcon
              :name="hasSignificantDiff ? 'i-lucide-circle-check' : 'i-lucide-info'"
              :class="[
                'mt-0.5 h-4 w-4 shrink-0',
                hasSignificantDiff ? 'text-[var(--app-green)]' : 'text-[var(--app-ink-soft)]',
              ]"
            />
            <p :class="['text-sm', hasSignificantDiff ? 'text-[var(--app-green)]' : 'text-muted']">
              {{
                hasSignificantDiff
                  ? winnerMessage
                  : "Écart encore trop faible pour déclarer un gagnant (< 10 points d'ouverture)."
              }}
            </p>
          </div>
        </template>
      </div>

      <!-- ═══ Tab: Prospects ══════════════════════════════════════════════ -->
      <div v-if="activeTab === 'prospects'" class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-muted text-sm">
            {{ campaign.prospects.length }} prospect{{ campaign.prospects.length !== 1 ? 's' : '' }}
          </p>
          <button class="btn-secondary" @click="showAddProspectsModal = true">
            <UIcon name="i-lucide-user-plus" class="mr-1.5 h-4 w-4" />Ajouter
          </button>
        </div>

        <div
          v-if="campaign.prospects.length === 0"
          class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] py-14 text-center"
        >
          <UIcon name="i-lucide-users" class="mx-auto mb-3 h-10 w-10 text-[var(--app-faint)]" />
          <p class="text-muted text-sm">Aucun prospect dans cette campagne</p>
          <button class="btn-secondary mt-4" @click="showAddProspectsModal = true">Ajouter des prospects</button>
        </div>

        <div v-else class="overflow-hidden rounded-xl border border-[var(--app-line)]">
          <table class="w-full border-collapse">
            <thead>
              <tr class="bg-[var(--app-bg)]">
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Prospect</th>
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Ville</th>
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Catégorie</th>
                <th v-if="campaign.ab_template_id_b" class="text-muted px-3 py-2.5 text-center text-xs font-semibold">
                  Variante
                </th>
                <th class="text-muted px-3 py-2.5 text-right text-xs font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="prospect in campaign.prospects"
                :key="prospect.id"
                class="border-t border-[var(--app-line)] transition-colors hover:bg-[var(--app-surface)]"
              >
                <td class="px-3 py-2.5">
                  <div class="text-sm font-medium text-[var(--app-ink)]">{{ prospect.name }}</div>
                  <div class="text-muted text-xs">{{ prospect.email || '—' }}</div>
                </td>
                <td class="text-muted px-3 py-2.5 text-sm">{{ prospect.city || '—' }}</td>
                <td class="text-muted px-3 py-2.5 text-sm">{{ prospect.category }}</td>
                <td v-if="campaign.ab_template_id_b" class="px-3 py-2.5 text-center">
                  <span
                    v-if="prospect.ab_variant"
                    :class="[
                      'rounded px-1.5 py-0.5 text-xs font-bold',
                      prospect.ab_variant === 'A'
                        ? 'bg-[#1f3a5c] text-[var(--app-accent-ink)]'
                        : 'bg-[#8d7bb8]/15 text-[#8d7bb8]',
                    ]"
                    >{{ prospect.ab_variant }}</span
                  >
                  <span v-else class="text-muted text-xs">—</span>
                </td>
                <td class="px-3 py-2.5 text-right">
                  <button
                    class="inline-flex items-center gap-1 rounded-lg border border-[var(--app-red)]/30 px-2 py-1 text-xs text-[var(--app-red)] transition-colors hover:bg-[var(--app-red)]/10"
                    @click="startRemoveProspect(prospect.id)"
                  >
                    <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />Retirer
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ═══ Tab: Queue ══════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'queue'" class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-muted text-sm">
            <span class="font-semibold text-[var(--app-accent-ink)]">{{ queueData?.pending_count ?? 0 }}</span> email{{
              (queueData?.pending_count ?? 0) !== 1 ? 's' : ''
            }}
            en attente
          </p>
          <button class="btn-secondary" @click="loadQueue">
            <UIcon name="i-lucide-rotate-cw" class="mr-1.5 h-4 w-4" />Actualiser
          </button>
        </div>

        <div
          v-if="!queueData || queueData.items.length === 0"
          class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] py-14 text-center"
        >
          <UIcon name="i-lucide-inbox" class="mx-auto mb-3 h-10 w-10 text-[var(--app-faint)]" />
          <p class="text-muted text-sm">Aucun élément en file d'attente</p>
        </div>

        <div v-else class="overflow-hidden rounded-xl border border-[var(--app-line)]">
          <table class="w-full border-collapse">
            <thead>
              <tr class="bg-[var(--app-bg)]">
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Prospect</th>
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Type</th>
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Planifié</th>
                <th class="text-muted px-3 py-2.5 text-left text-xs font-semibold">Statut</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in queueData.items"
                :key="item.id"
                class="border-t border-[var(--app-line)] transition-colors hover:bg-[var(--app-surface)]"
              >
                <td class="px-3 py-2.5">
                  <div class="text-sm text-[var(--app-ink)]">{{ item.prospect_name || `#${item.prospect_id}` }}</div>
                  <div class="text-muted text-xs">{{ item.prospect_email || '' }}</div>
                </td>
                <td class="px-3 py-2.5">
                  <span
                    :class="[
                      'rounded px-1.5 py-0.5 text-xs font-medium',
                      item.queue_type === 'initial'
                        ? 'bg-[#1f3a5c] text-[var(--app-accent-ink)]'
                        : 'bg-[#3a2a0a] text-[var(--app-accent)]',
                    ]"
                  >
                    {{ item.queue_type === 'initial' ? 'J1' : `Relance ${item.follow_up_index}` }}
                  </span>
                  <span
                    v-if="item.ab_variant"
                    :class="[
                      'ml-1 text-[10px] font-bold',
                      item.ab_variant === 'A' ? 'text-[var(--app-accent-ink)]' : 'text-[#8d7bb8]',
                    ]"
                    >{{ item.ab_variant }}</span
                  >
                </td>
                <td class="text-muted px-3 py-2.5 text-sm">{{ formatDate(item.scheduled_at) }}</td>
                <td class="px-3 py-2.5">
                  <span
                    :class="[
                      'rounded px-1.5 py-0.5 text-xs font-medium',
                      QUEUE_STATUS_STYLE[item.status] ?? 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
                    ]"
                    >{{ QUEUE_STATUS_LABELS[item.status] ?? item.status }}</span
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- ─── Modals ──────────────────────────────────────────────────────── -->

    <!-- Edit -->
    <div
      v-if="showEditModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)] backdrop-blur-sm"
      @click.self="showEditModal = false"
    >
      <div class="w-full max-w-md rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-6">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Modifier la campagne</h2>
        <form class="space-y-3" @submit.prevent="handleUpdateCampaign">
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Nom</label>
            <input v-model="editForm.name" type="text" required class="input-field" />
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Description</label>
            <textarea v-model="editForm.description" class="input-field" rows="3" />
          </div>
          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showEditModal = false">Annuler</button>
            <button type="submit" class="btn-primary flex-1">Enregistrer</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Add prospects -->
    <div
      v-if="showAddProspectsModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)] backdrop-blur-sm"
      @click.self="showAddProspectsModal = false"
    >
      <div class="w-full max-w-2xl rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-6">
        <h2 class="mb-4 text-base font-semibold text-[var(--app-ink)]">Ajouter des prospects</h2>
        <div v-if="availableProspects.length === 0" class="py-8 text-center">
          <p class="text-muted text-sm">Aucun prospect disponible à ajouter</p>
        </div>
        <div v-else>
          <div class="mb-4 max-h-96 space-y-1 overflow-y-auto">
            <div
              v-for="prospect in availableProspects"
              :key="prospect.id"
              class="flex cursor-pointer items-center gap-3 rounded-lg p-2.5 transition-colors hover:bg-[var(--app-surface)]"
              @click="toggleProspect(prospect.id)"
            >
              <UiCheckbox
                :id="`prospect-${prospect.id}`"
                :model-value="selectedProspectIds.includes(prospect.id)"
                @update:model-value="toggleProspect(prospect.id)"
              />
              <div>
                <p class="text-sm text-[var(--app-ink)]">{{ prospect.name }}</p>
                <p class="text-muted text-xs">{{ prospect.city }} · {{ prospect.category }}</p>
              </div>
            </div>
          </div>
          <div class="flex gap-3 border-t border-[var(--app-line)] pt-3">
            <button class="btn-secondary flex-1" @click="showAddProspectsModal = false">Annuler</button>
            <button
              :disabled="selectedProspectIds.length === 0"
              class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
              @click="handleAddProspects"
            >
              Ajouter {{ selectedProspectIds.length || '' }} prospect{{ selectedProspectIds.length !== 1 ? 's' : '' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <UiConfirmModal
      ref="removeProspectModal"
      title="Retirer le prospect"
      message="Retirer ce prospect de la campagne ? Il ne sera pas supprimé de votre liste."
      confirm-text="Retirer"
      cancel-text="Annuler"
      @confirm="handleRemoveProspect"
    />

    <UiConfirmModal
      ref="confirmDeleteModal"
      title="Supprimer la campagne"
      :message="`Supprimer définitivement « ${campaign?.name} » ? Cette action est irréversible.`"
      confirm-text="Supprimer"
      cancel-text="Annuler"
      @confirm="handleDeleteCampaign"
    />
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  campaignService,
  type CampaignDetailResponse,
  type CampaignQueueResponse,
  type CampaignStats,
} from '~/services/campaignService'
import { listProspects } from '~/services/prospectsService'
import { api } from '~/services/api'
import type { Prospect, CampaignVariantStats } from '~/types'
import { formatDate } from '~/utils/date'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

// ─── Types ──────────────────────────────────────────────────────────────────

/** Lightweight template shape used by the selects. */
interface TemplateOption {
  id: number
  name: string
  subject: string
}

// ─── Composables ──────────────────────────────────────────────────────────────

const router = useRouter()
const route = useRoute()
const toast = useToast()

// ─── Constants ────────────────────────────────────────────────────────────────

const TABS: ReadonlyArray<{ key: string; label: string; icon: string }> = [
  { key: 'config', label: 'Configuration', icon: 'i-lucide-settings-2' },
  { key: 'ab', label: 'A/B Test', icon: 'i-lucide-flask-conical' },
  { key: 'prospects', label: 'Prospects', icon: 'i-lucide-users' },
  { key: 'queue', label: "File d'attente", icon: 'i-lucide-list-checks' },
]

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  active: 'Active',
  completed: 'Terminée',
  paused: 'En pause',
  cancelled: 'Annulée',
}
const STATUS_STYLE: Record<string, string> = {
  draft: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
  active: 'bg-[#1a3a2a] text-[var(--app-green)]',
  completed: 'bg-[#1f3a5c] text-[var(--app-accent-ink)]',
  paused: 'bg-[#3a2a0a] text-[var(--app-accent)]',
  cancelled: 'bg-[#3a1a1a] text-[var(--app-red)]',
}
const STATUS_DOT: Record<string, string> = {
  draft: 'bg-[var(--app-ink-soft)]',
  active: 'bg-[var(--app-green)]',
  completed: 'bg-[var(--app-accent-ink)]',
  paused: 'bg-[var(--app-accent)]',
  cancelled: 'bg-[var(--app-red)]',
}
const QUEUE_STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  sending: 'En cours',
  sent: 'Envoyé',
  skipped: 'Ignoré',
  failed: 'Échoué',
}
const QUEUE_STATUS_STYLE: Record<string, string> = {
  pending: 'bg-[#1f3a5c] text-[var(--app-accent-ink)]',
  sending: 'bg-[#3a2a0a] text-[var(--app-accent)]',
  sent: 'bg-[#1a3a2a] text-[var(--app-green)]',
  skipped: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
  failed: 'bg-[#3a1a1a] text-[var(--app-red)]',
}

// ─── State ────────────────────────────────────────────────────────────────────

const campaign: Ref<CampaignDetailResponse | null> = ref<CampaignDetailResponse | null>(null)
const stats: Ref<CampaignStats | null> = ref<CampaignStats | null>(null)
const queueData: Ref<CampaignQueueResponse | null> = ref<CampaignQueueResponse | null>(null)
const allProspects: Ref<Prospect[]> = ref<Prospect[]>([])
const templates: Ref<TemplateOption[]> = ref<TemplateOption[]>([])
const isLoading: Ref<boolean> = ref<boolean>(false)
const isSavingSettings: Ref<boolean> = ref<boolean>(false)
const activeTab: Ref<string> = ref<string>('config')
const showEditModal: Ref<boolean> = ref<boolean>(false)
const showAddProspectsModal: Ref<boolean> = ref<boolean>(false)
const selectedProspectIds: Ref<number[]> = ref<number[]>([])
const prospectToRemoveId: Ref<number | null> = ref<number | null>(null)
const removeProspectModal: Ref<{ open: () => void } | null> = ref(null)
const confirmDeleteModal: Ref<{ open: () => void } | null> = ref(null)

const editForm: Ref<{ name: string; description: string }> = ref({ name: '', description: '' })

const settingsForm: Ref<{
  template_id: number
  ab_template_id_b: number
  send_delay_minutes: number
  enable_ab: boolean
  behavior_personalized_followups: boolean
  follow_ups: Array<{ template_id: number; delay_days: number }>
}> = ref({
  template_id: 0,
  ab_template_id_b: 0,
  send_delay_minutes: 20,
  enable_ab: false,
  behavior_personalized_followups: false,
  follow_ups: [],
})

const campaignId: ComputedRef<number> = computed((): number => Number(route.params.id))

// ─── Computed ─────────────────────────────────────────────────────────────────

const availableProspects: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  if (!campaign.value) return []
  const existingIds: Set<number> = new Set(campaign.value.prospects.map((p) => p.id))
  return allProspects.value.filter((p: Prospect): boolean => !existingIds.has(p.id))
})

const canLaunch: ComputedRef<boolean> = computed((): boolean => settingsForm.value.template_id > 0)

/** Metric cards for the stats strip. */
const metricCards: ComputedRef<Array<{ label: string; value: number | string; icon: string; color: string }>> =
  computed(() => {
    const s = stats.value
    if (!s) return []
    return [
      { label: 'Envoyés', value: s.total_emails_sent, icon: 'i-lucide-send', color: 'text-[var(--app-ink)]' },
      { label: 'Délivrés', value: s.emails_delivered, icon: 'i-lucide-circle-check', color: 'text-[var(--app-green)]' },
      { label: 'Ouverts', value: s.emails_opened, icon: 'i-lucide-mail-open', color: 'text-[#8d7bb8]' },
      { label: 'Cliqués', value: s.emails_clicked, icon: 'i-lucide-mouse-pointer-click', color: 'text-[#c4b5fd]' },
      { label: 'Taux ouv.', value: `${s.open_rate}%`, icon: 'i-lucide-eye', color: 'text-[var(--app-accent-ink)]' },
      { label: 'Taux clic', value: `${s.click_rate}%`, icon: 'i-lucide-pointer', color: 'text-[var(--app-accent)]' },
    ]
  })

const hasSignificantDiff: ComputedRef<boolean> = computed((): boolean => {
  const ab = stats.value?.ab_stats
  if (!ab || ab.length < 2) return false
  return Math.abs(ab[0].open_rate - ab[1].open_rate) >= 10
})

const winnerMessage: ComputedRef<string> = computed((): string => {
  const ab = stats.value?.ab_stats
  if (!ab || ab.length < 2) return ''
  const winner = ab[0].open_rate > ab[1].open_rate ? ab[0] : ab[1]
  return `Variante ${winner.variant} en tête avec ${winner.open_rate}% d'ouverture.`
})

/** Detects whether the settings form differs from the persisted campaign. */
const settingsDirty: ComputedRef<boolean> = computed((): boolean => {
  if (!campaign.value) return false
  const c = campaign.value
  const f = settingsForm.value
  if (f.template_id !== (c.template_id ?? 0)) return true
  if (f.send_delay_minutes !== c.send_delay_minutes) return true
  if (f.behavior_personalized_followups !== c.behavior_personalized_followups) return true
  if (f.enable_ab !== !!c.ab_template_id_b) return true
  if (f.enable_ab && f.ab_template_id_b !== (c.ab_template_id_b ?? 0)) return true
  if (f.follow_ups.length !== c.follow_ups.length) return true
  return f.follow_ups.some(
    (fu, i) => fu.template_id !== c.follow_ups[i]?.template_id || fu.delay_days !== c.follow_ups[i]?.delay_days,
  )
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Determine if a variant is the open-rate winner (>= 10pp lead).
 * @param v - Variant stats to evaluate.
 */
function isWinner(v: CampaignVariantStats): boolean {
  const ab = stats.value?.ab_stats
  if (!ab || ab.length < 2 || !hasSignificantDiff.value) return false
  return ab.every(
    (other: CampaignVariantStats): boolean => other.variant === v.variant || v.open_rate > other.open_rate,
  )
}

// ─── Data loading ─────────────────────────────────────────────────────────────

/**
 * Load campaign, stats, queue, prospects and templates in parallel.
 */
async function loadAll(): Promise<void> {
  isLoading.value = true
  try {
    const [c, s, q, prospects, tpls] = await Promise.all([
      campaignService.get(campaignId.value),
      campaignService.getStats(campaignId.value).catch((): null => null),
      campaignService.getQueue(campaignId.value, { limit: 100 }).catch((): null => null),
      listProspects(),
      api.get<TemplateOption[]>('/api/v1/email-templates').catch((): TemplateOption[] => []),
    ])
    campaign.value = c
    stats.value = s
    queueData.value = q
    allProspects.value = prospects
    templates.value = Array.isArray(tpls) ? tpls : []
    syncSettingsForm(c)
  } catch {
    toast.error('Campagne introuvable')
    router.push('/dashboard/campaigns')
  } finally {
    isLoading.value = false
  }
}

/**
 * Mirror persisted campaign config into the editable settings form.
 * @param c - Campaign detail response.
 */
function syncSettingsForm(c: CampaignDetailResponse): void {
  settingsForm.value = {
    template_id: c.template_id ?? 0,
    ab_template_id_b: c.ab_template_id_b ?? 0,
    send_delay_minutes: c.send_delay_minutes,
    enable_ab: !!c.ab_template_id_b,
    behavior_personalized_followups: c.behavior_personalized_followups,
    follow_ups: c.follow_ups.map((fu) => ({ template_id: fu.template_id, delay_days: fu.delay_days })),
  }
}

/**
 * Reload only the queue (used by the refresh button and tab switch).
 */
async function loadQueue(): Promise<void> {
  queueData.value = await campaignService.getQueue(campaignId.value, { limit: 100 })
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

/**
 * Persist the settings form to the backend.
 */
async function saveSettings(): Promise<void> {
  isSavingSettings.value = true
  try {
    const f = settingsForm.value
    const updated = await campaignService.updateSettings(campaignId.value, {
      template_id: f.template_id > 0 ? f.template_id : undefined,
      ab_template_id_b: f.enable_ab && f.ab_template_id_b > 0 ? f.ab_template_id_b : undefined,
      disable_ab: !f.enable_ab,
      send_delay_minutes: f.send_delay_minutes,
      behavior_personalized_followups: f.behavior_personalized_followups,
      follow_ups: f.follow_ups
        .filter((fu) => fu.template_id > 0)
        .map((fu, i) => ({ template_id: fu.template_id, delay_days: fu.delay_days, position: i + 1 })),
    })
    campaign.value = updated
    syncSettingsForm(updated)
    toast.success('Configuration enregistrée')
  } catch {
    toast.error("Erreur lors de l'enregistrement")
  } finally {
    isSavingSettings.value = false
  }
}

/**
 * Launch the campaign using the stored template and the user's Resend config.
 */
async function handleLaunch(): Promise<void> {
  try {
    if (settingsDirty.value) await saveSettings()
    const result = await campaignService.launch(campaignId.value)
    toast.success(result.message)
    await loadAll()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors du lancement')
  }
}

/**
 * Pause the campaign — cancel all pending queue items.
 */
async function handlePause(): Promise<void> {
  try {
    const result = await campaignService.pause(campaignId.value)
    toast.success(`Campagne en pause — ${result.cancelled} email(s) annulé(s)`)
    await loadAll()
  } catch {
    toast.error('Erreur lors de la mise en pause')
  }
}

/**
 * Resume a paused campaign — re-enqueue prospects not yet contacted.
 */
async function handleResume(): Promise<void> {
  try {
    const result = await campaignService.resume(campaignId.value)
    toast.success(`Campagne reprise — ${result.enqueued} email(s) planifié(s)`)
    await loadAll()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la reprise')
  }
}

/**
 * Update campaign name/description.
 */
async function handleUpdateCampaign(): Promise<void> {
  try {
    const updated = await campaignService.update(campaignId.value, {
      name: editForm.value.name,
      description: editForm.value.description,
    })
    if (campaign.value) campaign.value = { ...campaign.value, ...updated }
    showEditModal.value = false
    toast.success('Campagne mise à jour')
  } catch {
    toast.error('Erreur lors de la mise à jour')
  }
}

/**
 * Permanently delete the campaign.
 */
async function handleDeleteCampaign(): Promise<void> {
  try {
    await campaignService.delete(campaignId.value)
    toast.success('Campagne supprimée')
    router.push('/dashboard/campaigns')
  } catch {
    toast.error('Erreur lors de la suppression')
  }
}

/**
 * Add the selected prospects to the campaign.
 */
async function handleAddProspects(): Promise<void> {
  if (selectedProspectIds.value.length === 0) return
  try {
    campaign.value = await campaignService.addProspects(campaignId.value, selectedProspectIds.value)
    toast.success(`${selectedProspectIds.value.length} prospect(s) ajouté(s)`)
    selectedProspectIds.value = []
    showAddProspectsModal.value = false
  } catch {
    toast.error("Erreur lors de l'ajout")
  }
}

/**
 * Open the removal confirmation for a prospect.
 * @param prospectId - Prospect ID to target.
 */
function startRemoveProspect(prospectId: number): void {
  prospectToRemoveId.value = prospectId
  removeProspectModal.value?.open()
}

/**
 * Remove the targeted prospect after confirmation.
 */
async function handleRemoveProspect(): Promise<void> {
  if (!prospectToRemoveId.value) return
  try {
    campaign.value = await campaignService.removeProspect(campaignId.value, prospectToRemoveId.value)
    toast.success('Prospect retiré')
  } catch {
    toast.error('Erreur lors du retrait')
  } finally {
    prospectToRemoveId.value = null
  }
}

/**
 * Toggle a prospect's selection in the add modal.
 * @param id - Prospect ID.
 */
function toggleProspect(id: number): void {
  const idx = selectedProspectIds.value.indexOf(id)
  if (idx > -1) selectedProspectIds.value.splice(idx, 1)
  else selectedProspectIds.value.push(id)
}

/**
 * Open the edit modal pre-filled with current values.
 */
function openEditModal(): void {
  if (!campaign.value) return
  editForm.value = { name: campaign.value.name, description: campaign.value.description ?? '' }
  showEditModal.value = true
}

/** Append an empty follow-up slot. */
function addFollowUp(): void {
  settingsForm.value.follow_ups.push({ template_id: 0, delay_days: 5 })
}

/**
 * Remove a follow-up slot.
 * @param idx - Index to remove.
 */
function removeFollowUp(idx: number): void {
  settingsForm.value.follow_ups.splice(idx, 1)
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted((): void => {
  loadAll()
})

watch(activeTab, (tab: string): void => {
  if (tab === 'queue') loadQueue()
})
</script>
