<template>
  <div class="flex min-h-0 flex-1 flex-col" :data-no-pull-to-refresh="hasPendingChanges ? '' : undefined">
    <UiLoader v-if="pending" />

    <div
      v-else-if="loadError"
      class="card m-4 border-[var(--app-red)]/30 bg-[var(--app-red-soft)] p-6 text-[var(--app-red)]"
    >
      {{ loadError }}
    </div>

    <template v-else-if="site">
      <header
        class="flex shrink-0 items-center gap-2 border-b border-[var(--app-line)] bg-[var(--app-surface)] px-3 py-2 md:px-4"
      >
        <NuxtLink
          to="/dashboard/demo-sites"
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
          title="Retour aux sites"
          aria-label="Retour aux sites"
        >
          <UIcon name="i-lucide-arrow-left" class="h-5 w-5" />
        </NuxtLink>
        <div class="min-w-0 flex-1">
          <div class="flex min-w-0 items-center gap-2">
            <h1 class="truncate text-base font-semibold text-[var(--app-ink)]">{{ site.business_name }}</h1>
            <span
              :class="[
                'inline-flex shrink-0 items-center gap-1.5 rounded-full p-1.5 text-[11px] font-medium sm:px-2 sm:py-0.5',
                isSiteReachable
                  ? 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
                  : 'bg-[var(--app-red)]/20 text-[var(--app-red)]',
              ]"
            >
              <span class="h-1.5 w-1.5 rounded-full bg-current" :title="statusLabel"></span>
              <span class="hidden sm:inline">{{ statusLabel }}</span>
              <span class="sr-only sm:hidden">{{ statusLabel }}</span>
            </span>
          </div>
          <p class="truncate text-xs text-[var(--app-ink-soft)]">{{ siteFactsLine }}</p>
        </div>
        <template v-if="hasPendingChanges">
          <button
            type="button"
            class="btn-secondary inline-flex h-10 items-center gap-2 px-3 sm:px-4"
            title="Annuler les modifications"
            aria-label="Annuler les modifications"
            :disabled="saving"
            @click="resetPendingChanges"
          >
            <UIcon name="i-lucide-undo-2" class="h-4 w-4 sm:hidden" />
            <span class="hidden sm:inline">Annuler</span>
          </button>
          <button
            type="button"
            class="btn-primary inline-flex h-10 items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="saving || !canSavePendingChanges"
            :title="!canSavePendingChanges ? serviceCardsValidationMessage : undefined"
            @click="savePendingChanges"
          >
            <UIcon name="i-lucide-upload" class="h-4 w-4" />
            {{ saving ? 'Publication…' : 'Publier' }}
          </button>
        </template>
        <template v-else-if="openUrl">
          <button
            type="button"
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[var(--app-line)] text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
            :title="copied ? 'Lien copié' : 'Copier le lien de la démo'"
            :aria-label="copied ? 'Lien copié' : 'Copier le lien de la démo'"
            @click="copyDemoUrl(openUrl)"
          >
            <UIcon :name="copied ? 'i-lucide-check' : 'i-lucide-link'" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="btn-primary inline-flex h-10 items-center gap-2"
            title="Ouvrir la démo"
            aria-label="Ouvrir la démo"
            @click="openDemoUrl(DemoSiteService.withInternalFlag(openUrl))"
          >
            <UIcon name="i-lucide-external-link" class="h-4 w-4" />
            <span class="hidden sm:inline">Ouvrir</span>
          </button>
        </template>
      </header>

      <p
        v-if="site.verification_message && !isSiteReachable"
        class="shrink-0 border-b border-[var(--app-red)]/30 bg-[var(--app-red-soft)] px-4 py-2 text-xs text-[var(--app-red)]"
      >
        {{ site.verification_message }}
      </p>

      <div v-show="activeTool !== 'plus'" class="flex min-h-0 flex-1 flex-col">
        <div class="flex shrink-0 justify-center border-b border-[var(--app-line)] bg-[var(--app-surface)] py-2">
          <div
            class="flex overflow-hidden rounded-full border border-[var(--app-line)] bg-[var(--app-bg)]"
            role="group"
            aria-label="Format de l'aperçu"
          >
            <button
              v-for="device in ATELIER_PREVIEW_DEVICES"
              :key="device.key"
              type="button"
              :class="[
                'flex h-9 items-center gap-1.5 px-4 text-xs font-medium transition-colors',
                previewDevice === device.key
                  ? 'bg-[var(--app-ink)] text-[var(--app-bg)]'
                  : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
              ]"
              :aria-pressed="previewDevice === device.key"
              @click="previewDevice = device.key"
            >
              <UIcon :name="device.icon" class="h-3.5 w-3.5" />
              {{ device.label }}
            </button>
          </div>
        </div>

        <div ref="workAreaElement" class="flex min-h-0 flex-1 flex-col">
          <div class="min-h-0 flex-1">
            <AtelierDevicePreview
              v-if="openUrl"
              :page-url="openUrl"
              :device="previewDevice"
              :preview-message="previewMessage"
              :reload-nonce="previewReloadNonce"
            />
            <div v-else class="flex h-full items-center justify-center bg-[var(--app-surface-2)] p-6">
              <UiEmptyState title="Pas encore d'adresse" description="Le site n'est pas encore en ligne." />
            </div>
          </div>

          <Transition name="atelier-sheet">
            <section
              v-if="isToolSheetOpen && activeToolMeta"
              ref="sheetElement"
              class="relative flex shrink-0 flex-col rounded-t-2xl border-t border-[var(--app-line)] bg-[var(--app-surface)] shadow-[0_-12px_40px_rgba(0,0,0,0.08)] outline-none"
              :style="sheetStyle"
              :aria-label="activeToolMeta.title"
              tabindex="-1"
              data-no-pull-to-refresh
            >
              <button
                type="button"
                class="flex h-5 w-full shrink-0 cursor-grab touch-none items-end justify-center active:cursor-grabbing"
                :title="sheetSize === 'expanded' ? 'Réduire le volet' : 'Agrandir le volet'"
                :aria-label="sheetSize === 'expanded' ? 'Réduire le volet' : 'Agrandir le volet'"
                :aria-expanded="sheetSize === 'expanded'"
                @pointerdown="startSheetDrag"
                @pointermove="followSheetDrag"
                @pointerup="endSheetDrag"
                @pointercancel="cancelSheetDrag"
                @click="toggleSheetSize"
              >
                <span class="h-1 w-10 rounded-full bg-[var(--app-line)]"></span>
              </button>
              <div class="flex shrink-0 items-start gap-3 px-4 pt-1 pb-2 md:px-5">
                <div class="min-w-0 flex-1">
                  <h2 class="text-sm font-semibold text-[var(--app-ink)]">{{ activeToolMeta.title }}</h2>
                  <p class="truncate text-xs text-[var(--app-ink-soft)]">{{ activeToolHint }}</p>
                </div>
                <button
                  type="button"
                  class="-mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                  title="Fermer le volet"
                  aria-label="Fermer le volet"
                  @click="closeActiveTool"
                >
                  <UIcon name="i-lucide-x" class="h-4 w-4" />
                </button>
              </div>

              <div class="min-h-0 flex-1 overflow-y-auto px-4 pb-4 md:px-5">
                <template v-if="activeTool === 'template'">
                  <div v-if="loadingTemplates" class="flex items-center justify-center py-10">
                    <div class="loader-smooth"></div>
                  </div>
                  <div v-else-if="selectableTemplates.length" class="flex gap-3 overflow-x-auto pb-2">
                    <button
                      v-for="template in selectableTemplates"
                      :key="template.id"
                      type="button"
                      :class="[
                        'w-52 shrink-0 rounded-xl border p-2 text-left transition-colors',
                        selectedTemplateId === template.id
                          ? 'border-[var(--app-ink)] ring-1 ring-[var(--app-ink)]/15'
                          : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]',
                      ]"
                      :aria-pressed="selectedTemplateId === template.id"
                      @click="selectedTemplateId = template.id"
                    >
                      <div
                        class="relative aspect-[16/10] overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
                      >
                        <img
                          v-if="!failedTemplateThumbnailIds.has(template.id)"
                          :src="`/templates/${template.id}.jpg`"
                          :alt="`Aperçu du template ${template.name}`"
                          class="absolute inset-0 h-full w-full object-cover object-top"
                          loading="lazy"
                          @error="failedTemplateThumbnailIds.add(template.id)"
                        />
                        <span
                          v-if="selectedTemplateId === template.id"
                          class="absolute top-1.5 right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--app-ink)] text-[var(--app-bg)]"
                        >
                          <UIcon name="i-lucide-check" class="h-3 w-3" />
                        </span>
                      </div>
                      <div class="mt-2 flex items-center justify-between gap-2 px-0.5">
                        <span class="truncate text-[13px] font-semibold text-[var(--app-ink)]">{{
                          template.name
                        }}</span>
                        <span
                          v-if="template.id === site.template_id"
                          class="shrink-0 rounded-full bg-[var(--app-surface-2)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-ink-soft)]"
                        >
                          Actuelle
                        </span>
                      </div>
                    </button>
                  </div>
                  <UiEmptyState
                    v-else
                    title="Templates indisponibles"
                    description="La liste des templates n'a pas pu être chargée. Rechargez la page pour réessayer."
                  />
                </template>

                <DemoSitesColorEditor
                  v-else-if="activeTool === 'couleurs'"
                  :template="selectedTemplate"
                  :theme="selectedTheme"
                  :use-brand-color="selectedUseBrandColor"
                  :brand-color="site.brand_color ?? null"
                  @update:theme="selectedTheme = $event"
                  @update:use-brand-color="selectedUseBrandColor = $event"
                />

                <template v-else-if="activeTool === 'photos'">
                  <template v-if="siteImages && siteImages.pool.length">
                    <DemoSitesImageGrid
                      v-if="isCoarsePointer"
                      :pool="siteImages.pool"
                      :order="imagesOrder"
                      is-heading-hidden
                      @update:order="onImageOrderChange"
                    />
                    <DemoSitesImageSlots
                      v-else
                      :pool="siteImages.pool"
                      :order="imagesOrder"
                      is-heading-hidden
                      @update:order="onImageOrderChange"
                    />
                  </template>
                  <UiEmptyState
                    v-else
                    title="Aucune photo exploitable"
                    description="Ce prospect n'a pas de photo utilisable : le site garde les images par défaut de la template."
                  />
                </template>

                <DemoSitesServiceCardsEditor
                  v-else-if="activeTool === 'prestations' && serviceCards && isServiceCardsEditorVisible"
                  :cards="serviceCardsDraft"
                  :pool="serviceCards.pool"
                  :config="serviceCards.config"
                  :ai-available="serviceCards.ai_available"
                  :suggesting="suggestingServiceCards"
                  :suggestion-error="serviceCardsSuggestionError"
                  :analysis="serviceCardsAnalysis"
                  :override-active="serviceCards.override_active"
                  :override-source="serviceCards.override_source"
                  :labels-pending="serviceCards.labels_pending"
                  @update:cards="onServiceCardsChange"
                  @suggest="suggestServiceCards"
                  @reset="resetServiceCardsModalRef?.open()"
                />

                <div v-else-if="activeTool === 'video'">
                  <div class="mx-auto w-full max-w-md">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-xs text-[var(--app-ink-soft)]">
                        Votre webcam + le site qui défile, avec « Bonjour {Prénom} » à l'écran.
                      </p>
                      <span
                        v-if="videoStatusLabel"
                        :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', videoStatusClass]"
                      >
                        {{ videoStatusLabel }}
                      </span>
                    </div>
                    <div
                      v-if="isVideoGenerating"
                      class="mt-3 flex items-center gap-2 text-xs text-[var(--app-ink-soft)]"
                    >
                      <UIcon name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
                      Génération en cours (capture + montage)…
                    </div>

                    <div v-else-if="isVideoWaitingForDesktop" class="mt-3">
                      <p class="flex items-start gap-2 text-xs leading-relaxed text-[var(--app-ink-soft)]">
                        <UIcon
                          :name="site.is_video_desktop_build_started ? 'i-lucide-loader-circle' : 'i-lucide-monitor'"
                          :class="['mt-0.5 h-4 w-4 shrink-0', { 'animate-spin': site.is_video_desktop_build_started }]"
                        />
                        <span>{{ desktopVideoRequestLabel }}</span>
                      </p>
                      <div v-if="!site.is_video_desktop_build_started" class="mt-2 space-y-2">
                        <button
                          type="button"
                          class="btn-secondary w-full text-xs"
                          :disabled="cancellingDesktopVideoRequest || generatingVideo"
                          @click="handleCancelDesktopVideoRequest"
                        >
                          {{ cancellingDesktopVideoRequest ? 'Annulation…' : 'Annuler la demande' }}
                        </button>
                        <button
                          type="button"
                          class="btn-secondary w-full text-xs"
                          :disabled="cancellingDesktopVideoRequest || generatingVideo"
                          @click="handleGenerateVideoOnServer"
                        >
                          {{ generatingVideo ? 'Lancement…' : 'Générer sur le serveur (sans la séquence Storyblok)' }}
                        </button>
                      </div>
                    </div>

                    <p v-else-if="videoFailureMessage" class="mt-3 text-xs text-[var(--app-red)]">
                      {{ videoFailureMessage }}
                    </p>

                    <template v-if="site.video_status === 'ready' && site.video_page_url">
                      <button
                        type="button"
                        class="mt-3 block w-full cursor-pointer overflow-hidden rounded-lg border border-[var(--app-line)] transition-opacity hover:opacity-90"
                        title="Ouvrir la page vidéo"
                        aria-label="Ouvrir la page vidéo"
                        @click="openVideoPage(site.video_page_url)"
                      >
                        <img
                          v-if="site.video_thumbnail_url"
                          :src="site.video_thumbnail_url"
                          alt="Vignette de la vidéo de prospection"
                          class="w-full"
                        />
                      </button>
                      <div class="mt-2 space-y-2">
                        <button
                          type="button"
                          class="btn-secondary w-full text-xs"
                          @click="copyVideoUrl(site.video_page_url)"
                        >
                          {{ copied ? 'Lien copié !' : 'Copier le lien vidéo' }}
                        </button>
                        <button
                          v-if="!isVideoWaitingForDesktop"
                          type="button"
                          class="btn-secondary w-full text-xs"
                          :disabled="generatingVideo"
                          @click="handleGenerateVideo"
                        >
                          {{ generatingVideo ? 'Lancement…' : 'Régénérer la vidéo' }}
                        </button>
                        <button
                          type="button"
                          class="btn-secondary w-full text-xs text-[var(--app-red)]"
                          :disabled="deletingVideo || site.is_video_desktop_build_started"
                          @click="askDeleteVideo"
                        >
                          {{ deletingVideo ? 'Suppression…' : 'Supprimer la vidéo' }}
                        </button>
                      </div>
                    </template>

                    <button
                      v-if="!isVideoGenerating && !isVideoWaitingForDesktop && site.video_status !== 'ready'"
                      type="button"
                      class="btn-primary mt-3 w-full text-xs disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="generatingVideo"
                      @click="handleGenerateVideo"
                    >
                      <UIcon name="i-lucide-clapperboard" class="mr-1.5 h-3.5 w-3.5" />
                      {{
                        generatingVideo
                          ? 'Lancement…'
                          : site.video_status === 'failed'
                            ? 'Réessayer'
                            : 'Générer la vidéo'
                      }}
                    </button>

                    <p v-if="videoPrepStatus" class="text-muted mt-3 text-center text-[11px] leading-relaxed">
                      {{ videoPrepStatus }}
                    </p>

                    <NuxtLink
                      to="/dashboard/settings/video"
                      class="mt-2 block w-full text-center text-[11px] text-[var(--app-ink-soft)] underline underline-offset-2 transition-colors hover:text-[var(--app-ink)]"
                    >
                      Configurer mon clip webcam (Paramètres
                      <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Vidéo de
                      prospection)
                    </NuxtLink>
                  </div>
                </div>
              </div>
            </section>
          </Transition>
        </div>
      </div>

      <section
        v-if="activeTool === 'plus'"
        class="min-h-0 flex-1 overflow-y-auto p-4 md:p-6"
        :aria-label="activeToolMeta?.title"
      >
        <div class="mx-auto w-full max-w-4xl space-y-4">
          <div class="card p-5">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Lien de la démo</h2>
            <p class="mt-1 text-xs text-[var(--app-ink-soft)]">Le lien envoyé au prospect. {{ expiryLabel }}</p>
            <div v-if="openUrl" class="mt-3 flex items-center gap-2">
              <input
                :value="openUrl"
                readonly
                class="input-field h-10 flex-1 truncate text-xs"
                aria-label="Lien de la démo"
              />
              <button
                type="button"
                class="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]"
                :title="copied ? 'Lien copié !' : 'Copier le lien'"
                :aria-label="copied ? 'Lien copié' : 'Copier le lien'"
                @click="copyDemoUrl(openUrl)"
              >
                <UIcon :name="copied ? 'i-lucide-check' : 'i-lucide-copy'" class="h-4 w-4" />
              </button>
            </div>
            <p v-else class="mt-3 text-xs text-[var(--app-ink-soft)]">Le site n'a pas encore d'adresse.</p>
            <p
              v-if="site.local_demo_url && site.local_demo_url !== site.demo_url"
              class="mt-2 text-xs break-all text-[var(--app-ink-soft)]"
            >
              Adresse locale : {{ site.local_demo_url }}
            </p>
          </div>

          <div v-if="site.storyblok_editor_url" class="card p-5">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-sm font-semibold text-[var(--app-ink)]">Espace d'administration du client</h2>
              <span
                v-if="cmsStatusLabel"
                :class="['rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase', cmsStatusClass]"
              >
                {{ cmsStatusLabel }}
              </span>
            </div>
            <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
              <template v-if="cmsStatus === 'joined'">
                Le client a rejoint l'espace{{ cmsJoinedAtLabel ? ` le ${cmsJoinedAtLabel}` : '' }} ({{
                  site.storyblok_login_email || site.email
                }}).
              </template>
              <template v-else-if="cmsStatus === 'pending'">
                Invitation envoyée à {{ site.storyblok_login_email || site.email }}, en attente qu'il rejoigne l'espace.
              </template>
              <template v-else>
                Le client modifie ses textes et ses photos lui-même dans Storyblok. Invitez-le une fois le site vendu.
              </template>
            </p>
            <div class="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                class="btn-secondary h-10 text-xs"
                @click="openDemoUrl(site.storyblok_editor_url ?? null)"
              >
                <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
                Ouvrir l'éditeur
              </button>
              <button
                v-if="cmsStatus === 'pending'"
                type="button"
                class="btn-secondary h-10 text-xs disabled:opacity-50"
                :disabled="refreshingCms"
                @click="handleRefreshCmsStatus"
              >
                {{ refreshingCms ? 'Vérification…' : 'Vérifier s’il a rejoint' }}
              </button>
              <button
                v-else-if="cmsStatus !== 'joined'"
                type="button"
                class="btn-primary h-10 text-xs"
                :disabled="inviting"
                @click="handleInvite"
              >
                {{ inviting ? 'Envoi…' : 'Inviter le client' }}
              </button>
            </div>
          </div>

          <div class="card p-5">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Informations du prospect</h2>
            <dl class="mt-3 grid gap-x-8 gap-y-2.5 text-sm @2xl:grid-cols-2">
              <div v-if="site.email" class="flex justify-between gap-3 border-b border-[var(--app-line-soft)] pb-2">
                <dt class="text-[var(--app-ink-soft)]">Email</dt>
                <dd class="truncate text-right text-[var(--app-ink)]">{{ site.email }}</dd>
              </div>
              <div v-if="site.phone" class="flex justify-between gap-3 border-b border-[var(--app-line-soft)] pb-2">
                <dt class="text-[var(--app-ink-soft)]">Téléphone</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ site.phone }}</dd>
              </div>
              <div v-if="site.city" class="flex justify-between gap-3 border-b border-[var(--app-line-soft)] pb-2">
                <dt class="text-[var(--app-ink-soft)]">Ville</dt>
                <dd class="truncate text-right text-[var(--app-ink)]">{{ site.city }}</dd>
              </div>
              <div class="flex justify-between gap-3 border-b border-[var(--app-line-soft)] pb-2">
                <dt class="text-[var(--app-ink-soft)]">Site créé le</dt>
                <dd class="text-right text-[var(--app-ink)]">{{ formatNumericDate(site.created_at) }}</dd>
              </div>
              <div class="flex justify-between gap-3 border-b border-[var(--app-line-soft)] pb-2">
                <dt class="text-[var(--app-ink-soft)]">Template</dt>
                <dd class="truncate text-right text-[var(--app-ink)]">{{ templateLabel }}</dd>
              </div>
            </dl>
            <p
              v-if="site.description"
              class="mt-3 text-sm leading-relaxed whitespace-pre-wrap text-[var(--app-ink-soft)]"
            >
              {{ site.description }}
            </p>
            <NuxtLink :to="`/dashboard/demo-sites/${site.id}/edit`" class="btn-secondary mt-3 h-10 w-full text-xs">
              <UIcon name="i-lucide-square-pen" class="h-3.5 w-3.5" />
              Modifier ces informations
            </NuxtLink>
          </div>

          <div class="card p-5">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Code du site</h2>
            <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
              Un zip prêt à lancer, avec le contenu du prospect : pour un travail sur mesure après la vente.
            </p>
            <button type="button" class="btn-secondary mt-3 h-10 text-xs" :disabled="exporting" @click="handleExport">
              <UIcon name="i-lucide-download" class="h-3.5 w-3.5" />
              {{ exporting ? 'Préparation du zip…' : 'Exporter le code' }}
            </button>
          </div>

          <div class="card border-[var(--app-red)]/30 p-5">
            <h2 class="text-sm font-semibold text-[var(--app-red)]">Supprimer le site</h2>
            <p class="mt-1 text-xs text-[var(--app-ink-soft)]">
              La démo et son espace d'administration sont retirés. Les liens déjà envoyés ne mènent plus nulle part.
            </p>
            <button
              type="button"
              class="btn-secondary mt-3 h-10 text-xs text-[var(--app-red)]"
              :disabled="deleting"
              @click="deleteSiteModalRef?.open()"
            >
              <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
              {{ deleting ? 'Suppression…' : 'Supprimer le site' }}
            </button>
          </div>
        </div>
      </section>

      <nav
        class="flex shrink-0 items-stretch border-t border-[var(--app-line)] bg-[var(--app-surface)] pb-[env(safe-area-inset-bottom)]"
        aria-label="Outils du site"
      >
        <button
          v-for="tool in visibleTools"
          :key="tool.key"
          :ref="(element: Element | ComponentPublicInstance | null): void => registerToolButton(tool.key, element)"
          type="button"
          :class="[
            'relative flex min-h-16 min-w-0 flex-1 flex-col items-center justify-center gap-1 text-[10px] font-medium transition-colors [-webkit-tap-highlight-color:transparent] sm:text-[11px]',
            activeTool === tool.key
              ? 'text-[var(--app-ink)]'
              : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
          ]"
          :aria-pressed="activeTool === tool.key"
          @click="toggleTool(tool.key)"
        >
          <span
            :class="[
              'flex h-8 w-12 items-center justify-center rounded-full transition-colors',
              activeTool === tool.key ? 'bg-[var(--app-ink)] text-[var(--app-bg)]' : '',
            ]"
          >
            <UIcon :name="tool.icon" class="h-5 w-5" />
          </span>
          <span class="max-w-full truncate px-0.5">{{ tool.label }}</span>
          <span
            v-if="toolPendingChanges[tool.key]"
            class="absolute top-2 right-[calc(50%-18px)] h-2 w-2 rounded-full bg-[var(--app-accent)]"
            title="Modifications non publiées"
          ></span>
          <span v-if="toolPendingChanges[tool.key]" class="sr-only">(modifications non publiées)</span>
        </button>
      </nav>

      <UiConfirmModal
        ref="deleteSiteModalRef"
        title="Supprimer le site"
        :message="`Supprimer le site « ${site.business_name} » ? La démo et son espace CMS seront retirés. Cette action est irréversible.`"
        confirm-text="Supprimer"
        cancel-text="Annuler"
        @confirm="handleDelete"
      />
      <UiConfirmModal
        ref="deleteVideoModalRef"
        title="Supprimer la vidéo"
        message="Supprimer la vidéo de prospection de ce site ? Le lien envoyé dans les emails ne fonctionnera plus."
        confirm-text="Supprimer"
        cancel-text="Annuler"
        @confirm="handleDeleteVideoConfirmed"
      />
      <UiConfirmModal
        ref="resetServiceCardsModalRef"
        title="Revenir aux cartes automatiques"
        message="Les cartes personnalisées seront supprimées et le site régénéré avec les cartes automatiques. Continuer ?"
        confirm-text="Revenir"
        cancel-text="Annuler"
        @confirm="restoreGeneratedServiceCards"
      />
    </template>

    <UiVideoGenerationModal
      :open="videoProgress.isOpen.value"
      title="Génération de la vidéo"
      :steps="videoProgress.steps.value"
      :log-lines="videoProgress.logLines.value"
      :elapsed-seconds="videoProgress.elapsedSeconds.value"
      :error-message="videoProgress.errorMessage.value"
      :is-running="videoProgress.isRunning.value"
      @close="videoProgress.close()"
    />
  </div>
