<template>
  <div class="space-y-6">
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-circle" class="h-8 w-8 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <template v-else-if="campaign">
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
              <h1 class="app-page-title truncate">{{ campaign.name }}</h1>
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
                class="inline-flex items-center gap-1 rounded-full bg-[var(--app-violet-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--app-violet)]"
              >
                <UIcon name="i-lucide-flask-conical" class="h-3 w-3" /> A/B
              </span>
              <span
                class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                :class="
                  isSms
                    ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                    : 'bg-[var(--app-blue-soft)] text-[var(--app-blue)]'
                "
              >
                <UIcon :name="isSms ? 'i-lucide-message-square-text' : 'i-lucide-mail'" class="h-3 w-3" />
                {{ isSms ? 'SMS' : 'Email' }}
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
            :title="canLaunch ? '' : launchDisabledReason"
            @click="handleLaunch"
          >
            <UIcon name="i-lucide-rocket" class="mr-1.5 h-4 w-4" />
            {{ campaign.status === 'paused' ? 'Relancer' : 'Lancer' }}
          </button>
          <button
            class="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)] disabled:opacity-50"
            title="Actualiser"
            :disabled="isRefreshing"
            @click="refreshLiveData"
          >
            <UIcon name="i-lucide-rotate-cw" :class="['h-4 w-4', { 'animate-spin': isRefreshing }]" />
          </button>
          <button
            class="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface)] hover:text-[var(--app-ink)]"
            title="Modifier"
            @click="openEditDrawer"
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

      <div
        v-if="metricCards.length"
        class="grid grid-cols-2 gap-3 @xl:grid-cols-4"
        :class="{ '@5xl:grid-cols-7': !isSms }"
      >
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

      <div class="border-b border-[var(--app-line)]">
        <nav class="flex gap-1">
          <button
            v-for="tab in visibleTabs"
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
              class="rounded-full bg-[var(--app-blue-soft)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-blue)]"
            >
              {{ queueData.pending_count }}
            </span>
          </button>
        </nav>
      </div>

      <div v-if="activeTab === 'config'" class="space-y-4">
        <section class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
          <div class="mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-timer" class="h-4 w-4 text-[var(--app-accent-ink)]" />
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Cadence d'envoi</h3>
          </div>

          <p class="text-sm text-[var(--app-ink)]">
            Cette campagne suit vos réglages d'envoi :
            <strong class="font-semibold">{{ sendPolicySummary }}</strong>
          </p>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <button type="button" class="app-btn-secondary h-8 px-3 text-xs" @click="openSendPolicyDrawer">
              <UIcon name="i-lucide-sliders-horizontal" class="h-3.5 w-3.5" />
              Réglages d'envoi
            </button>
          </div>

          <div class="mt-4 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-sm font-medium text-[var(--app-ink)]">Limiter cette campagne par jour</p>
                <p class="mt-0.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">
                  Nombre maximum d'envois par jour pour cette campagne, en plus du plafond global. Mettez 1 sur
                  plusieurs campagnes (barbier, garage, food) pour envoyer 1 de chaque par jour.
                </p>
              </div>
              <button
                type="button"
                class="mt-0.5 shrink-0"
                :aria-pressed="settingsForm.max_emails_per_day !== null"
                @click="toggleDailyCap"
              >
                <span
                  :class="[
                    'relative inline-block h-5 w-9 rounded-full transition-colors',
                    settingsForm.max_emails_per_day !== null ? 'bg-[var(--app-green)]' : 'bg-[var(--app-surface)]',
                  ]"
                >
                  <span
                    :class="[
                      'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all',
                      settingsForm.max_emails_per_day !== null ? 'left-4' : 'left-0.5',
                    ]"
                  />
                </span>
              </button>
            </div>
            <div
              v-if="settingsForm.max_emails_per_day !== null"
              class="mt-3 flex items-center gap-2 text-sm text-[var(--app-ink)]"
            >
              <span>Maximum</span>
              <input
                v-model.number="settingsForm.max_emails_per_day"
                type="number"
                min="1"
                max="1000"
                class="input-field h-9 w-20 text-center"
                placeholder="1"
              />
              <span>envoi(s) par jour</span>
            </div>
          </div>

          <UiCollapsibleCard icon="i-lucide-wrench" title="Espacement (avancé)" class="mt-4">
            <div class="space-y-2 px-4 py-4">
              <div class="flex items-center gap-2 text-sm text-[var(--app-ink)]">
                <span>1 email toutes les</span>
                <input
                  v-model.number="settingsForm.send_delay_minutes"
                  type="number"
                  min="1"
                  max="1440"
                  class="input-field h-9 w-20 text-center"
                  placeholder="20"
                />
                <span>minutes</span>
              </div>
              <p class="text-xs leading-relaxed text-[var(--app-ink-soft)]">
                Écart minimum entre deux envois. Le plafond journalier et la fenêtre horaire de vos réglages priment :
                ils s'appliquent en plus de cet espacement.
              </p>
            </div>
          </UiCollapsibleCard>
        </section>

        <section v-if="isSms" class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
          <div class="mb-4 flex items-center gap-2">
            <UIcon name="i-lucide-message-square-text" class="h-4 w-4 text-[var(--app-accent-ink)]" />
            <h3 class="text-sm font-semibold text-[var(--app-ink)]">Message SMS</h3>
          </div>

          <div
            v-if="!smsReady"
            class="mb-3 flex items-start gap-2 rounded-lg border border-[var(--app-red)]/20 bg-[var(--app-red-soft)] px-3 py-2"
          >
            <UIcon name="i-lucide-triangle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-red)]" />
            <p class="text-xs text-[var(--app-ink)]">
              <span class="font-medium">Expéditeur SMS requis.</span>
              Renseignez un nom d'expéditeur dans
              <NuxtLink to="/dashboard/settings/sms" class="font-medium underline">Paramètres → Relance SMS</NuxtLink>
              avant de lancer.
            </p>
          </div>
          <div v-else class="mb-3 flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
            <UIcon name="i-lucide-circle-check" class="h-3.5 w-3.5 text-[var(--app-green)]" />
            Expéditeur : <span class="font-medium text-[var(--app-ink)]">{{ smsConfig?.sender }}</span>
          </div>

          <div v-if="smsTemplateOptions.length" class="mb-3">
            <label class="text-muted mb-1.5 block text-xs font-medium">Modèle de message</label>
            <UiSelectField
              :model-value="smsTemplate?.key ?? ''"
              :options="smsTemplateOptions"
              placeholder="Choisir un modèle…"
              @update:model-value="onChangeSmsTemplate"
            />
          </div>

          <p class="text-muted mb-1.5 text-xs font-medium">Aperçu du message</p>
          <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)] p-3">
            <p class="text-sm leading-relaxed whitespace-pre-line text-[var(--app-ink)]">{{ smsPreview }}</p>
          </div>
          <p class="text-muted mt-2 text-[11px] leading-relaxed">
            Modèle « {{ smsTemplate?.name ?? 'Direct' }} » de la bibliothèque SMS, rendu pour chaque prospect
            (salutation, nom de l'entreprise, lien de sa démo, votre prénom et la mention « STOP »). Un seul SMS par
            prospect, sans A/B ni relance.
          </p>
        </section>

        <section v-if="!isSms" class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
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
                  settingsForm.enable_ab ? 'bg-[var(--app-violet)]' : 'bg-[var(--app-surface-2)]',
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

          <div :class="settingsForm.enable_ab ? 'grid gap-4 @2xl:grid-cols-2' : ''">
            <div>
              <label
                v-if="settingsForm.enable_ab"
                class="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[var(--app-accent-ink)]"
              >
                <span class="rounded bg-[var(--app-accent-soft)] px-1.5 py-0.5 font-bold">A</span> Variante A
              </label>
              <UiTemplateSelect
                v-model="settingsForm.template_id"
                :templates="templates"
                allow-create
                @create="openCreate((id) => (settingsForm.template_id = id))"
                @preview="openPreview"
              />
            </div>
            <div v-if="settingsForm.enable_ab">
              <label class="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[var(--app-violet)]">
                <span class="rounded bg-[var(--app-violet-soft)] px-1.5 py-0.5 font-bold">B</span> Variante B
              </label>
              <UiTemplateSelect
                v-model="settingsForm.ab_template_id_b"
                :templates="templates"
                allow-create
                @create="openCreate((id) => (settingsForm.ab_template_id_b = id))"
                @preview="openPreview"
              />
            </div>
          </div>

          <div
            v-if="settingsForm.enable_ab"
            class="mt-3 flex items-start gap-2 rounded-lg border border-[var(--app-violet)]/20 bg-[var(--app-violet-soft)] px-3 py-2"
          >
            <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-violet)]" />
            <p class="text-xs text-[var(--app-violet)]">
              Distribution 50/50 automatique — chaque variante part à la moitié des prospects.
            </p>
          </div>
        </section>

        <section v-if="!isSms" class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
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
            v-if="hasReplyCapture"
            class="mb-3 flex items-start gap-2 rounded-lg border border-[var(--app-green)]/20 bg-[var(--app-green-soft)] px-3 py-2"
          >
            <UIcon name="i-lucide-circle-check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-green)]" />
            <p class="text-xs text-[var(--app-ink)]">
              <span class="font-medium">Arrêt automatique à la réponse.</span>
              Dès qu'un prospect répond, ses relances restantes sont annulées — rien à configurer.
            </p>
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
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--app-accent-soft)] text-xs font-bold text-[var(--app-accent-ink)]"
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
                    placeholder="5"
                  />
                  <span>après l'envoi précédent</span>
                </div>
                <UiTemplateSelect
                  v-model="fu.template_id"
                  :templates="templates"
                  allow-create
                  @create="openCreate((id) => (fu.template_id = id))"
                  @preview="openPreview"
                />
              </div>
              <button
                class="absolute top-2 right-2 text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-red)]"
                @click="removeFollowUp(idx)"
              >
                <UIcon name="i-lucide-x" class="h-4 w-4" />
              </button>
            </div>
          </div>

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

          <label
            class="mt-3 flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
          >
            <input
              v-model="settingsForm.include_video"
              type="checkbox"
              class="mt-0.5 h-4 w-4 rounded border-[var(--app-line)]"
            />
            <span class="text-xs">
              <span class="font-medium text-[var(--app-ink)]">Joindre la vidéo de prospection</span>
              <span class="text-muted mt-0.5 block">
                Insère la vignette vidéo quand une vidéo est prête. Décochée, la campagne n'envoie que le lien du site
                (les modèles combinés basculent alors sur la démo seule).
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
          <div class="grid gap-4 @2xl:grid-cols-2">
            <div
              v-for="v in stats.ab_stats"
              :key="v.variant"
              :class="[
                'rounded-xl border-2 bg-[var(--app-surface)] p-5',
                v.variant === 'A' ? 'border-[var(--app-accent-ink)]/30' : 'border-[var(--app-violet)]/30',
              ]"
            >
              <div class="mb-4 flex items-center justify-between">
                <span
                  :class="[
                    'flex items-center gap-2 text-base font-bold',
                    v.variant === 'A' ? 'text-[var(--app-accent-ink)]' : 'text-[var(--app-violet)]',
                  ]"
                >
                  <span
                    :class="[
                      'flex h-6 w-6 items-center justify-center rounded-lg text-sm',
                      v.variant === 'A' ? 'bg-[var(--app-accent-soft)]' : 'bg-[var(--app-violet-soft)]',
                    ]"
                    >{{ v.variant }}</span
                  >
                  Variante {{ v.variant }}
                </span>
                <span
                  v-if="isWinner(v)"
                  class="inline-flex items-center gap-1 rounded-full bg-[var(--app-green-soft)] px-2 py-0.5 text-xs font-semibold text-[var(--app-green)]"
                >
                  <UIcon name="i-lucide-trophy" class="h-3 w-3" /> Gagnant
                </span>
              </div>
              <div class="grid grid-cols-4 gap-3 text-center">
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
                <div>
                  <p class="text-xl font-bold text-[var(--app-green)]">{{ v.replied }}</p>
                  <p class="text-muted text-xs">Réponses</p>
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
                      v.variant === 'A' ? 'bg-[var(--app-accent-ink)]' : 'bg-[var(--app-violet)]',
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

      <div v-if="activeTab === 'prospects'" class="space-y-4">
        <template v-if="campaign.prospects.length > 0">
          <div class="flex items-center justify-between">
            <p class="text-muted text-sm">
              {{ campaign.prospects.length }} prospect{{ campaign.prospects.length !== 1 ? 's' : '' }}
            </p>
            <button class="btn-secondary" @click="openAddProspectsDrawer">
              <UIcon name="i-lucide-user-plus" class="mr-1.5 h-4 w-4" />Ajouter
            </button>
          </div>

          <div class="app-card overflow-hidden">
            <UiProspectTable
              :prospects="campaignProspectRows"
              :selected-prospects="campaignSelectedProspects"
              :show-ab-variant="!!campaign.ab_template_id_b"
              :ab-variants="campaignAbVariants"
              row-action="remove"
              reorderable
              @view-prospect="openProspectDrawer"
              @remove-prospect="startRemoveProspectFromRow"
              @reorder="handleReorderProspects"
              @toggle-select="toggleCampaignProspectSelect"
              @toggle-select-all="toggleCampaignProspectSelectAll"
            />
          </div>
        </template>

        <div
          v-else
          class="flex flex-col items-center rounded-xl border border-dashed border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-16 text-center"
        >
          <span class="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-[var(--app-line)]">
            <UIcon name="i-lucide-user-plus" class="h-5 w-5 text-[var(--app-ink-soft)]" />
          </span>
          <p class="text-sm font-semibold text-[var(--app-ink)]">Aucun prospect dans cette campagne</p>
          <p class="text-muted mx-auto mt-1 max-w-xs text-sm">
            Ajoutez des prospects pour programmer les premiers envois de cette campagne.
          </p>
          <button class="btn-primary mt-5" @click="openAddProspectsDrawer">
            <UIcon name="i-lucide-user-plus" class="mr-1.5 h-4 w-4" />Ajouter des prospects
          </button>
        </div>
      </div>

      <div v-if="activeTab === 'queue'" class="space-y-4">
        <p class="text-muted text-sm">
          <span class="font-semibold text-[var(--app-accent-ink)]">{{ queueData?.pending_count ?? 0 }}</span>
          {{ isSms ? 'SMS' : (queueData?.pending_count ?? 0) !== 1 ? 'emails' : 'email' }}
          en attente
        </p>

        <div
          v-if="!queueData || queueData.items.length === 0"
          class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] py-14 text-center"
        >
          <UIcon name="i-lucide-inbox" class="mx-auto mb-3 h-10 w-10 text-[var(--app-faint)]" />
          <p class="text-muted text-sm">Aucun élément en file d'attente</p>
        </div>

        <div v-else class="app-card overflow-hidden">
          <BaseTable min-width="760px">
            <template #head>
              <BaseTableTh>Prospect</BaseTableTh>
              <BaseTableTh>Type</BaseTableTh>
              <BaseTableTh>Planifié</BaseTableTh>
              <BaseTableTh align="center">Statut</BaseTableTh>
              <BaseTableTh align="right">Actions</BaseTableTh>
            </template>

            <BaseTableTr v-for="item in queueData.items" :key="item.id">
              <BaseTableTd>
                <span class="block text-sm font-semibold text-[var(--app-ink)]">
                  {{ item.prospect_name || `#${item.prospect_id}` }}
                </span>
                <span v-if="item.prospect_email" class="font-label text-xs text-[var(--app-ink-soft)]">
                  {{ item.prospect_email }}
                </span>
              </BaseTableTd>

              <BaseTableTd label="Type">
                <span class="flex items-center gap-1.5">
                  <span
                    :class="['app-badge', item.queue_type === 'initial' ? 'app-badge--info' : 'app-badge--progress']"
                  >
                    {{ item.queue_type === 'initial' ? 'J1' : `Relance ${item.follow_up_index}` }}
                  </span>
                  <span
                    v-if="item.ab_variant"
                    :class="[
                      'rounded px-1.5 py-0.5 text-xs font-bold',
                      item.ab_variant === 'A'
                        ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
                        : 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
                    ]"
                  >
                    {{ item.ab_variant }}
                  </span>
                </span>
              </BaseTableTd>

              <BaseTableTd label="Planifié" class="font-label text-xs text-[var(--app-ink-soft)]">
                {{ formatCompactDateTime(item.scheduled_at) }}
              </BaseTableTd>

              <BaseTableTd label="Statut" align="center">
                <span :class="['app-badge', QUEUE_STATUS_BADGE_CLASS[item.status] ?? '']">
                  {{ QUEUE_STATUS_LABELS[item.status] ?? item.status }}
                </span>
                <span v-if="item.skip_reason" class="text-muted mt-1 block text-xs">
                  {{ item.skip_reason }}
                </span>
              </BaseTableTd>

              <BaseTableTd label="Actions" align="right">
                <button
                  v-if="item.status === 'pending'"
                  type="button"
                  class="app-btn-secondary h-8 px-3 text-xs"
                  @click="startCancelQueueItem(item)"
                >
                  <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
                  Annuler
                </button>
                <button
                  v-else-if="item.status === 'skipped'"
                  type="button"
                  class="app-btn-primary h-8 px-3 text-xs"
                  @click="startResendQueueItem(item)"
                >
                  <UIcon name="i-lucide-send" class="h-3.5 w-3.5" />
                  Renvoyer
                </button>
                <span v-else class="text-muted text-xs">—</span>
              </BaseTableTd>
            </BaseTableTr>
          </BaseTable>
        </div>
      </div>
    </template>

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

    <UiConfirmModal
      ref="cancelQueueModal"
      title="Annuler l'envoi"
      :message="`Ce ${isSms ? 'SMS' : 'email'} ne sera pas envoyé. Vous pourrez le renvoyer manuellement plus tard depuis la file d'attente.`"
      confirm-text="Ne pas envoyer"
      cancel-text="Retour"
      @confirm="handleCancelQueueItem"
    />

    <UiConfirmModal
      ref="resendQueueModal"
      title="Renvoyer l'email"
      :message="`Ce ${isSms ? 'SMS' : 'email'} sera renvoyé dans la minute qui suit.`"
      confirm-text="Renvoyer"
      cancel-text="Retour"
      confirm-button-variant="primary"
      @confirm="handleResendQueueItem"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseAuthReturn, UseToastReturn } from '~/types/Composables'
