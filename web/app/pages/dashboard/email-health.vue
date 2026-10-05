<template>
  <div class="space-y-8">
    <UiPageHeader
      eyebrow="Prospection"
      title="Santé email"
      description="Délivrabilité, réputation du domaine et signaux spam de votre adresse d'envoi — tout ce qui peut expliquer un silence des prospects."
    >
      <template #actions>
        <div class="flex overflow-hidden rounded-lg border border-[var(--app-line)]">
          <button
            v-for="preset in PERIODS"
            :key="preset"
            type="button"
            class="h-10.5 flex-1 px-3 text-sm font-medium whitespace-nowrap transition-colors @2xl:pointer-fine:h-8 @2xl:pointer-fine:flex-none @2xl:pointer-fine:text-xs"
            :class="
              period === preset
                ? 'bg-[var(--app-ink)] text-[var(--app-surface)]'
                : 'bg-[var(--app-surface)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
            "
            @click="changePeriod(preset)"
          >
            {{ preset }} j
          </button>
        </div>
        <button
          type="button"
          class="app-btn-secondary h-11 px-3 text-sm whitespace-nowrap @2xl:pointer-fine:h-8 @2xl:pointer-fine:text-xs"
          :disabled="isLoading"
          @click="load"
        >
          <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
      </template>
    </UiPageHeader>

    <div
      v-if="loadError"
      class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-sm text-[var(--app-red)]"
    >
      {{ loadError }}
    </div>

    <div
      v-if="overview && overview.accounts.length === 0"
      class="app-card flex flex-wrap items-center justify-between gap-3 p-4"
    >
      <p class="flex items-center gap-2 text-sm text-[var(--app-ink)]">
        <UIcon name="i-lucide-mail-warning" class="h-4 w-4 shrink-0 text-[var(--app-accent-ink)]" />
        Aucun compte d'envoi configuré — l'authentification du domaine et le testeur ont besoin d'une adresse
        d'expédition.
      </p>
      <NuxtLink to="/dashboard/settings/sending" class="app-btn-secondary h-8 px-3 text-xs">
        Configurer un compte
      </NuxtLink>
    </div>

    <section v-if="overview">
      <div class="mb-3 flex items-baseline justify-between">
        <h2 class="text-sm font-semibold text-[var(--app-ink)]">Signaux de santé</h2>
        <p class="text-xs text-[var(--app-ink-soft)] tabular-nums">
          {{ formatInt(overview.totals.sent) }} envoyés · {{ formatInt(overview.totals.delivered) }} délivrés ·
          {{ formatInt(overview.totals.opened) }} ouverts · {{ formatInt(overview.totals.replied ?? 0) }} répondus sur
          {{ period }} jours
        </p>
      </div>
      <div class="grid grid-cols-2 gap-3 sm:gap-4 @4xl:grid-cols-4">
        <EmailHealthSignalTile
          v-for="signal in overview.signals"
          :key="signal.key"
          :label="signal.label"
          :value="formatRate(signal.value)"
          :unit="signal.unit"
          :status="signal.status"
          :hint="signal.hint"
          :sparkline="sparklineFor(signal.key)"
        />
      </div>
      <p class="mt-2 flex items-center gap-1.5 text-[11px] text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-info" class="h-3 w-3 shrink-0" />
        Le taux d'ouverture ({{ formatRate(overview.totals.open_rate) }} %) est indicatif : Apple Mail le gonfle
        artificiellement en préchargeant les images. Le taux de réponse ({{
          formatRate(overview.totals.reply_rate ?? 0)
        }}
        %) est l'indicateur fiable — une réponse humaine ne se simule pas.
      </p>
    </section>

    <section v-if="trendDays.length > 0" class="grid grid-cols-1 gap-6 @3xl:grid-cols-2">
      <div class="app-card p-5">
        <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Volume d'envoi</h2>
        <EmailHealthVolumeChart
          :labels="trendLabels"
          :sent="sentValues"
          :delivered="deliveredValues"
          :opened="openedValues"
        />
      </div>
      <div class="app-card p-5">
        <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Taux critiques</h2>
        <EmailHealthTrendChart
          :labels="trendLabels"
          :series="criticalSeries"
          :thresholds="CRITICAL_THRESHOLDS"
          unit="%"
        />
      </div>
    </section>

    <section v-if="providers.length > 0" class="app-card p-5 md:p-6">
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Par fournisseur destinataire</h2>
      <p class="mt-1 mb-4 text-xs text-[var(--app-ink-soft)]">
        Orange, Free ou SFR n'ont pas d'outil de réputation public — mais si un fournisseur rejette vos emails ou ne les
        ouvre jamais alors que les autres répondent, c'est qu'il vous filtre.
      </p>
      <div class="divide-y divide-[var(--app-line-soft)]">
        <div
          v-for="provider in providers"
          :key="provider.provider"
          class="grid grid-cols-2 items-center gap-x-4 gap-y-2 py-3 first:pt-0 last:pb-0 @3xl:grid-cols-[1.4fr_repeat(4,1fr)_auto]"
        >
          <div class="col-span-2 @3xl:col-span-1">
            <p class="text-sm font-medium text-[var(--app-ink)]">{{ provider.label }}</p>
            <p v-if="provider.note" class="mt-0.5 text-[11px]" :style="{ color: statusColor(provider.status) }">
              {{ provider.note }}
            </p>
          </div>
          <div v-for="metric in providerMetrics(provider)" :key="metric.label">
            <p class="text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">{{ metric.label }}</p>
            <p class="mt-0.5 text-sm font-semibold tabular-nums" :style="{ color: metric.color }">
              {{ metric.value }}
            </p>
            <div class="mt-1 h-1 w-full max-w-[90px] overflow-hidden rounded-full bg-[var(--app-surface-2)]">
              <div
                class="h-full rounded-full"
                :style="{ width: `${Math.min(metric.barPct, 100)}%`, backgroundColor: metric.color }"
              ></div>
            </div>
          </div>
          <span
            class="justify-self-start rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase @3xl:justify-self-end"
            :style="{ color: statusColor(provider.status), backgroundColor: statusSoft(provider.status) }"
          >
            {{ statusLabel(provider.status) }}
          </span>
        </div>
      </div>
    </section>

    <section class="app-card p-5 md:p-6">
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Réputation Gmail</h2>
      <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
        Vue officielle de Gmail sur votre domaine d'envoi — complémentaire aux stats Resend ci-dessus.
      </p>

      <template v-if="!postmasterConnection?.connected">
        <UiCollapsibleCard
          class="mt-4"
          icon="i-lucide-mail-check"
          title="Comment brancher la réputation Gmail"
          suffix="gratuit"
        >
          <div class="space-y-6 px-4 py-5">
            <ol class="space-y-4">
              <li v-for="(step, index) in postmasterWorkflowSteps" :key="step.title" class="flex items-start gap-3">
                <span
                  class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] bg-[var(--app-bg)] text-[11px] font-bold text-[var(--app-ink)]"
                >
                  {{ index + 1 }}
                </span>
                <div class="min-w-0 pt-0.5">
                  <p class="text-sm font-medium text-[var(--app-ink)]">{{ step.title }}</p>
                  <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ step.detail }}</p>
                </div>
              </li>
            </ol>
            <p class="text-muted flex items-start gap-2 text-xs leading-relaxed">
              <UIcon name="i-lucide-circle-alert" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
              <span>
                Utilisez le <strong class="font-semibold text-[var(--app-ink)]">même compte Google</strong> pour
                Postmaster et pour la connexion ci-dessous.
              </span>
            </p>
          </div>
        </UiCollapsibleCard>

        <div
          v-if="postmasterConnection?.oauth_available"
          class="mt-6 flex flex-col items-center gap-4 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-10 text-center"
        >
          <UiGoogleLogo class="h-11 w-11" />
          <div class="space-y-1.5">
            <h3 class="text-base font-semibold text-[var(--app-ink)]">Connecter Google Postmaster</h3>
            <p class="text-muted mx-auto max-w-md text-sm leading-relaxed">
              Un clic pour autoriser la lecture de votre réputation Gmail. La connexion reste active — pas besoin de
              revenir ici à chaque visite.
            </p>
          </div>
          <button type="button" class="btn-primary" :disabled="isConnectingPostmaster" @click="connectPostmaster">
            <UiGoogleLogo class="h-4 w-4" />
            {{ isConnectingPostmaster ? 'Redirection…' : 'Connecter avec Google' }}
          </button>
        </div>
        <p v-else class="mt-4 text-sm text-[var(--app-ink-soft)]">
          La connexion Google n'est pas disponible sur ce serveur — contactez l'administrateur.
        </p>
      </template>

      <template v-else>
        <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2 text-sm text-[var(--app-ink)]">
            <UiGoogleLogo class="h-5 w-5" />
            <span>
              Connecté :
              <span class="font-medium">{{ postmasterConnection.google_email }}</span>
            </span>
          </div>
          <button
            type="button"
            class="btn-secondary text-xs"
            :disabled="isDisconnectingPostmaster"
            @click="disconnectPostmaster"
          >
            {{ isDisconnectingPostmaster ? 'Déconnexion…' : 'Déconnecter' }}
          </button>
        </div>

        <div v-for="postmaster in postmasterDomains" :key="postmaster.domain" class="mt-6 space-y-4">
          <h3 class="text-xs font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
            Domaine
            <span class="font-mono text-[var(--app-accent-ink)] normal-case">{{ postmaster.domain }}</span>
          </h3>

          <p v-if="postmaster.error" class="text-sm text-[var(--app-red)]">{{ postmaster.error }}</p>

          <UiCallout v-else-if="postmaster.domain_not_found" variant="warning">
            Ce domaine n'apparaît pas dans votre Postmaster Tools. Ajoutez-le sur
            <a href="https://postmaster.google.com" target="_blank" rel="noopener" class="underline">
              postmaster.google.com</a
            >
            avec le compte <strong>{{ postmasterConnection.google_email }}</strong
            >, puis validez-le par DNS.
          </UiCallout>

          <div v-else class="space-y-5">
            <div class="flex flex-wrap items-center gap-6">
              <div>
                <p class="text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">Réputation actuelle</p>
                <p
                  class="mt-1 text-xl font-bold"
                  :style="{ color: reputationColor(postmaster.latest?.domain_reputation ?? null) }"
                >
                  {{ reputationLabel(postmaster.latest?.domain_reputation ?? null) }}
                </p>
              </div>
              <div>
                <p class="text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">Taux de spam vu par Gmail</p>
                <p class="mt-1 text-xl font-bold text-[var(--app-ink)] tabular-nums">
                  {{ formatSpamRatio(postmaster.latest?.user_reported_spam_ratio ?? null) }}
                </p>
              </div>
              <div v-for="auth in postmasterAuthRatios(postmaster)" :key="auth.label">
                <p class="text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">{{ auth.label }}</p>
                <p class="mt-1 text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ auth.value }}</p>
              </div>
            </div>
            <div>
              <p class="mb-2 text-xs font-medium text-[var(--app-ink-soft)]">Historique de réputation</p>
              <EmailHealthReputationTimeline :days="reputationDays(postmaster)" />
            </div>
            <p v-if="(postmaster.days ?? []).length === 0" class="text-xs text-[var(--app-ink-soft)]">
              Google n'a pas encore publié de données — il faut un volume d'envoi régulier vers Gmail (souvent quelques
              centaines d'emails) avant que Postmaster remonte des chiffres.
            </p>
          </div>
        </div>

        <p v-if="postmasterDomains.length === 0" class="mt-4 text-sm text-[var(--app-ink-soft)]">
          Aucun domaine d'envoi détecté — configurez d'abord votre méthode d'envoi dans les paramètres.
        </p>
      </template>
    </section>

    <section class="app-card p-5 md:p-6">
      <div class="flex items-baseline justify-between gap-3">
        <h2 class="text-sm font-semibold text-[var(--app-ink)]">Score anti-spam de vos modèles</h2>
        <span v-if="isScoringTemplates" class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
          <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" /> Analyse en cours…
        </span>
      </div>
      <p class="mt-1 mb-5 text-xs text-[var(--app-ink-soft)]">
        Chaque modèle actif est analysé automatiquement à l'ouverture de la page — aucun email n'est envoyé. Note sur 5,
        comme à l'école : 5/5 = aucun signal spam · en dessous de 3/5 : à retravailler · 0/5 : classé spam par la
        plupart des filtres.
      </p>

      <div
        v-if="!isScoringTemplates && templateGroups.every((group) => group.items.length === 0)"
        class="py-6 text-center text-sm text-[var(--app-ink-soft)]"
      >
        Aucun modèle d'email actif à analyser.
      </div>

      <div v-else class="space-y-6">
        <div v-for="group in templateGroups" :key="group.key">
          <template v-if="group.items.length > 0">
            <h3 class="app-label mb-2">{{ group.label }}</h3>
            <div class="divide-y divide-[var(--app-line-soft)] rounded-xl border border-[var(--app-line)]">
              <div v-for="(score, index) in group.items" :key="score.id">
                <button
                  type="button"
                  class="grid w-full cursor-pointer grid-cols-[1fr_auto_auto] items-center gap-x-4 gap-y-1 px-4 py-3 text-left transition-colors hover:bg-[var(--app-bg)]"
                  @click="toggleTemplate(score.id)"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium text-[var(--app-ink)]">
                      {{ score.name }}
                      <span
                        v-if="index === 0 && group.showBest && score.spamassassin.available"
                        class="ml-1.5 rounded-full bg-[var(--app-green-soft)] px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-[var(--app-green)] uppercase"
                      >
                        Meilleur score
                      </span>
                    </p>
                    <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">{{ score.subject }}</p>
                    <p v-if="score.issues.length > 0" class="mt-1 flex flex-wrap gap-1">
                      <span
                        v-for="issue in score.issues.slice(0, 3)"
                        :key="issue.key"
                        class="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                        :style="{ color: statusColor(issue.status), backgroundColor: statusSoft(issue.status) }"
                      >
                        {{ issue.label }}
                      </span>
                      <span v-if="score.issues.length > 3" class="text-[10px] text-[var(--app-ink-soft)]">
                        +{{ score.issues.length - 3 }}
                      </span>
                    </p>
                    <p v-else-if="score.spamassassin.available" class="mt-1 text-[10px] text-[var(--app-green)]">
                      Aucun point bloquant
                    </p>
                  </div>
                  <div class="text-right">
                    <template v-if="score.spamassassin.available">
                      <p class="text-xl font-bold tabular-nums" :style="{ color: statusColor(combinedStatus(score)) }">
                        {{ formatNote(score.spamassassin.score ?? 0)
                        }}<span class="text-xs font-medium text-[var(--app-ink-soft)]"> / 5</span>
                      </p>
                      <p class="text-[10px] text-[var(--app-ink-soft)]">
                        {{ scoreVerdict(combinedStatus(score)) }}
                      </p>
                    </template>
                    <p v-else class="max-w-[140px] text-[10px] text-[var(--app-red)]">
                      {{ score.spamassassin.error }}
                    </p>
                  </div>
                  <UIcon
                    :name="expandedTemplateId === score.id ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
                    class="h-4 w-4 text-[var(--app-ink-soft)]"
                  />
                </button>

                <div
                  v-if="expandedTemplateId === score.id"
                  class="border-t border-[var(--app-line-soft)] bg-[var(--app-bg)] px-4 py-3"
                >
                  <div class="grid grid-cols-1 gap-4 @3xl:grid-cols-2">
                    <div>
                      <p class="mb-1.5 text-[11px] font-semibold text-[var(--app-ink)]">Checklist cold email</p>
                      <ul class="space-y-1.5">
                        <li v-for="check in score.checks" :key="check.key" class="flex items-start gap-2 text-[11px]">
                          <UIcon
                            :name="statusIcon(check.status)"
                            class="mt-0.5 h-3.5 w-3.5 shrink-0"
                            :style="{ color: statusColor(check.status) }"
                          />
                          <span class="text-[var(--app-ink-soft)]">
                            <span class="font-medium text-[var(--app-ink)]">{{ check.label }}</span> —
                            {{ check.detail }}
                          </span>
                        </li>
                      </ul>
                    </div>
                    <div v-if="topRulesFor(score).length > 0">
                      <p class="mb-1.5 text-[11px] font-semibold text-[var(--app-ink)]">Règles anti-spam déclenchées</p>
                      <ul class="space-y-1">
                        <li
                          v-for="rule in topRulesFor(score)"
                          :key="rule.description ?? ''"
                          class="flex items-start justify-between gap-3 text-[11px] text-[var(--app-ink-soft)]"
                        >
                          <span>{{ rule.description }}</span>
                          <span class="shrink-0 font-mono tabular-nums">{{ rule.score }}</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </section>

    <section class="app-card p-5 md:p-6">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Journal des incidents</h2>
      <div v-if="incidents.length === 0" class="py-6 text-center text-sm text-[var(--app-ink-soft)]">
        Aucun email rejeté, signalement spam ou échec récent — rien à signaler.
      </div>
      <div v-else class="md:overflow-x-auto">
        <table class="dlh-card-table w-full min-w-[640px] text-sm">
          <thead>
            <tr class="border-b border-[var(--app-line)] text-left">
              <th class="py-2 pr-3 text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">Date</th>
              <th class="py-2 pr-3 text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">Type</th>
              <th class="py-2 pr-3 text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">
                Destinataire
              </th>
              <th class="py-2 text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">Motif</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="incident in incidents"
              :key="incident.id"
              class="border-b border-[var(--app-line-soft)] last:border-b-0"
            >
              <td data-label="Date" class="py-2 pr-3 whitespace-nowrap text-[var(--app-ink-soft)] tabular-nums">
                {{ formatNumericDayMonthTime(incident.at) || '—' }}
              </td>
              <td data-label="Type" class="py-2 pr-3">
                <span
                  class="rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
                  :style="{
                    color: statusColor(incidentTone(incident.kind)),
                    backgroundColor: statusSoft(incidentTone(incident.kind)),
                  }"
                >
                  {{ incidentLabel(incident.kind) }}
                </span>
              </td>
              <td data-label="Destinataire" class="py-2 pr-3 font-medium text-[var(--app-ink)]">
                {{ incident.recipient_email }}
              </td>
              <td
                data-label="Motif"
                class="max-w-[280px] truncate py-2 text-xs text-[var(--app-ink-soft)]"
                :title="incident.error_message ?? ''"
              >
                {{ incident.error_message || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="overview && overview.accounts.length > 0" class="app-card p-5 md:p-6">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Comptes d'envoi</h2>
      <div class="md:overflow-x-auto">
        <table class="dlh-card-table w-full min-w-[640px] text-sm">
          <thead>
            <tr class="border-b border-[var(--app-line)] text-left">
              <th class="py-2 pr-3 text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">
                Compte
              </th>
              <th
                class="py-2 pr-3 text-right text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase"
              >
                Envoyés
              </th>
              <th
                class="py-2 pr-3 text-right text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase"
              >
                Délivrés
              </th>
              <th
                class="py-2 pr-3 text-right text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase"
              >
                Rejetés
              </th>
              <th class="py-2 text-right text-[10px] font-medium tracking-wide text-[var(--app-ink-soft)] uppercase">
                Signalés spam
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="account in overview.accounts"
              :key="account.id"
              class="border-b border-[var(--app-line-soft)] last:border-b-0"
            >
              <td class="py-2 pr-3">
                <p class="font-medium text-[var(--app-ink)]">
                  {{ account.email }}
                  <span
                    v-if="account.is_default"
                    class="ml-1.5 rounded-full bg-[var(--app-surface-2)] px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase"
                  >
                    défaut
                  </span>
                </p>
                <p class="text-[11px] text-[var(--app-ink-soft)]">{{ accountTypeLabel(account.account_type) }}</p>
              </td>
              <td data-label="Envoyés" class="py-2 pr-3 text-right text-[var(--app-ink)] tabular-nums">
                {{ formatInt(account.stats.sent) }}
              </td>
              <td data-label="Délivrés" class="py-2 pr-3 text-right text-[var(--app-ink)] tabular-nums">
                {{ formatInt(account.stats.delivered) }}
                <span class="text-[11px] text-[var(--app-ink-soft)]"
                  >({{ formatRate(account.stats.delivery_rate) }} %)</span
                >
              </td>
              <td
                data-label="Rejetés"
                class="py-2 pr-3 text-right tabular-nums"
                :style="{ color: rateColor(account.stats.bounce_rate, 2, 5) }"
              >
                {{ formatRate(account.stats.bounce_rate) }} %
              </td>
              <td
                data-label="Signalés spam"
                class="py-2 text-right tabular-nums"
                :style="{ color: rateColor(account.stats.complaint_rate, 0.1, 0.3) }"
              >
                {{ formatRate(account.stats.complaint_rate) }} %
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-for="domain in dnsDomains" :key="domain.domain" class="app-card p-5 md:p-6">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-[var(--app-ink)]">
          Authentification du domaine <span class="font-mono text-[var(--app-accent-ink)]">{{ domain.domain }}</span>
        </h2>
      </div>
      <div class="grid grid-cols-1 gap-3 @sm:grid-cols-2 @5xl:grid-cols-5">
        <div
          v-for="check in dnsChecks(domain)"
          :key="check.key"
          class="rounded-xl border bg-[var(--app-bg)] p-3.5"
          :style="{ borderColor: check.status === 'ok' ? 'var(--app-line)' : statusColor(check.status) }"
        >
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold text-[var(--app-ink)]">{{ check.label }}</p>
            <UIcon :name="statusIcon(check.status)" class="h-4 w-4" :style="{ color: statusColor(check.status) }" />
          </div>
          <p class="mt-1.5 text-[11px] leading-snug text-[var(--app-ink-soft)]">{{ check.detail }}</p>
          <p
            v-if="check.record"
            class="mt-2 truncate rounded bg-[var(--app-surface-2)] px-1.5 py-1 font-mono text-[10px] text-[var(--app-ink-soft)]"
            :title="check.record"
          >
            {{ check.record }}
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import { formatNumericDayMonthTime } from '~/utils/date'
import type { TemplateScoreGroup } from '~/types/EmailHealthPage'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type {
  EmailDnsCheck,
  EmailDnsDomain,
  EmailHealthIncident,
  EmailHealthOverview,
  EmailHealthProvider,
  EmailHealthTrendDay,
  PostmasterConnection,
  PostmasterDay,
  PostmasterDomain,
  PostmasterResponse,
  SpamLocalCheck,
  TemplateScore,
  TemplateScoresResponse,
} from '~/services/emailHealthService'
import { EmailHealthService } from '~/services/emailHealthService'
import type { EmailHealthChartSeries, EmailHealthChartThreshold } from '~/types/EmailHealthTrendChart'
import type { UseToastReturn } from '~/types/Composables'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const toast: UseToastReturn = useToast()
const route: ReturnType<typeof useRoute> = useRoute()
const router: ReturnType<typeof useRouter> = useRouter()

/** Supported rolling windows (days). */
const PERIODS: number[] = [7, 30, 90]

/** Threshold guides of the critical-rates chart. */
const CRITICAL_THRESHOLDS: EmailHealthChartThreshold[] = [
  { value: 0.3, label: 'Plafond signalements spam Gmail/Yahoo (0,3 %)', tone: 'red' },
  { value: 2, label: "Plafond sain d'emails rejetés (2 %)", tone: 'amber' },
]

const period: Ref<number> = ref(30)
const isLoading: Ref<boolean> = ref(false)
const loadError: Ref<string | null> = ref(null)
const overview: Ref<EmailHealthOverview | null> = ref(null)
const trendDays: Ref<EmailHealthTrendDay[]> = ref([])
const providers: Ref<EmailHealthProvider[]> = ref([])
const incidents: Ref<EmailHealthIncident[]> = ref([])
const dnsDomains: Ref<EmailDnsDomain[]> = ref([])
const postmasterConnection: Ref<PostmasterConnection | null> = ref(null)
const postmasterDomains: Ref<PostmasterDomain[]> = ref([])
const isConnectingPostmaster: Ref<boolean> = ref(false)
const isDisconnectingPostmaster: Ref<boolean> = ref(false)

const templateScores: Ref<TemplateScoresResponse | null> = ref(null)
const isScoringTemplates: Ref<boolean> = ref(false)
const expandedTemplateId: Ref<number | null> = ref(null)

/** Primary sending domain label for the Postmaster setup guide. */
const primarySendingDomain: ComputedRef<string> = computed((): string => {
  const fromPostmaster: string | undefined = postmasterDomains.value[0]?.domain
  if (fromPostmaster) return fromPostmaster
  const fromDns: string | undefined = dnsDomains.value[0]?.domain
  if (fromDns) return fromDns
  return 'votre-domaine.fr'
})

/** Numbered steps for the Postmaster onboarding card. */
const postmasterWorkflowSteps: ComputedRef<{ title: string; detail: string }[]> = computed(
  (): { title: string; detail: string }[] => [
    {
      title: `Vérifiez ${primarySendingDomain.value} sur Postmaster Tools`,
      detail:
        "Sur postmaster.google.com, ajoutez votre domaine d'envoi et posez l'enregistrement TXT DNS demandé par Google. Comptez quelques minutes pour la validation.",
    },
    {
      title: 'Connectez le même compte Google',
      detail:
        "Cliquez sur le bouton ci-dessous avec le compte Google qui possède ce domaine dans Postmaster. La connexion reste active — vous n'aurez pas à recommencer à chaque visite.",
    },
  ],
)

/** ISO dates of the trend series. */
const trendLabels: ComputedRef<string[]> = computed((): string[] =>
  trendDays.value.map((day: EmailHealthTrendDay): string => day.date),
)

/** Daily "sent" counts for the volume chart. */
const sentValues: ComputedRef<number[]> = computed((): number[] =>
  trendDays.value.map((day: EmailHealthTrendDay): number => day.sent),
)
/** Daily "delivered" counts for the volume chart. */
const deliveredValues: ComputedRef<number[]> = computed((): number[] =>
  trendDays.value.map((day: EmailHealthTrendDay): number => day.delivered),
)
/** Daily "opened" counts for the volume chart. */
const openedValues: ComputedRef<number[]> = computed((): number[] =>
  trendDays.value.map((day: EmailHealthTrendDay): number => day.opened),
)

/** Series of the critical-rates chart (bounce % + complaint %). */
const criticalSeries: ComputedRef<EmailHealthChartSeries[]> = computed((): EmailHealthChartSeries[] => [
  {
    key: 'bounce_rate',
    label: 'Rejetés',
    tone: 'amber',
    values: trendDays.value.map((day: EmailHealthTrendDay): number => day.bounce_rate),
  },
  {
    key: 'complaint_rate',
    label: 'Signalés spam',
    tone: 'red',
    values: trendDays.value.map((day: EmailHealthTrendDay): number => day.complaint_rate),
  },
])

/** Template scores grouped and sorted best-first (unavailable last). */
const templateGroups: ComputedRef<TemplateScoreGroup[]> = computed((): TemplateScoreGroup[] => {
  /**
   * Sort scores ascending (best anti-spam score first), unscored at the end.
   * @param items - Scores of one group.
   * @returns The sorted copy.
   */
  const sorted: (items: TemplateScore[]) => TemplateScore[] = (items: TemplateScore[]): TemplateScore[] =>
    [...items].sort((a: TemplateScore, b: TemplateScore): number => {
      if (a.spamassassin.available !== b.spamassassin.available) return a.spamassassin.available ? -1 : 1
      return (a.spamassassin.score ?? 99) - (b.spamassassin.score ?? 99)
    })
  /**
   * Whether at least two scored templates of the group have different scores.
   * @param items - Scores of one group.
   * @returns True when a "best" actually exists.
   */
  const hasDistinctScores: (items: TemplateScore[]) => boolean = (items: TemplateScore[]): boolean => {
    const values: number[] = items
      .filter((item: TemplateScore): boolean => item.spamassassin.available)
      .map((item: TemplateScore): number => item.spamassassin.score ?? 0)
    return values.length > 1 && new Set(values).size > 1
  }
  const initial: TemplateScore[] = sorted(templateScores.value?.initial ?? [])
  const followUp: TemplateScore[] = sorted(templateScores.value?.follow_up ?? [])
  return [
    { key: 'initial', label: 'Premiers contacts', items: initial, showBest: hasDistinctScores(initial) },
    { key: 'follow_up', label: 'Relances', items: followUp, showBest: hasDistinctScores(followUp) },
  ]
})

/**
 * Row status combining the anti-spam score with the checklist findings —
 * a clean score with warning checks must not display as fully « Sain ».
 * @param score - The template score entry.
 * @returns The worst of both statuses.
 */
function combinedStatus(score: TemplateScore): 'ok' | 'warn' | 'danger' {
  const rank: Record<string, number> = { ok: 0, warn: 1, danger: 2 }
  const statuses: string[] = [
    score.spamassassin.status ?? 'ok',
    ...score.issues.map((issue: SpamLocalCheck): string => issue.status),
  ]
  const worst: string = statuses.reduce(
    (acc: string, status: string): string => ((rank[status] ?? 0) > (rank[acc] ?? 0) ? status : acc),
    'ok',
  )
  return worst as 'ok' | 'warn' | 'danger'
}

/**
 * Turn a raw SpamAssassin score into a school-style note out of 5 (higher is
 * better): a clean template (score 0) shows 5/5, a spammy one (score ≥5) shows
 * 0/5. The real score still drives the sort order and status color.
 * @param score - Raw SpamAssassin score (lower = cleaner).
 * @returns Localized note (0–5), at most one decimal.
 */
function formatNote(score: number): string {
  const note: number = 5 - Math.min(Math.max(score, 0), 5)
  return note.toLocaleString('fr-FR', { maximumFractionDigits: 1 })
}

/**
 * Anti-spam rules that actually raised a template's score, heaviest first.
 * @param score - The template score entry.
 * @returns Up to 6 triggered rules.
 */
function topRulesFor(score: TemplateScore): { score: string | number | null; description: string | null }[] {
  return [...(score.spamassassin.rules ?? [])]
    .filter(
      (rule: { score: string | number | null; description: string | null }): boolean => Number(rule.score ?? 0) > 0,
    )
    .sort(
      (a: { score: string | number | null }, b: { score: string | number | null }): number =>
        Number(b.score ?? 0) - Number(a.score ?? 0),
    )
    .slice(0, 6)
}

/**
 * One-word verdict under a template's score.
 * @param status - Score status.
 * @returns The French verdict.
 */
function scoreVerdict(status: string): string {
  if (status === 'ok') return 'Sain'
  if (status === 'warn') return 'À surveiller'
  return 'Risque spam'
}

/**
 * Expand/collapse a template's detail panel.
 * @param templateId - The template id.
 */
function toggleTemplate(templateId: number): void {
  expandedTemplateId.value = expandedTemplateId.value === templateId ? null : templateId
}

/**
 * Daily sparkline values matching one health signal.
 * @param key - Signal key.
 * @returns Daily values (empty when the signal has no daily series).
 */
function sparklineFor(key: string): number[] {
  const days: EmailHealthTrendDay[] = trendDays.value
  if (key === 'complaint_rate') return days.map((day: EmailHealthTrendDay): number => day.complaint_rate)
  if (key === 'bounce_rate') return days.map((day: EmailHealthTrendDay): number => day.bounce_rate)
  if (key === 'delivery_rate') return days.map((day: EmailHealthTrendDay): number => day.delivery_rate)
  return []
}

/**
 * The four metric cells of one provider row.
 * @param provider - Provider entry.
 * @returns Label/value/bar definitions.
 */
function providerMetrics(
  provider: EmailHealthProvider,
): { label: string; value: string; barPct: number; color: string }[] {
  return [
    {
      label: 'Envoyés',
      value: formatInt(provider.sent),
      barPct: overview.value && overview.value.totals.sent > 0 ? (provider.sent / overview.value.totals.sent) * 100 : 0,
      color: 'var(--app-ink)',
    },
    {
      label: 'Délivrés',
      value: `${formatRate(provider.delivery_rate)} %`,
      barPct: provider.delivery_rate,
      color: 'var(--app-green)',
    },
    {
      label: 'Ouverts',
      value: `${formatRate(provider.open_rate)} %`,
      barPct: provider.open_rate,
      color: 'var(--app-blue)',
    },
    {
      label: 'Rejetés',
      value: `${formatRate(provider.bounce_rate)} %`,
      barPct: provider.bounce_rate,
      color: rateColor(provider.bounce_rate, 2, 5),
    },
  ]
}

/**
 * The five DNS check cards of one domain.
 * @param domain - DNS payload of the domain.
 * @returns Card definitions in display order.
 */
function dnsChecks(
  domain: EmailDnsDomain,
): { key: string; label: string; status: string; detail: string; record: string | null }[] {
  /**
   * Shape one check into its card.
   * @param key - Check key.
   * @param label - Card label.
   * @param check - Raw check payload.
   * @returns The card definition.
   */
  const card: (
    key: string,
    label: string,
    check: EmailDnsCheck,
  ) => { key: string; label: string; status: string; detail: string; record: string | null } = (
    key: string,
    label: string,
    check: EmailDnsCheck,
  ): { key: string; label: string; status: string; detail: string; record: string | null } => ({
    key,
    label,
    status: check.status,
    detail: check.detail,
    record: check.record ?? null,
  })
  return [
    card('spf', 'SPF', domain.spf),
    card('dkim', 'DKIM', domain.dkim),
    card('dmarc', 'DMARC', domain.dmarc),
    card('mx', 'MX', domain.mx),
    card('blocklists', 'Blocklists', domain.blocklists),
  ]
}

/**
 * Authentication success ratios reported by Postmaster (when present).
 * @param postmaster - Postmaster payload.
 * @returns Label/value pairs.
 */
function postmasterAuthRatios(postmaster: PostmasterDomain): { label: string; value: string }[] {
  const latest: PostmasterDay | null | undefined = postmaster.latest
  if (!latest) return []
  const entries: { label: string; ratio: number | null }[] = [
    { label: 'SPF ok', ratio: latest.spf_success_ratio },
    { label: 'DKIM ok', ratio: latest.dkim_success_ratio },
    { label: 'DMARC ok', ratio: latest.dmarc_success_ratio },
  ]
  return entries
    .filter((entry: { label: string; ratio: number | null }): boolean => entry.ratio !== null)
    .map((entry: { label: string; ratio: number | null }): { label: string; value: string } => ({
      label: entry.label,
      value: `${formatRate((entry.ratio ?? 0) * 100)} %`,
    }))
}

/**
 * Reputation timeline days for the squares component.
 * @param postmaster - Postmaster payload.
 * @returns Date + reputation pairs.
 */
function reputationDays(postmaster: PostmasterDomain): { date: string; reputation: string | null }[] {
  return (postmaster.days ?? []).map((day: PostmasterDay): { date: string; reputation: string | null } => ({
    date: day.date,
    reputation: day.domain_reputation,
  }))
}

/**
 * Color of a Postmaster reputation value.
 * @param reputation - HIGH | MEDIUM | LOW | BAD | null.
 * @returns A CSS color.
 */
function reputationColor(reputation: string | null): string {
  switch ((reputation ?? '').toUpperCase()) {
    case 'HIGH':
      return 'var(--app-green)'
    case 'MEDIUM':
      return 'var(--app-accent-ink)'
    case 'LOW':
      return '#c47a3d'
    case 'BAD':
      return 'var(--app-red)'
    default:
      return 'var(--app-ink-soft)'
  }
}

/**
 * French label of a Postmaster reputation value.
 * @param reputation - HIGH | MEDIUM | LOW | BAD | null.
 * @returns The display label.
 */
function reputationLabel(reputation: string | null): string {
  switch ((reputation ?? '').toUpperCase()) {
    case 'HIGH':
      return 'Excellente'
    case 'MEDIUM':
      return 'Moyenne'
    case 'LOW':
      return 'Faible'
    case 'BAD':
      return 'Mauvaise'
    default:
      return 'Pas encore de donnée'
  }
}

/**
 * Format the Gmail user-reported spam ratio.
 * @param ratio - Ratio in [0, 1] or null.
 * @returns Percentage string or a dash.
 */
function formatSpamRatio(ratio: number | null): string {
  if (ratio === null) return '—'
  return `${formatRate(ratio * 100)} %`
}

/**
 * Color of the ok/warn/danger scale.
 * @param status - Status value.
 * @returns A CSS color.
 */
function statusColor(status: string): string {
  if (status === 'ok') return 'var(--app-green)'
  if (status === 'warn') return 'var(--app-accent-ink)'
  return 'var(--app-red)'
}

/**
 * Soft background of the ok/warn/danger scale.
 * @param status - Status value.
 * @returns A CSS color.
 */
function statusSoft(status: string): string {
  if (status === 'ok') return 'var(--app-green-soft)'
  if (status === 'warn') return 'var(--app-accent-soft)'
  return 'var(--app-red-soft)'
}

/**
 * French label of the ok/warn/danger scale.
 * @param status - Status value.
 * @returns The badge label.
 */
function statusLabel(status: string): string {
  if (status === 'ok') return 'Sain'
  if (status === 'warn') return 'À surveiller'
  return 'Problème'
}

/**
 * Icon of the ok/warn/danger scale.
 * @param status - Status value.
 * @returns A lucide icon name.
 */
function statusIcon(status: string): string {
  if (status === 'ok') return 'i-lucide-circle-check'
  if (status === 'warn') return 'i-lucide-triangle-alert'
  return 'i-lucide-circle-x'
}

/**
 * Color a rate against warn/danger thresholds.
 * @param value - Rate value.
 * @param warnAt - Warning threshold.
 * @param dangerAt - Danger threshold.
 * @returns A CSS color.
 */
function rateColor(value: number, warnAt: number, dangerAt: number): string {
  if (value >= dangerAt) return 'var(--app-red)'
  if (value >= warnAt) return 'var(--app-accent-ink)'
  return 'var(--app-ink)'
}

/**
 * Tone of an incident kind.
 * @param kind - Incident kind.
 * @returns ok/warn/danger.
 */
function incidentTone(kind: string): string {
  if (kind === 'complained') return 'danger'
  if (kind === 'bounced') return 'danger'
  return 'warn'
}

/**
 * French label of an incident kind.
 * @param kind - Incident kind.
 * @returns The badge label.
 */
function incidentLabel(kind: string): string {
  const labels: Record<string, string> = {
    bounced: 'Rejeté',
    complained: 'Signalé spam',
    suppressed: 'Bloqué (liste)',
    failed: 'Échec',
  }
  return labels[kind] ?? kind
}

/**
 * French label of a sending-account type.
 * @param accountType - Raw account type.
 * @returns The display label.
 */
function accountTypeLabel(accountType: string): string {
  const labels: Record<string, string> = {
    resend: 'Resend',
    custom_domain: 'Domaine personnalisé',
    gmail_oauth: 'Gmail',
    mailjet: 'Mailjet',
  }
  return labels[accountType] ?? accountType
}

/**
 * Format an integer for display.
 * @param value - Raw integer.
 * @returns Localized string.
 */
function formatInt(value: number): string {
  return value.toLocaleString('fr-FR')
}

/**
 * Format a rate with up to 2 decimals.
 * @param value - Raw rate.
 * @returns Localized string.
 */
function formatRate(value: number): string {
  return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
}

/**
 * Switch the rolling window and reload the period-scoped sections.
 * @param preset - New window in days.
 * @returns A promise resolved once reloaded.
 */
async function changePeriod(preset: number): Promise<void> {
  if (period.value === preset) return
  period.value = preset
  await load()
}

/**
 * Load every section of the page (period-scoped + static ones in parallel).
 * @returns A promise resolved once everything settled.
 */
async function load(): Promise<void> {
  isLoading.value = true
  loadError.value = null
  try {
    const [overviewData, trendsData, providersData, incidentsData]: [
      EmailHealthOverview,
      { days: EmailHealthTrendDay[] },
      { providers: EmailHealthProvider[] },
      { items: EmailHealthIncident[] },
    ] = await Promise.all([
      EmailHealthService.getEmailHealthOverview(period.value),
      EmailHealthService.getEmailHealthTrends(period.value),
      EmailHealthService.getEmailHealthProviders(period.value),
      EmailHealthService.getEmailHealthIncidents(50),
    ])
    overview.value = overviewData
    trendDays.value = trendsData.days
    providers.value = providersData.providers
    incidents.value = incidentsData.items
  } catch (error: unknown) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger la santé email.'
  } finally {
    isLoading.value = false
  }

  // Chargés à part : plus lents, et leur échec dégrade en section vide, jamais en erreur de page.
  try {
    dnsDomains.value = (await EmailHealthService.getEmailHealthDns()).domains
  } catch {
    dnsDomains.value = []
  }
  await loadPostmaster()
}

/**
 * Load Postmaster connection state and per-domain stats.
 * @returns A promise resolved once loaded.
 */
async function loadPostmaster(): Promise<void> {
  try {
    const response: PostmasterResponse = await EmailHealthService.getEmailHealthPostmaster(period.value)
    postmasterConnection.value = response.connection
    postmasterDomains.value = response.domains
  } catch {
    postmasterConnection.value = { connected: false, oauth_available: true }
    postmasterDomains.value = []
  }
}

/**
 * Redirect the browser to Google OAuth for Postmaster Tools.
 * @returns A promise resolved once the auth URL is fetched.
 */
async function connectPostmaster(): Promise<void> {
  isConnectingPostmaster.value = true
  try {
    const { auth_url: authUrl }: { auth_url: string } = await EmailHealthService.getPostmasterAuthUrl()
    window.location.href = authUrl
  } catch {
    toast.error('Impossible de lancer la connexion Google')
    isConnectingPostmaster.value = false
  }
}

/**
 * Remove the stored Postmaster OAuth connection.
 * @returns A promise resolved once disconnected.
 */
async function disconnectPostmaster(): Promise<void> {
  isDisconnectingPostmaster.value = true
  try {
    await EmailHealthService.disconnectPostmaster()
    postmasterConnection.value = { connected: false, google_email: null, oauth_available: true }
    postmasterDomains.value = []
    toast.success('Postmaster déconnecté')
  } catch {
    toast.error('Échec de la déconnexion')
  } finally {
    isDisconnectingPostmaster.value = false
  }
}

/**
 * Surface Postmaster OAuth callback feedback and strip the query flag.
 * @returns A promise resolved once handled.
 */
async function handlePostmasterCallbackFeedback(): Promise<void> {
  const flag: unknown = route.query.postmaster
  if (flag !== 'connected' && flag !== 'error') return
  if (flag === 'connected') {
    toast.success('Google Postmaster connecté')
    await loadPostmaster()
  } else {
    toast.error('La connexion Google Postmaster a échoué')
  }
  await router.replace({ query: { ...route.query, postmaster: undefined } })
}

/**
 * Score every active email template automatically (nothing is sent).
 * Independent of the period selector — run once per page visit.
 * @returns A promise resolved once scored.
 */
async function loadTemplateScores(): Promise<void> {
  isScoringTemplates.value = true
  try {
    templateScores.value = await EmailHealthService.getEmailTemplateScores()
  } catch {
    templateScores.value = { initial: [], follow_up: [] }
  } finally {
    isScoringTemplates.value = false
  }
}

onMounted(async (): Promise<void> => {
  await load()
  void loadTemplateScores()
  await handlePostmasterCallbackFeedback()
})
</script>