</template>

<script lang="ts" setup>
import { formatNumericDate } from '~/utils/date'
import type {
  UseAtelierToolSheetReturn,
  UseCopyToClipboardReturn,
  UseOpenExternalUrlReturn,
  UseToastReturn,
} from '~/types/Composables'
import type { DemoSiteAtelierToolKey } from '~/types/DemoSiteDetailPage'
import type { AtelierTool } from '~/types/AtelierToolSheet'
import { filterSelectableTemplates, sortTemplatesByRecommendation } from '~/utils/templateRecommendation'
import type { ServiceCardDraft } from '~/types/ServiceCardsEditor'
import type { TemplatePreviewDevice, TemplateThemeColorKey } from '~/types/TemplatePicker'
import type { ComponentPublicInstance, ComputedRef, Ref } from 'vue'
import type {
  DemoSite,
  DemoSiteImages,
  DemoSitePhotoLabel,
  DemoSiteServiceCard,
  DemoSiteServiceCards,
  DemoSiteServiceCardsAnalysis,
  DemoSiteServiceCardsSuggestionResult,
  DemoSiteTemplate,
  DemoSiteTheme,
  DemoSiteUpdatePayload,
  DemoSiteVideoState,
  StoryblokCollaboratorStatus,
} from '~/services/demoSiteService'
import { DEFAULT_DEMO_SITE_THEME, DemoSiteService } from '~/services/demoSiteService'
import { getScraperSidecarInfo } from '~/services/scraperSidecarService'
import { StoryblokSidecarService } from '~/services/storyblokSidecarService'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { useToast } from '~/composables/useToast'
import type { UseVideoGenerationProgressReturn } from '~/composables/useVideoGenerationProgress'
import { useVideoGenerationProgress } from '~/composables/useVideoGenerationProgress'
import { ServiceCards } from '~/utils/serviceCards'
import { useAtelierToolSheet } from '~/composables/useAtelierToolSheet'
import { ATELIER_PREVIEW_DEVICES } from '~/constants/atelierPreviewDevices'
import { useCoarsePointer } from '~/composables/useCoarsePointer'