import type { TemplateOption } from '~/types/CampaignDetailPage'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type {
  CampaignDetailResponse,
  CampaignProspect,
  CampaignQueueItem,
  CampaignQueueResponse,
  CampaignStats,
  LaunchCampaignResponse,
} from '~/services/campaignService'
import { CampaignService } from '~/services/campaignService'
import { ProspectsService } from '~/services/prospectsService'
import { ApiClient } from '~/services/api'
import type { CampaignFollowUp, CampaignVariantStats, Prospect, ProspectSource } from '~/types'
import { formatCompactDateTime } from '~/utils/date'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import type { SendPolicy } from '~/types/Automation'
import { SendPolicyService } from '~/services/sendPolicyService'
import { formatSendPolicySummary } from '~/utils/sendPolicy'
import type { SendingIdentityResponse } from '~/services/settingsService'
import { SettingsService } from '~/services/settingsService'
import { SmsService, type SmsConfig, type SmsTemplate, type SmsTemplatePreview } from '~/services/smsService'
import { SmsVariables } from '~/utils/smsVariables'
import type { SelectFieldOption } from '~/types/SelectField'

definePageMeta({ layout: 'dashboard', middleware: 'auth' })

const router: ReturnType<typeof useRouter> = useRouter()
const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()
const { user }: UseAuthReturn = useAuth()