const VIDEO_STATE_POLL_INTERVAL_MS: number = 5_000

const DESKTOP_VIDEO_WAIT_POLL_INTERVAL_MS: number = 15_000

definePageMeta({ layout: 'dashboard', middleware: 'auth', shouldFillDashboardViewport: true })

const route: ReturnType<typeof useRoute> = useRoute()
const demoSiteId: number = Number(route.params.id)
const { copy, copied }: UseCopyToClipboardReturn = useCopyToClipboard()
const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()
const toast: UseToastReturn = useToast()
const videoProgress: UseVideoGenerationProgressReturn = useVideoGenerationProgress()
const prospectSearchStore: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const isCoarsePointer: Ref<boolean> = useCoarsePointer()

/** The tools of the atelier, in the order of the bottom bar; « Prestations » only when the template has cards. */
const atelierTools: AtelierTool<DemoSiteAtelierToolKey>[] = [
  {
    key: 'template',
    label: 'Template',
    icon: 'i-lucide-layout-template',
    title: 'Template',
    hint: 'Le site se redessine en direct ; publiez pour l’appliquer.',
  },
  {
    key: 'couleurs',
    label: 'Couleurs',
    icon: 'i-lucide-palette',
    title: 'Couleurs',
    hint: 'Couleur du logo ou de la template, et le fond.',
  },
  {
    key: 'photos',
    label: 'Photos',
    icon: 'i-lucide-images',
    title: 'Photos',
    hint: 'La première devient l’en-tête, la deuxième « à propos », le reste la galerie.',
    coarsePointerHint:
      'Maintenez une photo puis glissez-la. La première est l’en-tête, la deuxième « à propos », le reste la galerie.',
  },
  {
    key: 'prestations',
    label: 'Prestations',
    icon: 'i-lucide-list-checks',
    title: 'Prestations',
    hint: 'Les cartes de services montrées sur le site.',
  },
  {
    key: 'video',
    label: 'Vidéo',
    icon: 'i-lucide-clapperboard',
    title: 'Vidéo de prospection',
    hint: 'La vidéo envoyée dans les emails et les SMS.',
  },
  {
    key: 'plus',
    label: 'Plus',
    icon: 'i-lucide-ellipsis',
    title: 'Lien, client et après-vente',
    hint: 'Le lien de la démo, l’espace du client, les informations, le code.',
  },
]

const {
  activeTool,
  sheetSize,
  workAreaElement,
  sheetElement,
  isToolSheetOpen,
  activeToolMeta,
  activeToolHint,
  sheetStyle,
  toggleTool,
  closeActiveTool,
  registerToolButton,
  startSheetDrag,
  followSheetDrag,
  endSheetDrag,
  cancelSheetDrag,
  toggleSheetSize,
}: UseAtelierToolSheetReturn<DemoSiteAtelierToolKey> = useAtelierToolSheet<DemoSiteAtelierToolKey>(
  atelierTools,
  ['plus'],
  isCoarsePointer,
)

const site: Ref<DemoSite | null> = ref(null)
const pending: Ref<boolean> = ref(true)
const loadError: Ref<string | null> = ref(null)
const templates: Ref<DemoSiteTemplate[]> = ref([])
const loadingTemplates: Ref<boolean> = ref(true)
const failedTemplateThumbnailIds: Ref<Set<string>> = ref(new Set())
const previewDevice: Ref<TemplatePreviewDevice> = ref('mobile')
const selectedTemplateId: Ref<string> = ref('')
const selectedTheme: Ref<DemoSiteTheme> = ref({ ...DEFAULT_DEMO_SITE_THEME })
/** Action colour source: logo (true) / template (false). */
const selectedUseBrandColor: Ref<boolean> = ref(true)
/** Candidate photo placement (hero/about/gallery), edited live and saved with the other changes. */
const imagesOrder: Ref<string[]> = ref([])
const siteImages: Ref<DemoSiteImages | null> = ref(null)
const serviceCards: Ref<DemoSiteServiceCards | null> = ref(null)
/** Candidate cards, edited live and saved with the other changes. */
const serviceCardsDraft: Ref<ServiceCardDraft[]> = ref([])
/** True while the draft is exactly the last AI suggestion (saved as source « ai »). */
const serviceCardsDraftFromAi: Ref<boolean> = ref(false)
const suggestingServiceCards: Ref<boolean> = ref(false)
const serviceCardsSuggestionError: Ref<string | null> = ref(null)
const serviceCardsAnalysis: Ref<DemoSiteServiceCardsAnalysis | null> = ref(null)
const resetServiceCardsModalRef: Ref<{ open: () => void } | null> = ref(null)
const saving: Ref<boolean> = ref(false)
/** Bumped after a save to force the live preview iframe to reload the published content. */
const previewReloadNonce: Ref<number> = ref(0)
const deleting: Ref<boolean> = ref(false)
const inviting: Ref<boolean> = ref(false)
const refreshingCms: Ref<boolean> = ref(false)
const exporting: Ref<boolean> = ref(false)
const generatingVideo: Ref<boolean> = ref(false)
const videoPrepStatus: Ref<string> = ref('')
const deletingVideo: Ref<boolean> = ref(false)
const cancellingDesktopVideoRequest: Ref<boolean> = ref(false)
const deleteVideoModalRef: Ref<{ open: () => void } | null> = ref(null)
const deleteSiteModalRef: Ref<{ open: () => void } | null> = ref(null)
let videoPollTimer: ReturnType<typeof setTimeout> | null = null
let hasLeftPage: boolean = false