const TABS: { key: string; label: string; icon: string }[] = [
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
  active: 'bg-[var(--app-green-soft)] text-[var(--app-green)]',
  completed: 'bg-[var(--app-blue-soft)] text-[var(--app-blue)]',
  paused: 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]',
  cancelled: 'bg-[var(--app-red-soft)] text-[var(--app-red)]',
}
const STATUS_DOT: Record<string, string> = {
  draft: 'bg-[var(--app-ink-soft)]',
  active: 'bg-[var(--app-green)]',
  completed: 'bg-[var(--app-blue)]',
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
const QUEUE_STATUS_BADGE_CLASS: Record<string, string> = {
  pending: 'app-badge--info',
  sending: 'app-badge--progress',
  sent: 'app-badge--success',
  skipped: '',
  failed: 'app-badge--danger',
}

const AUTO_REFRESH_INTERVAL_MS: number = 30_000

const campaign: Ref<CampaignDetailResponse | null> = ref(null)
const stats: Ref<CampaignStats | null> = ref(null)
const queueData: Ref<CampaignQueueResponse | null> = ref(null)
const allProspects: Ref<Prospect[]> = ref([])
const templates: Ref<TemplateOption[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const isSavingSettings: Ref<boolean> = ref(false)
const activeTab: Ref<string> = ref('config')
const campaignSelectedProspects: Ref<string[]> = ref([])
const prospectToRemoveId: Ref<number | null> = ref(null)
const removeProspectModal: Ref<{ open: () => void } | null> = ref(null)
const confirmDeleteModal: Ref<{ open: () => void } | null> = ref(null)
const queueActionItem: Ref<CampaignQueueItem | null> = ref(null)
const cancelQueueModal: Ref<{ open: () => void } | null> = ref(null)
const resendQueueModal: Ref<{ open: () => void } | null> = ref(null)
const isRefreshing: Ref<boolean> = ref(false)
const autoRefreshTimer: Ref<ReturnType<typeof setInterval> | null> = ref(null)
/** SMS sender config — loaded only for SMS campaigns, drives the launch precondition + config panel. */
const smsConfig: Ref<SmsConfig | null> = ref(null)

/** First-contact templates of the SMS library, offered in the campaign's template picker. */
const smsTemplates: Ref<SmsTemplate[]> = ref([])

/** The first-contact template this SMS campaign sends (chosen key, else the library default). */
const smsTemplate: Ref<SmsTemplate | null> = ref(null)

/** The SMS rendered for the campaign's first prospect, when his demo allows it. */
const smsRenderedPreview: Ref<string> = ref('')

const settingsForm: Ref<{
  template_id: number
  ab_template_id_b: number
  send_delay_minutes: number
  max_emails_per_day: number | null
  enable_ab: boolean
  behavior_personalized_followups: boolean
  include_video: boolean
  follow_ups: Array<{ template_id: number; delay_days: number }>
}> = ref({
  template_id: 0,
  ab_template_id_b: 0,
  send_delay_minutes: 20,
  max_emails_per_day: null,
  enable_ab: false,
  behavior_personalized_followups: false,
  include_video: true,
  follow_ups: [],
})

const { openCreate, openPreview }: EmailTemplateCreator = useEmailTemplateCreator(templates, reloadTemplates)

/** The user's effective sending cadence — it governs this campaign, not the raw spacing. */
const sendPolicy: Ref<SendPolicy | null> = ref(null)

const sendPolicySummary: ComputedRef<string> = computed((): string => formatSendPolicySummary(sendPolicy.value))

/** Persistent drawer stack (prospect detail lives in the layout). */
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const campaignId: ComputedRef<number> = computed((): number => Number(route.params.id))

/** True for an SMS-channel campaign — swaps the email-only UI (template/A-B/video/follow-ups/stats) for SMS. */
const isSms: ComputedRef<boolean> = computed((): boolean => campaign.value?.channel === 'sms')

/** SMS campaigns can launch only once a sender is configured and the provider is ready. */
const smsReady: ComputedRef<boolean> = computed(
  (): boolean => !!smsConfig.value?.sender && !!smsConfig.value?.provider_ready,
)

/** Options for the SMS template picker (first-contact library). */
const smsTemplateOptions: ComputedRef<SelectFieldOption<string>[]> = computed((): SelectFieldOption<string>[] =>
  smsTemplates.value.map(
    (template: SmsTemplate): SelectFieldOption<string> => ({
      value: template.key,
      label: template.name,
    }),
  ),
)

/** The real SMS of the first prospect when rendered, else the template with sample values. */
const smsPreview: ComputedRef<string> = computed((): string => {
  const body: string = smsRenderedPreview.value
    ? smsRenderedPreview.value
    : SmsVariables.renderWithSampleValues(smsTemplate.value?.body ?? '', SmsVariables.firstNameOf(user.value?.name))
  return body ? `${body} STOP au 36180` : ''
})

/** Send progress for an SMS campaign, counted from the queue (no email stats apply). */
const smsQueueCounts: ComputedRef<{ sent: number; pending: number; failed: number }> = computed(() => {
  const items: CampaignQueueItem[] = queueData.value?.items ?? []
  let sent: number = 0
  let pending: number = 0
  let failed: number = 0
  for (const item of items) {
    if (item.status === 'sent') sent += 1
    else if (item.status === 'pending' || item.status === 'sending') pending += 1
    else if (item.status === 'failed' || item.status === 'skipped') failed += 1
  }
  return { sent, pending, failed }
})

/** Tabs shown for this campaign — the A/B tab is email-only. */
const visibleTabs: ComputedRef<{ key: string; label: string; icon: string }[]> = computed(() =>
  isSms.value ? TABS.filter((tab: { key: string; label: string; icon: string }): boolean => tab.key !== 'ab') : TABS,
)

/** Campaign prospects enriched with full list data when available. */
const campaignProspectRows: ComputedRef<Prospect[]> = computed((): Prospect[] => {
  if (!campaign.value) return []
  const byId: Map<number, Prospect> = new Map(allProspects.value.map((prospect: Prospect) => [prospect.id, prospect]))
  return campaign.value.prospects.map((cp: CampaignProspect): Prospect => {
    const full: Prospect | undefined = byId.get(cp.id)
    if (full) return full
    return {
      id: cp.id,
      user_id: 0,
      name: cp.name,
      city: cp.city ?? undefined,
      phone: cp.phone ?? undefined,
      email: cp.email ?? undefined,
      category: cp.category,
      source: cp.source as ProspectSource,
      confidence: cp.confidence,
      contacted: false,
    }
  })
})

/** A/B variant labels keyed by prospect id (campaign tab only). */
const campaignAbVariants: ComputedRef<Record<number, string | null | undefined>> = computed(
  (): Record<number, string | null | undefined> => {
    if (!campaign.value?.ab_template_id_b) return {}
    const variants: Record<number, string | null | undefined> = {}
    for (const prospect of campaign.value.prospects) {
      variants[prospect.id] = prospect.ab_variant
    }
    return variants
  },
)

const canLaunch: ComputedRef<boolean> = computed((): boolean =>
  isSms.value ? smsReady.value : settingsForm.value.template_id > 0,
)

/** Reason the launch button is disabled, shown as its tooltip (channel-aware). */
const launchDisabledReason: ComputedRef<string> = computed((): string =>
  isSms.value
    ? 'Configurez un expéditeur SMS dans Paramètres → Relance SMS'
    : 'Sélectionnez un template J1 dans la configuration',
)

const isCampaignActive: ComputedRef<boolean> = computed((): boolean => campaign.value?.status === 'active')

/** Metric cards for the stats strip. */
const metricCards: ComputedRef<Array<{ label: string; value: number | string; icon: string; color: string }>> =
  computed(() => {
    // SMS has no opens/clicks/replies: report send progress from the queue instead.
    if (isSms.value) {
      const c: { sent: number; pending: number; failed: number } = smsQueueCounts.value
      return [
        {
          label: 'Prospects',
          value: campaign.value?.prospects_count ?? 0,
          icon: 'i-lucide-users',
          color: 'text-[var(--app-ink)]',
        },
        { label: 'Envoyés', value: c.sent, icon: 'i-lucide-send', color: 'text-[var(--app-green)]' },
        { label: 'En attente', value: c.pending, icon: 'i-lucide-clock', color: 'text-[var(--app-accent-ink)]' },
        { label: 'Échecs', value: c.failed, icon: 'i-lucide-circle-x', color: 'text-[var(--app-red)]' },
      ]
    }
    const s: CampaignStats | null = stats.value
    if (!s) return []
    return [
      { label: 'Envoyés', value: s.total_emails_sent, icon: 'i-lucide-send', color: 'text-[var(--app-ink)]' },
      { label: 'Délivrés', value: s.emails_delivered, icon: 'i-lucide-circle-check', color: 'text-[var(--app-green)]' },
      { label: 'Ouverts', value: s.emails_opened, icon: 'i-lucide-mail-open', color: 'text-[var(--app-violet)]' },
      {
        label: 'Cliqués',
        value: s.emails_clicked,
        icon: 'i-lucide-mouse-pointer-click',
        color: 'text-[var(--app-ink)]',
      },
      { label: 'Répondus', value: s.emails_replied, icon: 'i-lucide-reply', color: 'text-[var(--app-green)]' },
      { label: 'Taux ouv.', value: `${s.open_rate}%`, icon: 'i-lucide-eye', color: 'text-[var(--app-accent-ink)]' },
      { label: 'Taux rép.', value: `${s.reply_rate}%`, icon: 'i-lucide-pointer', color: 'text-[var(--app-accent)]' },
    ]
  })

/** True when at least one variant captured a reply — replies then judge the A/B, not opens. */
const judgeByReplies: ComputedRef<boolean> = computed((): boolean =>
  (stats.value?.ab_stats ?? []).some((v: CampaignVariantStats): boolean => v.replied > 0),
)

/**
 * The metric a variant is judged on: reply rate once replies exist (the strongest,
 * proxy-proof signal), open rate before that.
 * @param v - Variant stats to evaluate.
 */
function judgeMetric(v: CampaignVariantStats): number {
  return judgeByReplies.value ? v.reply_rate : v.open_rate
}

const hasSignificantDiff: ComputedRef<boolean> = computed((): boolean => {
  const [first, second]: CampaignVariantStats[] = stats.value?.ab_stats ?? []
  if (!first || !second) return false
  return Math.abs(judgeMetric(first) - judgeMetric(second)) >= 10
})

const winnerMessage: ComputedRef<string> = computed((): string => {
  const [first, second]: CampaignVariantStats[] = stats.value?.ab_stats ?? []
  if (!first || !second) return ''
  const winner: CampaignVariantStats = judgeMetric(first) > judgeMetric(second) ? first : second
  return judgeByReplies.value
    ? `Variante ${winner.variant} en tête avec ${winner.reply_rate}% de réponses.`
    : `Variante ${winner.variant} en tête avec ${winner.open_rate}% d'ouverture.`
})

/** Detects whether the settings form differs from the persisted campaign. */
const settingsDirty: ComputedRef<boolean> = computed((): boolean => {
  if (!campaign.value) return false
  const c: CampaignDetailResponse = campaign.value
  const f: {
    template_id: number
    ab_template_id_b: number
    send_delay_minutes: number
    max_emails_per_day: number | null
    enable_ab: boolean
    behavior_personalized_followups: boolean
    include_video: boolean
    follow_ups: { template_id: number; delay_days: number }[]
  } = settingsForm.value
  if (f.template_id !== (c.template_id ?? 0)) return true
  if (f.send_delay_minutes !== c.send_delay_minutes) return true
  if ((f.max_emails_per_day ?? null) !== (c.max_emails_per_day ?? null)) return true
  if (f.behavior_personalized_followups !== c.behavior_personalized_followups) return true
  if (f.include_video !== c.include_video) return true
  if (f.enable_ab !== !!c.ab_template_id_b) return true
  if (f.enable_ab && f.ab_template_id_b !== (c.ab_template_id_b ?? 0)) return true
  if (f.follow_ups.length !== c.follow_ups.length) return true
  return f.follow_ups.some(
    (fu: { template_id: number; delay_days: number }, i: number) =>
      fu.template_id !== c.follow_ups[i]?.template_id || fu.delay_days !== c.follow_ups[i]?.delay_days,
  )
})

/**
 * Determine if a variant is the winner (>= 10pp lead on the judge metric:
 * reply rate once replies exist, open rate before that).
 * @param v - Variant stats to evaluate.
 */
function isWinner(v: CampaignVariantStats): boolean {
  const ab: CampaignVariantStats[] | null | undefined = stats.value?.ab_stats
  if (!ab || ab.length < 2 || !hasSignificantDiff.value) return false
  return ab.every(
    (other: CampaignVariantStats): boolean => other.variant === v.variant || judgeMetric(v) > judgeMetric(other),
  )
}

/**
 * Load the template an SMS campaign sends and render it for the campaign's first prospect.
 * @param detail - The campaign detail; its first prospect gives the real example.
 * @returns A promise that resolves once the preview is set.
 */
async function loadSmsPreview(detail: CampaignDetailResponse): Promise<void> {
  smsTemplates.value = await SmsService.listTemplates('first_contact').catch((): SmsTemplate[] => [])
  const fallback: SmsTemplate | null =
    smsTemplates.value.find((template: SmsTemplate): boolean => template.is_default) ?? smsTemplates.value[0] ?? null
  // Honour the campaign's chosen template; fall back to the library default.
  smsTemplate.value = detail.sms_template_key
    ? (smsTemplates.value.find((template: SmsTemplate): boolean => template.key === detail.sms_template_key) ??
      fallback)
    : fallback
  await renderSmsPreview(detail.prospects[0]?.id)
}

/**
 * Render the selected SMS template for a given prospect (real preview), else keep the sample rendering.
 * @param prospectId - The prospect whose demo personalises the preview.
 * @returns A promise resolved once the preview is set.
 */
async function renderSmsPreview(prospectId: number | undefined): Promise<void> {
  smsRenderedPreview.value = ''
  if (!smsTemplate.value || prospectId === undefined) return
  try {
    const preview: SmsTemplatePreview = await SmsService.previewTemplate(smsTemplate.value.key, prospectId)
    smsRenderedPreview.value = preview.body
  } catch {
    // No demo for that prospect yet: the sample rendering stands in.
  }
}

/**
 * Change the SMS template of the campaign, re-render the preview and persist the choice.
 * @param key - The chosen library template key.
 * @returns A promise resolved once the choice is saved.
 */
async function onChangeSmsTemplate(key: string): Promise<void> {
  const template: SmsTemplate | undefined = smsTemplates.value.find((t: SmsTemplate): boolean => t.key === key)
  if (!template) return
  smsTemplate.value = template
  await renderSmsPreview(campaign.value?.prospects?.[0]?.id)
  try {
    campaign.value = await CampaignService.updateSettings(campaignId.value, { sms_template_key: key })
    toast.success('Modèle SMS enregistré')
  } catch {
    toast.error("Erreur lors de l'enregistrement du modèle")
  }
}

/**
 * Load campaign, stats, queue, prospects and templates in parallel.
 */
async function loadAll(): Promise<void> {
  isLoading.value = true
  try {
    const [c, s, q, prospects, tpls]: [
      CampaignDetailResponse,
      CampaignStats | null,
      CampaignQueueResponse | null,
      Prospect[],
      TemplateOption[],
    ] = await Promise.all([
      CampaignService.get(campaignId.value),
      CampaignService.getStats(campaignId.value).catch((): null => null),
      CampaignService.getQueue(campaignId.value, { limit: 100 }).catch((): null => null),
      ProspectsService.listProspects(),
      ApiClient.get<TemplateOption[]>('/api/v1/email-templates').catch((): TemplateOption[] => []),
    ])
    campaign.value = c
    stats.value = s
    queueData.value = q
    allProspects.value = prospects
    templates.value = Array.isArray(tpls) ? tpls : []
    sendPolicy.value = await SendPolicyService.getSendPolicy().catch((): null => null)
    syncSettingsForm(c)
    if (c.channel === 'sms') {
      smsConfig.value = await SmsService.getConfig().catch((): null => null)
      await loadSmsPreview(c)
      if (activeTab.value === 'ab') activeTab.value = 'config'
    }
  } catch {
    toast.error('Campagne introuvable')
    router.push('/dashboard/campaigns')
  } finally {
    isLoading.value = false
  }
}

/**
 * Reload only the email templates feeding the config/follow-up selects.
 * @returns A promise resolved once the templates are reloaded.
 */
async function reloadTemplates(): Promise<void> {
  const tpls: TemplateOption[] = await ApiClient.get<TemplateOption[]>('/api/v1/email-templates').catch(
    (): TemplateOption[] => [],
  )
  templates.value = Array.isArray(tpls) ? tpls : []
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
    max_emails_per_day: c.max_emails_per_day ?? null,
    enable_ab: !!c.ab_template_id_b,
    behavior_personalized_followups: c.behavior_personalized_followups,
    include_video: c.include_video,
    follow_ups: c.follow_ups.map((fu: CampaignFollowUp) => ({
      template_id: fu.template_id,
      delay_days: fu.delay_days,
    })),
  }
}

/**
 * Reload only the queue (used by the refresh button and tab switch).
 */
async function loadQueue(): Promise<void> {
  queueData.value = await CampaignService.getQueue(campaignId.value, { limit: 100 })
}

/**
 * Reload only the live data (campaign, stats, queue), without the full-page spinner and without touching the settings form being edited.
 * @returns A promise resolved once the three blocks are refreshed.
 */
async function refreshLiveData(): Promise<void> {
  if (isRefreshing.value) return
  isRefreshing.value = true
  try {
    const [c, s, q]: [CampaignDetailResponse, CampaignStats | null, CampaignQueueResponse | null] = await Promise.all([
      CampaignService.get(campaignId.value),
      CampaignService.getStats(campaignId.value).catch((): null => null),
      CampaignService.getQueue(campaignId.value, { limit: 100 }).catch((): null => null),
    ])
    campaign.value = c
    stats.value = s
    queueData.value = q
  } catch {
    // Silent refresh: keep the last data on screen.
  } finally {
    isRefreshing.value = false
  }
}

/** Start the auto-refresh (idempotent); each tick only refreshes while the browser tab is visible. */
function startAutoRefresh(): void {
  if (autoRefreshTimer.value !== null) return
  autoRefreshTimer.value = setInterval((): void => {
    if (document.visibilityState === 'visible') refreshLiveData()
  }, AUTO_REFRESH_INTERVAL_MS)
}

/** Stop the auto-refresh if it is running. */
function stopAutoRefresh(): void {
  if (autoRefreshTimer.value === null) return
  clearInterval(autoRefreshTimer.value)
  autoRefreshTimer.value = null
}

/** Refresh as soon as the tab becomes visible again while the campaign is running, to avoid waiting for the next tick. */
function refreshOnTabVisible(): void {
  if (document.visibilityState === 'visible' && isCampaignActive.value) refreshLiveData()
}

/** Toggle the per-campaign daily cap: default to 1 send/day when enabling, clear it when disabling. */
function toggleDailyCap(): void {
  settingsForm.value.max_emails_per_day = settingsForm.value.max_emails_per_day === null ? 1 : null
}

/**
 * Persist the settings form to the backend.
 */
async function saveSettings(): Promise<void> {
  isSavingSettings.value = true
  try {
    const f: {
      template_id: number
      ab_template_id_b: number
      send_delay_minutes: number
      max_emails_per_day: number | null
      enable_ab: boolean
      behavior_personalized_followups: boolean
      include_video: boolean
      follow_ups: { template_id: number; delay_days: number }[]
    } = settingsForm.value
    const hasDailyCap: boolean = f.max_emails_per_day !== null && f.max_emails_per_day > 0
    const updated: CampaignDetailResponse = await CampaignService.updateSettings(campaignId.value, {
      template_id: f.template_id > 0 ? f.template_id : undefined,
      ab_template_id_b: f.enable_ab && f.ab_template_id_b > 0 ? f.ab_template_id_b : undefined,
      disable_ab: !f.enable_ab,
      send_delay_minutes: f.send_delay_minutes,
      max_emails_per_day: hasDailyCap ? f.max_emails_per_day : undefined,
      clear_max_emails_per_day: !hasDailyCap,
      behavior_personalized_followups: f.behavior_personalized_followups,
      include_video: f.include_video,
      follow_ups: f.follow_ups
        .filter((fu: { template_id: number; delay_days: number }) => fu.template_id > 0)
        .map((fu: { template_id: number; delay_days: number }, i: number) => ({
          template_id: fu.template_id,
          delay_days: fu.delay_days,
          position: i + 1,
        })),
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
    const result: LaunchCampaignResponse = await CampaignService.launch(campaignId.value)
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
    const result: { success: boolean; cancelled: number } = await CampaignService.pause(campaignId.value)
    toast.success(`Campagne en pause — ${result.cancelled} ${isSms.value ? 'SMS' : 'email(s)'} annulé(s)`)
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
    const result: { success: boolean; enqueued: number } = await CampaignService.resume(campaignId.value)
    toast.success(`Campagne reprise — ${result.enqueued} ${isSms.value ? 'SMS' : 'email(s)'} planifié(s)`)
    await loadAll()
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la reprise')
  }
}

/**
 * Update campaign name/description.
 */
/**
 * Permanently delete the campaign.
 */
async function handleDeleteCampaign(): Promise<void> {
  try {
    await CampaignService.delete(campaignId.value)
    toast.success('Campagne supprimée')
    router.push('/dashboard/campaigns')
  } catch {
    toast.error('Erreur lors de la suppression')
  }
}

/**
 * Open the drawer to attach existing prospects to this campaign.
 */
function openAddProspectsDrawer(): void {
  if (!campaign.value) return
  drawerStack.push({
    kind: 'campaign-prospects-picker',
    campaignId: campaignId.value,
    existingProspectIds: campaign.value.prospects.map((prospect: CampaignProspect): number => prospect.id),
  })
}

/**
 * Open the prospect detail drawer from the campaign prospects tab.
 * @param prospect - Prospect row that was clicked.
 */
function openProspectDrawer(prospect: Prospect): void {
  drawerStack.push({ kind: 'prospect', prospect })
}

/**
 * Relay a table row removal to the existing confirm flow.
 * @param prospect - Prospect to remove from the campaign.
 */
function startRemoveProspectFromRow(prospect: Prospect): void {
  startRemoveProspect(prospect.id)
}

/**
 * Toggle a single prospect in the campaign tab selection.
 * @param prospect - The prospect whose checkbox was toggled.
 */
function toggleCampaignProspectSelect(prospect: Prospect): void {
  const id: string = String(prospect.id)
  const index: number = campaignSelectedProspects.value.indexOf(id)
  if (index === -1) campaignSelectedProspects.value.push(id)
  else campaignSelectedProspects.value.splice(index, 1)
}

/**
 * Select or clear every prospect in the campaign tab table.
 * @param checked - True to select all visible rows, false to clear them.
 */
function toggleCampaignProspectSelectAll(checked: boolean): void {
  if (checked) {
    campaignSelectedProspects.value = campaignProspectRows.value.map((prospect: Prospect) => String(prospect.id))
  } else {
    campaignSelectedProspects.value = []
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
    campaign.value = await CampaignService.removeProspect(campaignId.value, prospectToRemoveId.value)
    // The removal cancels the prospect's pending send and re-dates the rest, so refresh the queue.
    await loadQueue()
    toast.success('Prospect retiré')
  } catch {
    toast.error('Erreur lors du retrait')
  } finally {
    prospectToRemoveId.value = null
  }
}

/**
 * Persist a drag & drop reorder of the campaign's prospects, then refresh the queue.
 * The list reorders optimistically; on a launched campaign the backend re-dates the pending
 * sends to the new order, so the queue is reloaded to show the new send days at once.
 * @param orderedProspectIds - The campaign's prospect ids in their new send order.
 */
async function handleReorderProspects(orderedProspectIds: number[]): Promise<void> {
  const current: CampaignDetailResponse | null = campaign.value
  if (!current) return
  const byId: Map<number, CampaignProspect> = new Map(
    current.prospects.map((prospect: CampaignProspect): [number, CampaignProspect] => [prospect.id, prospect]),
  )
  const reordered: CampaignProspect[] = orderedProspectIds
    .map((id: number): CampaignProspect | undefined => byId.get(id))
    .filter((prospect: CampaignProspect | undefined): prospect is CampaignProspect => prospect !== undefined)
  campaign.value = { ...current, prospects: reordered }
  try {
    campaign.value = await CampaignService.reorderProspects(campaignId.value, orderedProspectIds)
    await loadQueue()
  } catch {
    toast.error('Impossible de réordonner les prospects')
    await loadAll()
  }
}

/**
 * Open the confirm modal to cancel a pending queue item.
 * @param item - Queue item to cancel.
 */
function startCancelQueueItem(item: CampaignQueueItem): void {
  queueActionItem.value = item
  cancelQueueModal.value?.open()
}

/**
 * Cancel the targeted pending item after confirmation — it will not be sent.
 */
async function handleCancelQueueItem(): Promise<void> {
  const item: CampaignQueueItem | null = queueActionItem.value
  if (!item) return
  try {
    await CampaignService.cancelQueueItem(campaignId.value, item.id)
    toast.success('Envoi annulé')
    await loadQueue()
  } catch {
    toast.error("Impossible d'annuler l'envoi")
  } finally {
    queueActionItem.value = null
  }
}

/**
 * Open the confirm modal to re-send a skipped queue item.
 * @param item - Queue item to re-send.
 */
function startResendQueueItem(item: CampaignQueueItem): void {
  queueActionItem.value = item
  resendQueueModal.value?.open()
}

/**
 * Re-queue the targeted skipped item after confirmation — the worker sends it within ~1 min.
 */
async function handleResendQueueItem(): Promise<void> {
  const item: CampaignQueueItem | null = queueActionItem.value
  if (!item) return
  try {
    await CampaignService.resendQueueItem(campaignId.value, item.id)
    toast.success('Email replanifié — envoi imminent')
    await loadQueue()
  } catch {
    toast.error("Impossible de renvoyer l'email")
  } finally {
    queueActionItem.value = null
  }
}

/** Open the send-policy drawer, where the effective cadence is set. */
function openSendPolicyDrawer(): void {
  drawerStack.push({ kind: 'send-policy' })
}

/** Open the campaign drawer in edit mode, on the persistent stack. */
function openEditDrawer(): void {
  if (!campaign.value) return
  drawerStack.push({ kind: 'campaign-form', mode: 'edit', campaign: campaign.value })
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

watch(activeTab, (tab: string): void => {
  if (tab === 'queue') loadQueue()
})

// La campagne vient d'être renommée depuis son drawer.
watch((): number => drawerStack.campaignsRefreshCounter, loadAll)

// Soft auto-refresh: starts while the campaign is running, stops otherwise.
watch(isCampaignActive, (active: boolean): void => {
  if (active) startAutoRefresh()
  else stopAutoRefresh()
})

/** Sending identity — powers the « arrêt automatique à la réponse » assurance line. */
const sendingIdentity: Ref<SendingIdentityResponse | null> = ref(null)

/**
 * Whether prospect replies are captured for this user's sends (Resend provider
 * + platform inbound domain active) — the follow-up auto-stop promise only
 * holds in that case, so the assurance line hides otherwise.
 */
const hasReplyCapture: ComputedRef<boolean> = computed(
  (): boolean => Boolean(sendingIdentity.value?.reply_capture_enabled) && sendingIdentity.value?.provider === 'resend',
)

onMounted((): void => {
  loadAll()
  // Best-effort: the assurance line simply stays hidden if this fails.
  SettingsService.getSendingIdentity()
    .then((identity: SendingIdentityResponse): void => {
      sendingIdentity.value = identity
    })
    .catch((): void => {})
  document.addEventListener('visibilitychange', refreshOnTabVisible)
})

onUnmounted((): void => {
  stopAutoRefresh()
  document.removeEventListener('visibilitychange', refreshOnTabVisible)
})
</script>