const templateLabel: ComputedRef<string> = computed((): string => {
  const templateId: string = site.value?.template_id ?? ''
  const catalogued: DemoSiteTemplate | undefined = templates.value.find(
    (template: DemoSiteTemplate): boolean => template.id === templateId,
  )
  if (catalogued) return catalogued.name
  const labels: Record<string, string> = {
    'plumber-cuivre': 'Plombier Source',
    'electrician-eclat': 'Électricien Éclat',
    'electrician-lumen': 'Électricien Lumen',
  }
  return labels[templateId] ?? templateId
})

const openUrl: ComputedRef<string | null> = computed(() =>
  site.value ? DemoSiteService.getDemoSiteOpenUrl(site.value) : null,
)

const isSiteReachable: ComputedRef<boolean> = computed(
  (): boolean => site.value !== null && DemoSiteService.isDemoSiteReachable(site.value),
)

const statusLabel: ComputedRef<string> = computed((): string => {
  if (!site.value) return ''
  if (isSiteReachable.value) return 'En ligne'
  if (site.value.status === 'failed') return 'Échec'
  if (site.value.status === 'unavailable') return 'Hors ligne'
  return site.value.status
})

const daysLeft: ComputedRef<number> = computed(() =>
  site.value ? DemoSiteService.daysUntilExpiry(site.value.expires_at) : 0,
)

/** The template currently selected in the picker (drives the colour editor's roles). */
const selectedTemplate: ComputedRef<DemoSiteTemplate | null> = computed(
  (): DemoSiteTemplate | null =>
    templates.value.find((template: DemoSiteTemplate): boolean => template.id === selectedTemplateId.value) ?? null,
)

/** Whether the picked template differs from the published one. */
const templateChanged: ComputedRef<boolean> = computed(
  (): boolean => Boolean(site.value) && selectedTemplateId.value !== site.value?.template_id,
)

/** Whether the edited colours differ from the published theme. */
const themeChanged: ComputedRef<boolean> = computed((): boolean => {
  if (!site.value) return false
  const publishedTheme: DemoSiteTheme = site.value.theme ?? DEFAULT_DEMO_SITE_THEME
  return (['primary', 'secondary', 'accent'] as const).some(
    (key: keyof DemoSiteTheme): boolean => publishedTheme[key] !== selectedTheme.value[key],
  )
})

/** Whether the Logo ⟷ Template action-colour source differs from the published choice. */
const brandSourceChanged: ComputedRef<boolean> = computed(
  (): boolean => Boolean(site.value) && selectedUseBrandColor.value !== (site.value?.use_brand_color ?? true),
)

/** Whether the edited photo placement differs from the published one. */
const imagesChanged: ComputedRef<boolean> = computed((): boolean => {
  if (!siteImages.value) return false
  return imagesOrder.value.join('\n') !== siteImages.value.order.join('\n')
})

/** Whether the section cards editor applies: the template declares editable cards (published and picked). */
const isServiceCardsEditorVisible: ComputedRef<boolean> = computed((): boolean => {
  if (!serviceCards.value?.config.enabled) return false
  const picked: DemoSiteTemplate | null = selectedTemplate.value
  return picked ? Boolean(picked.service_cards?.enabled) : true
})

const serviceCardsChanged: ComputedRef<boolean> = computed((): boolean => {
  if (!serviceCards.value || !isServiceCardsEditorVisible.value) return false
  return ServiceCards.signature(serviceCardsDraft.value) !== ServiceCards.signature(serviceCards.value.cards)
})

/** Why the pending cards cannot be saved yet (empty when they can). */
const serviceCardsValidationMessage: ComputedRef<string> = computed((): string => {
  if (!serviceCardsChanged.value || !serviceCards.value) return ''
  const minimum: number = serviceCards.value.config.min_cards
  if (serviceCardsDraft.value.length === 0) {
    return 'Ajoutez des cartes, ou revenez aux cartes automatiques depuis le bloc Spécialités.'
  }
  if (serviceCardsDraft.value.length < minimum) return `Au moins ${minimum} cartes sont nécessaires.`
  if (serviceCardsDraft.value.some((card: ServiceCardDraft): boolean => card.title.trim().length === 0)) {
    return 'Chaque carte doit avoir un titre.'
  }
  return ''
})

/** Any pending edit: « Annuler » and « Publier » take the place of the link buttons in the top bar. */
const hasPendingChanges: ComputedRef<boolean> = computed(
  (): boolean =>
    templateChanged.value ||
    themeChanged.value ||
    brandSourceChanged.value ||
    imagesChanged.value ||
    serviceCardsChanged.value,
)

/** Pending edits that are complete enough to publish (the cards editor can block a save). */
const canSavePendingChanges: ComputedRef<boolean> = computed(
  (): boolean => hasPendingChanges.value && serviceCardsValidationMessage.value === '',
)

/** Candidate placement pushed live into the preview, only when it differs from the published one. */
const previewPhotos: ComputedRef<string[] | null> = computed((): string[] | null =>
  imagesChanged.value ? imagesOrder.value : null,
)

/** Candidate section cards pushed live into the preview: only titled ones, only when edited. */
const previewServices: ComputedRef<DemoSiteServiceCard[] | null> = computed((): DemoSiteServiceCard[] | null => {
  if (!serviceCardsChanged.value) return null
  const cards: DemoSiteServiceCard[] = ServiceCards.toPayload(serviceCardsDraft.value).filter(
    (card: DemoSiteServiceCard): boolean => card.title.length > 0,
  )
  return cards.length > 0 ? cards : null
})

/** Candidate colours pushed live into the preview, only when a colour or template edit is pending. */
const previewTheme: ComputedRef<DemoSiteTheme | null> = computed((): DemoSiteTheme | null =>
  templateChanged.value || themeChanged.value || brandSourceChanged.value ? selectedTheme.value : null,
)

/** What the live site is told: the template picked, and the colours, photos and cards only while they are unpublished. */
const previewMessage: ComputedRef<Record<string, unknown>> = computed(
  (): Record<string, unknown> => ({
    templateId: selectedTemplateId.value || site.value?.template_id || '',
    palette: previewTheme.value,
    photos: previewPhotos.value,
    services: previewServices.value,
  }),
)

const isVideoGenerating: ComputedRef<boolean> = computed(
  () => site.value?.video_status === 'pending' || site.value?.video_status === 'generating',
)

const isVideoWaitingForDesktop: ComputedRef<boolean> = computed((): boolean =>
  Boolean(site.value?.video_desktop_requested_at),
)

const desktopVideoRequestLabel: ComputedRef<string> = computed((): string => {
  if (site.value?.is_video_desktop_build_started) {
    return 'Votre PC génère la vidéo (2 à 3 minutes). Vous pouvez quitter cette page.'
  }
  if (prospectSearchStore.isDesktopAppOnline) {
    return 'Demande envoyée à votre PC : il lance la génération dans la minute.'
  }
  return "En attente de votre PC : l'application DevLeadHunter générera la vidéo dès qu'elle sera ouverte. Elle démarre avec Windows."
})

const videoFailureMessage: ComputedRef<string | null> = computed((): string | null => {
  if (site.value?.video_status === 'failed') return site.value.video_error || 'La génération a échoué.'
  if (site.value?.video_status === 'ready' && site.value.video_error) {
    return `La nouvelle génération a échoué, la vidéo actuelle reste en ligne. ${site.value.video_error}`
  }
  return null
})

const videoStatusLabel: ComputedRef<string | null> = computed(() => {
  if (isVideoWaitingForDesktop.value) return site.value?.is_video_desktop_build_started ? 'En cours' : 'En attente'
  switch (site.value?.video_status) {
    case 'pending':
    case 'generating':
      return 'En cours'
    case 'ready':
      return 'Prête'
    case 'failed':
      return 'Échec'
    default:
      return null
  }
})

const videoStatusClass: ComputedRef<string> = computed(() => {
  if (isVideoWaitingForDesktop.value) return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
  if (site.value?.video_status === 'ready') return 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
  if (site.value?.video_status === 'failed') return 'bg-[var(--app-red)]/20 text-[var(--app-red)]'
  return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
})

/** CMS handover state, derived from the persisted status with a sensible fallback. */
const cmsStatus: ComputedRef<StoryblokCollaboratorStatus> = computed((): StoryblokCollaboratorStatus => {
  const current: DemoSite | null = site.value
  if (!current) return 'not_invited'
  if (current.storyblok_collaborator_status) return current.storyblok_collaborator_status
  return current.storyblok_invite_sent ? 'pending' : 'not_invited'
})

/** Badge label for the CMS handover (null hides the badge: nothing sent yet). */
const cmsStatusLabel: ComputedRef<string | null> = computed((): string | null => {
  switch (cmsStatus.value) {
    case 'joined':
      return 'Rejoint'
    case 'pending':
      return 'En attente'
    default:
      return null
  }
})

/** Colour of the CMS handover badge (green once joined, accent while pending). */
const cmsStatusClass: ComputedRef<string> = computed((): string =>
  cmsStatus.value === 'joined'
    ? 'bg-[var(--app-green)]/20 text-[var(--app-green)]'
    : 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]',
)

/** Human date the client joined the CMS, when known. */
const cmsJoinedAtLabel: ComputedRef<string | null> = computed((): string | null =>
  site.value?.storyblok_joined_at ? formatNumericDate(site.value.storyblok_joined_at) : null,
)

/** The tools shown in the bar: « Prestations » only when the template has service cards. */
const visibleTools: ComputedRef<AtelierTool<DemoSiteAtelierToolKey>[]> = computed(
  (): AtelierTool<DemoSiteAtelierToolKey>[] =>
    atelierTools.filter(
      (tool: AtelierTool<DemoSiteAtelierToolKey>): boolean =>
        tool.key !== 'prestations' || isServiceCardsEditorVisible.value,
    ),
)

/** Which tools hold an unpublished change, for the dot on their button. */
const toolPendingChanges: ComputedRef<Record<DemoSiteAtelierToolKey, boolean>> = computed(
  (): Record<DemoSiteAtelierToolKey, boolean> => ({
    template: templateChanged.value,
    couleurs: themeChanged.value || brandSourceChanged.value,
    photos: imagesChanged.value,
    prestations: serviceCardsChanged.value,
    video: false,
    plus: false,
  }),
)

/** The templates offered in the sheet: the current one first, then the recommended ones. */
const selectableTemplates: ComputedRef<DemoSiteTemplate[]> = computed((): DemoSiteTemplate[] => {
  const currentId: string | null = site.value?.template_id ?? null
  const offered: DemoSiteTemplate[] = sortTemplatesByRecommendation(
    filterSelectableTemplates(templates.value, currentId),
    null,
  )
  return [
    ...offered.filter((template: DemoSiteTemplate): boolean => template.id === currentId),
    ...offered.filter((template: DemoSiteTemplate): boolean => template.id !== currentId),
  ]
})

/** One line under the title: time left, video, client space. */
const siteFactsLine: ComputedRef<string> = computed((): string => {
  if (!site.value) return ''
  const facts: string[] = []
  facts.push(DemoSiteService.isTtlPending(site.value) ? 'Pas encore envoyé' : `Expire dans ${daysLeft.value} j`)
  facts.push(
    site.value.video_status === 'ready'
      ? 'Vidéo prête'
      : isVideoGenerating.value || isVideoWaitingForDesktop.value
        ? 'Vidéo en cours'
        : 'Pas de vidéo',
  )
  facts.push(
    cmsStatus.value === 'joined'
      ? 'Client dans son espace'
      : cmsStatus.value === 'pending'
        ? 'Client invité'
        : 'Client pas encore invité',
  )
  return facts.join(' · ')
})

/** When the demo goes offline, in words. */
const expiryLabel: ComputedRef<string> = computed((): string => {
  if (!site.value) return ''
  if (DemoSiteService.isTtlPending(site.value)) return 'Le compte à rebours démarre au premier email envoyé.'
  return `Elle est retirée dans ${daysLeft.value} jour${daysLeft.value > 1 ? 's' : ''}, le ${formatNumericDate(site.value.expires_at)}.`
})

/**
 * Apply a new photo placement.
 * @param next - The reordered list of placed photo URLs.
 */
function onImageOrderChange(next: string[]): void {
  imagesOrder.value = next
}

/**
 * Apply an edited card list; any manual gesture ends the untouched AI suggestion.
 * @param next - The edited cards.
 */
function onServiceCardsChange(next: ServiceCardDraft[]): void {
  serviceCardsDraft.value = next
  serviceCardsDraftFromAi.value = false
}

/**
 * Put the draft back on the published cards.
 */
function resetServiceCardsDraft(): void {
  serviceCardsDraft.value = ServiceCards.toDrafts(serviceCards.value?.cards ?? [])
  serviceCardsDraftFromAi.value = false
}

/**
 * Drop every pending edit: back to the published template, colours, photo placement and cards.
 */
function resetPendingChanges(): void {
  if (!site.value) return
  selectedTemplateId.value = site.value.template_id
  selectedTheme.value = { ...(site.value.theme ?? DEFAULT_DEMO_SITE_THEME) }
  selectedUseBrandColor.value = site.value.use_brand_color ?? true
  imagesOrder.value = [...(siteImages.value?.order ?? [])]
  resetServiceCardsDraft()
}

/**
 * Publish every pending edit (template, colours, photo placement, section cards) in ONE call, so the
 * API regenerates the published site once, then reload the preview on the fresh content.
 * @returns A promise resolved once the site has been regenerated.
 */
async function savePendingChanges(): Promise<void> {
  if (!site.value || !canSavePendingChanges.value) return
  saving.value = true
  try {
    const payload: DemoSiteUpdatePayload = {}
    if (templateChanged.value || themeChanged.value || brandSourceChanged.value) {
      payload.template_id = selectedTemplateId.value
      payload.theme = { ...selectedTheme.value }
      payload.use_brand_color = selectedUseBrandColor.value
    }
    if (imagesChanged.value) {
      payload.image_order = [...imagesOrder.value]
    }
    if (serviceCardsChanged.value) {
      payload.services = ServiceCards.toPayload(serviceCardsDraft.value)
      payload.services_source = serviceCardsDraftFromAi.value ? 'ai' : 'manual'
    }
    site.value = await DemoSiteService.updateDemoSite(demoSiteId, payload)
    await Promise.all([loadImages(), loadServiceCards()])
    resetPendingChanges()
    previewReloadNonce.value += 1
    toast.success('Modifications publiées, site mis à jour')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la publication')
  } finally {
    saving.value = false
  }
}

/**
 * Load the photo pool and current placement for the image editor.
 * Silent on failure: the editor block simply stays hidden.
 */
async function loadImages(): Promise<void> {
  try {
    siteImages.value = await DemoSiteService.getDemoSiteImages(demoSiteId)
  } catch {
    siteImages.value = null
  }
}

/**
 * Load the section cards, their curation state and the labelled photo pool; silent on failure (editor hidden).
 */
async function loadServiceCards(): Promise<void> {
  try {
    serviceCards.value = await DemoSiteService.getDemoSiteServiceCards(demoSiteId)
  } catch {
    serviceCards.value = null
  }
}

/**
 * Ask the AI to compose the section cards; the result replaces the draft, previewed live and saved with the other edits.
 */
async function suggestServiceCards(): Promise<void> {
  if (!serviceCards.value || suggestingServiceCards.value) return
  suggestingServiceCards.value = true
  serviceCardsSuggestionError.value = null
  try {
    const suggestion: DemoSiteServiceCardsSuggestionResult =
      await DemoSiteService.suggestDemoSiteServiceCards(demoSiteId)
    serviceCards.value = {
      ...serviceCards.value,
      pool: suggestion.pool,
      labels_pending: suggestion.pool.filter((photo: DemoSitePhotoLabel): boolean => photo.kind === 'unknown').length,
    }
    serviceCardsAnalysis.value = suggestion.analysis
    if (suggestion.cards.length === 0) {
      serviceCardsSuggestionError.value =
        "L'IA n'a rien pu proposer : pas assez d'indices (photos de plats, menus, avis) pour ce prospect."
      return
    }
    serviceCardsDraft.value = ServiceCards.toDrafts(suggestion.cards)
    serviceCardsDraftFromAi.value = true
    toast.success(
      `${suggestion.cards.length} carte${suggestion.cards.length > 1 ? 's' : ''} proposée${suggestion.cards.length > 1 ? 's' : ''} : vérifiez, ajustez, puis publiez`,
    )
  } catch (error) {
    serviceCardsSuggestionError.value = error instanceof Error ? error.message : 'Échec de la suggestion'
  } finally {
    suggestingServiceCards.value = false
  }
}

/**
 * Drop the saved curation: the site is regenerated right away with its automatic cards.
 */
async function restoreGeneratedServiceCards(): Promise<void> {
  if (!site.value) return
  saving.value = true
  try {
    site.value = await DemoSiteService.updateDemoSite(demoSiteId, { services: [] })
    await loadServiceCards()
    resetServiceCardsDraft()
    serviceCardsAnalysis.value = null
    previewReloadNonce.value += 1
    toast.success('Cartes automatiques restaurées, site mis à jour')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la restauration')
  } finally {
    saving.value = false
  }
}

/**
 * Open the live demo URL in a new browser tab.
 */
async function openDemoUrl(url: string | null): Promise<void> {
  if (!url) return
  await openExternalUrl(url)
}

/**
 * Copy the live demo URL to the clipboard.
 */
async function copyDemoUrl(url: string): Promise<void> {
  await copy(url)
}

/**
 * Invite the client to the Storyblok CMS workspace.
 */
async function handleInvite(): Promise<void> {
  inviting.value = true
  try {
    site.value = await DemoSiteService.inviteDemoSiteClientToCms(demoSiteId)
    toast.success('Invitation au CMS envoyée au client')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Échec de l'invitation")
  } finally {
    inviting.value = false
  }
}

/**
 * Re-read whether the client has joined the CMS (manual « Vérifier » click).
 */
async function handleRefreshCmsStatus(): Promise<void> {
  refreshingCms.value = true
  try {
    site.value = await DemoSiteService.refreshDemoSiteCmsStatus(demoSiteId)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la vérification du statut CMS')
  } finally {
    refreshingCms.value = false
  }
}

/**
 * Silently re-read the CMS handover status on load, so a client who joined shows up without a click.
 */
async function refreshCmsStatusSilently(): Promise<void> {
  try {
    site.value = await DemoSiteService.refreshDemoSiteCmsStatus(demoSiteId)
  } catch {
    // Best-effort : en cas d'échec on garde le statut déjà affiché.
  }
}

/**
 * Export the demo site source code as a downloadable archive.
 */
async function handleExport(): Promise<void> {
  if (!site.value) return
  exporting.value = true
  try {
    await DemoSiteService.exportDemoSiteCode(demoSiteId, site.value.slug)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : "Échec de l'export du code")
  } finally {
    exporting.value = false
  }
}

/**
 * Delete the demo site after user confirmation.
 */
async function handleDelete(): Promise<void> {
  if (!site.value) return
  deleting.value = true
  try {
    await DemoSiteService.deleteDemoSite(demoSiteId)
    await navigateTo('/dashboard/demo-sites')
  } finally {
    deleting.value = false
  }
}

/**
 * Stop the video-status polling loop.
 */
function stopVideoPolling(): void {
  if (videoPollTimer !== null) {
    clearTimeout(videoPollTimer)
    videoPollTimer = null
  }
}

/**
 * Publish what an action on the video returned, keeping the logo colour only the site's own route reads.
 * @param updated - The site as the video route returned it.
 */
function applyVideoActionResult(updated: DemoSite): void {
  site.value = { ...updated, brand_color: site.value?.brand_color ?? null }
}

/**
 * Tell how the video asked from this device ended, once the PC published it or gave it up.
 */
function announceDesktopVideoOutcome(): void {
  if (site.value?.video_error) {
    toast.error(site.value.video_error)
    return
  }
  if (site.value?.video_status === 'ready') toast.success('Vidéo générée par votre PC')
}

/**
 * Read the video's state once, then plan the next read while a generation runs or waits for the PC.
 * @returns A promise resolved once the state is published.
 */
async function pollVideoState(): Promise<void> {
  videoPollTimer = null
  const wasWaitingForDesktop: boolean = isVideoWaitingForDesktop.value
  const state: DemoSiteVideoState | null = await DemoSiteService.getDemoSiteVideoState(demoSiteId).catch(
    (): null => null,
  )
  if (state !== null && site.value !== null) site.value = { ...site.value, ...state }
  if (isVideoGenerating.value || isVideoWaitingForDesktop.value) {
    startVideoPolling()
    return
  }
  if (wasWaitingForDesktop) announceDesktopVideoOutcome()
}

/**
 * Follow the video while it is generated or waits for the PC: every 5 s, slower until the PC starts.
 */
function startVideoPolling(): void {
  if (hasLeftPage || videoPollTimer !== null) return
  const isWaitingForDesktopToStart: boolean =
    isVideoWaitingForDesktop.value && !site.value?.is_video_desktop_build_started
  videoPollTimer = setTimeout(
    pollVideoState,
    isWaitingForDesktopToStart ? DESKTOP_VIDEO_WAIT_POLL_INTERVAL_MS : VIDEO_STATE_POLL_INTERVAL_MS,
  )
}

/**
 * Run the desktop Storyblok background capture once, surfacing errors as a toast.
 * @returns What the sidecar did (`uploaded` / `needs_login` / `skipped` / `unavailable`).
 */
async function runStoryblokBackgroundPrep(): Promise<
  Awaited<ReturnType<typeof StoryblokSidecarService.prepareVideoBackground>>
> {
  videoPrepStatus.value = 'Enregistrement du site + de la séquence Storyblok (~1-2 min, une fenêtre peut s’ouvrir)…'
  try {
    return await StoryblokSidecarService.prepareVideoBackground(demoSiteId)
  } catch (backgroundError) {
    toast.error(
      backgroundError instanceof Error
        ? `Séquence Storyblok ignorée : ${backgroundError.message}`
        : 'Séquence Storyblok ignorée.',
    )
    return 'skipped'
  } finally {
    videoPrepStatus.value = ''
  }
}

/**
 * Open the Storyblok sign-in window and wait until the session is connected.
 *
 * The window stays open until the user signs in or closes it themselves; this
 * resolves true once connected, false if the user closes it or the wait elapses.
 * @returns Whether Storyblok is connected afterwards.
 */
async function waitForStoryblokConnection(): Promise<boolean> {
  videoPrepStatus.value = 'Connecte-toi dans la fenêtre Storyblok qui vient de s’ouvrir…'
  const opened: boolean = await StoryblokSidecarService.openLogin()
  if (!opened) return false
  // The window stays open until the user acts; give them up to 10 min to sign in.
  const deadline: number = Date.now() + 10 * 60 * 1000
  try {
    while (Date.now() < deadline) {
      await new Promise<void>((resolve: () => void): void => {
        window.setTimeout(resolve, 3000)
      })
      const info: Awaited<ReturnType<typeof StoryblokSidecarService.getSessionState>> =
        await StoryblokSidecarService.getSessionState()
      if (info.state === 'ready') return true
      if (!info.loginWindowOpen) return false // user closed the window without signing in
    }
    return false
  } finally {
    videoPrepStatus.value = ''
  }
}

/**
 * Try to build the ENTIRE video on the desktop (capture + montage), setting the status text.
 * @returns The build result (`done` / `needs_login` / `unavailable` / `failed`).
 */
async function runDesktopFullBuild(): Promise<Awaited<ReturnType<typeof StoryblokSidecarService.buildFullVideo>>> {
  videoPrepStatus.value = 'Génération de la vidéo sur votre ordinateur (~2-3 min, une fenêtre peut s’ouvrir)…'
  try {
    return await StoryblokSidecarService.buildFullVideo(demoSiteId)
  } finally {
    videoPrepStatus.value = ''
  }
}

/**
 * Leave the video to the owner's PC: this device cannot film the site and its Storyblok editor.
 * @returns A promise resolved once the request waits for the desktop app, or was refused.
 */
async function requestVideoFromDesktop(): Promise<void> {
  try {
    applyVideoActionResult(await DemoSiteService.requestDesktopVideo(demoSiteId))
    startVideoPolling()
    toast.success('Demande envoyée à votre PC')
  } catch (err: unknown) {
    toast.error(err instanceof Error && err.message ? err.message : "La demande n'a pas pu être envoyée à votre PC.")
  }
}

/**
 * Withdraw the video request left for the PC; a video already published stays online.
 * @returns A promise resolved once the request is withdrawn, or the withdrawal was refused.
 */
async function handleCancelDesktopVideoRequest(): Promise<void> {
  cancellingDesktopVideoRequest.value = true
  try {
    applyVideoActionResult(await DemoSiteService.cancelDesktopVideoRequest(demoSiteId))
    toast.success('Demande annulée')
  } catch (err: unknown) {
    toast.error(err instanceof Error && err.message ? err.message : "La demande n'a pas pu être annulée.")
  } finally {
    cancellingDesktopVideoRequest.value = false
  }
}

/**
 * Generate the video on the server instead of waiting for the PC: it starts at once, without the Storyblok sequence.
 * @returns A promise resolved once the server generation is launched, or was refused.
 */
async function handleGenerateVideoOnServer(): Promise<void> {
  generatingVideo.value = true
  try {
    applyVideoActionResult(await DemoSiteService.generateDemoSiteVideo(demoSiteId))
    startVideoPolling()
    toast.success('Génération de la vidéo lancée sur le serveur')
  } catch (err: unknown) {
    toast.error(err instanceof Error && err.message ? err.message : 'Échec du lancement de la génération')
  } finally {
    generatingVideo.value = false
  }
}

/**
 * Start (or restart) the prospection-video generation.
 */
async function handleGenerateVideo(): Promise<void> {
  generatingVideo.value = true
  const slug: string = site.value?.slug ?? ''
  try {
    const hasLocalVideoBuilder: boolean = (await getScraperSidecarInfo()) !== null
    if (!hasLocalVideoBuilder) {
      await requestVideoFromDesktop()
      return
    }
    // Desktop: build the ENTIRE video locally (capture + montage) with the bundled
    // ffmpeg — the VPS is never involved. The modal follows the sidecar's phases so
    // the wait is never opaque. If the Storyblok session expired, open the sign-in
    // window, wait, then retry automatically. Any local failure (or the web build,
    // which has no sidecar) falls back to the server-side generation.
    videoProgress.start(slug, 'Publication de la vidéo')
    let build: Awaited<ReturnType<typeof StoryblokSidecarService.buildFullVideo>> = await runDesktopFullBuild()

    if (build.status === 'needs_login') {
      videoProgress.close()
      const connected: boolean = await waitForStoryblokConnection()
      if (!connected) {
        toast.error('Storyblok non reconnecté : génération annulée. Reconnecte-toi puis relance.')
        return
      }
      toast.success('Storyblok reconnecté, reprise de la génération…')
      videoProgress.start(slug, 'Publication de la vidéo')
      build = await runDesktopFullBuild()
    }

    if (build.status === 'done') {
      videoProgress.finish()
      site.value = await DemoSiteService.getDemoSite(demoSiteId)
      videoProgress.close()
      toast.success('Vidéo générée sur votre ordinateur ✓')
      return
    }
    if (build.status === 'unavailable') {
      videoProgress.close()
    } else if (build.status === 'failed') {
      // Keep the modal open with the error + logs, and narrate the server fallback in it.
      videoProgress.fail(build.message ?? 'Échec de la génération locale.')
      videoProgress.note('Bascule sur le serveur…')
    }

    // 'unavailable' (web) or 'failed' → server-side generation (memory-guarded). Best-effort
    // desktop background first so the server montage stays light; else the VPS captures too.
    const prepared: Awaited<ReturnType<typeof StoryblokSidecarService.prepareVideoBackground>> =
      await runStoryblokBackgroundPrep()
    if (prepared === 'uploaded') {
      toast.success('Séquence Storyblok prête, montage en cours…')
    }
    site.value = await DemoSiteService.generateDemoSiteVideo(demoSiteId)
    startVideoPolling()
    videoProgress.note('Montage lancé sur le serveur, suivi dans l’outil « Vidéo ».')
    toast.success('Génération de la vidéo lancée (montage en tâche de fond)')
  } catch (error) {
    const message: string = error instanceof Error ? error.message : 'Échec du lancement de la génération'
    videoProgress.fail(message)
    toast.error(message)
  } finally {
    generatingVideo.value = false
  }
}

/**
 * Open the delete-video confirmation modal.
 */
function askDeleteVideo(): void {
  deleteVideoModalRef.value?.open()
}

/**
 * Delete the generated video once confirmed in the modal.
 */
async function handleDeleteVideoConfirmed(): Promise<void> {
  deletingVideo.value = true
  try {
    site.value = await DemoSiteService.deleteDemoSiteVideo(demoSiteId)
    toast.success('Vidéo supprimée')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : 'Échec de la suppression de la vidéo')
  } finally {
    deletingVideo.value = false
  }
}

/**
 * Open the tracked player page as the owner (close button + no tracking/notification).
 * @param url - Player page URL of the site's prospection video.
 */
async function openVideoPage(url: string): Promise<void> {
  await openExternalUrl(`${url}${url.includes('?') ? '&' : '?'}from=app&internal=1`)
}

/**
 * Copy the player page URL as an owner-preview link (excluded from tracking).
 * @param url - Player page URL of the site's prospection video.
 */
async function copyVideoUrl(url: string): Promise<void> {
  await copy(`${url}${url.includes('?') ? '&' : '?'}internal=1`)
}

watch(selectedTemplateId, (templateId: string, previous: string): void => {
  if (!site.value || !previous) return
  // Back to the published template → restore the published colours; another template → its
  // defaults, with the logo colour re-applied on its action key (what the server does on save).
  if (templateId === site.value.template_id) {
    selectedTheme.value = { ...(site.value.theme ?? DEFAULT_DEMO_SITE_THEME) }
    return
  }
  const picked: DemoSiteTemplate | null = selectedTemplate.value
  if (!picked) return
  const theme: DemoSiteTheme = { ...picked.default_theme }
  const actionKey: TemplateThemeColorKey | undefined = picked.color_roles?.action ?? picked.brand_color_key
  if (selectedUseBrandColor.value && site.value.brand_color && actionKey) {
    theme[actionKey] = site.value.brand_color
  }
  selectedTheme.value = theme
})

watch(isServiceCardsEditorVisible, (isVisible: boolean): void => {
  if (!isVisible && activeTool.value === 'prestations') closeActiveTool()
})

onMounted(async () => {
  try {
    site.value = await DemoSiteService.getDemoSite(demoSiteId)
    resetPendingChanges()
    if (isVideoGenerating.value || isVideoWaitingForDesktop.value) startVideoPolling()
    if (site.value.storyblok_invite_sent && site.value.storyblok_collaborator_status !== 'joined') {
      refreshCmsStatusSilently()
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : 'Impossible de charger le site'
  } finally {
    pending.value = false
  }
  try {
    templates.value = await DemoSiteService.listDemoSiteTemplates()
  } catch {
    // Sans le catalogue, la fiche reste lisible : seul le bloc de sélection disparaît.
  } finally {
    loadingTemplates.value = false
  }
  await Promise.all([loadImages(), loadServiceCards()])
  // Second sync now that the photo pool and the cards are known (drafts start on the published state).
  resetPendingChanges()
})

onBeforeUnmount((): void => {
  hasLeftPage = true
  stopVideoPolling()
})
</script>

<style scoped>
.atelier-sheet-enter-active,
.atelier-sheet-leave-active {
  transition:
    transform 0.22s ease,
    opacity 0.22s ease;
}
.atelier-sheet-enter-from,
.atelier-sheet-leave-to {
  transform: translateY(24px);
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .atelier-sheet-enter-active,
  .atelier-sheet-leave-active {
    transition: none;
  }
}
</style>
